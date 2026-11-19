"""Inspección local de candidatos Git. Nunca añade archivos ni contacta un remoto."""
import argparse
import fnmatch
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "docs/execution/APPLICATION_FILE_MANIFEST.md"
MAX_BYTES = 2 * 1024 * 1024
PRIVATE = {".env", ".envrc", "secrets", "sensitive", "private", "node_modules", ".venv",
           "__pycache__", ".cache", "raw-confidential", ".git"}
SUFFIXES = {".pdf", ".zip", ".gz", ".tar", ".pem", ".key", ".p12", ".sqlite", ".db",
            ".sqlite3", ".log", ".db-wal", ".db-shm", ".pyc", ".bin"}
SECRET = re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:AKIA|ASIA)[A-Z0-9]{16}|"
                    rb"gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{24,}|"
                    rb"(?:password|api[_-]?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9_./+=-]{12,}['\"]",
                    re.IGNORECASE)


def git(*args):
    return subprocess.check_output(["git", "--no-replace-objects", "-C", str(ROOT), *args],
                                   env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})


def rules():
    lines = (ROOT / MANIFEST).read_text().splitlines()
    patterns = [line.split("|")[1].strip().strip(chr(96)) for line in lines if line.startswith("| " + chr(96))]
    if not patterns:
        raise ValueError("Falta la lista positiva")
    return patterns


def path_issue(name, patterns):
    path = Path(name.lower())
    if any(ord(c) < 32 for c in name) or path.is_absolute() or ".." in path.parts:
        return "ruta no publicable"
    if any(part in PRIVATE or (part.startswith(".env.") and part != ".env.example")
           for part in path.parts) or path.suffix in SUFFIXES:
        return "material restringido"
    if not any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns):
        return "fuera del manifiesto"
    return None


def inspect(base):
    patterns = rules()
    issues = set()
    examined = {}
    def review(layer, name, mode, oid=None):
        issue = path_issue(name, patterns)
        if not issue and mode not in ("100644", "100755"):
            issue = "tipo de entrada no admitido"
        if not issue:
            key = oid or ("worktree", name)
            if key not in examined:
                path = ROOT / name
                size = int(git("cat-file", "-s", oid)) if oid else path.stat().st_size
                if size > MAX_BYTES:
                    examined[key] = "requiere revisión de tamaño"
                else:
                    body = git("cat-file", "blob", oid) if oid else path.read_bytes()
                    examined[key] = ("revisión de contenido requerida"
                                     if b"\x00" in body or SECRET.search(body) else None)
            issue = examined[key]
        if issue:
            issues.add(f"{layer}: {ascii(name)}: {issue}")

    work = git("ls-files", "--cached", "--others", "--exclude-standard", "-z")
    for raw in set(work.split(b"\x00")) - {b""}:
        name = os.fsdecode(raw)
        path = ROOT / name
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            review("árbol", name, "120000")
        elif path.exists():
            review("árbol", name, "100644" if path.is_file() else "160000")
    for record in git("ls-files", "--stage", "-z").split(b"\x00"):
        if record:
            meta, raw = record.split(b"\t", 1)
            mode, oid, stage = meta.decode().split()
            if stage != "0":
                issues.add(f"índice en conflicto: {ascii(os.fsdecode(raw))}")
            review("índice", os.fsdecode(raw), mode, oid)
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", "--quiet", "HEAD"],
                          stdout=subprocess.DEVNULL).returncode
    if head and (base or head != 1):
        raise ValueError("HEAD o base no verificables")
    if not head:
        if git("rev-parse", "--is-shallow-repository").strip() == b"true":
            raise ValueError("Historial incompleto")
        rev = "HEAD"
        if base:
            ancestor = git("rev-parse", "--verify", "--end-of-options", base + "^{commit}").strip().decode()
            git("merge-base", "--is-ancestor", ancestor, "HEAD")
            rev = ancestor + "..HEAD"
        for commit in git("rev-list", rev).decode().splitlines():
            if SECRET.search(git("cat-file", "commit", commit)):
                issues.add(f"{commit[:12]}: revisar metadatos o mensaje del commit")
            for record in git("ls-tree", "-rz", commit).split(b"\x00"):
                if record:
                    meta, raw = record.split(b"\t", 1)
                    mode, _, oid = meta.decode().split()
                    review(commit[:12], os.fsdecode(raw), mode, oid)
    return sorted(issues)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="Ancestro remoto verificado. Sin base se revisa todo HEAD.")
    args = parser.parse_args()
    try:
        findings = inspect(args.base)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        findings = [f"Comprobación incompleta ({type(exc).__name__})"]
    if findings:
        print("FAIL", *findings, sep="\n")
        sys.exit(1)
    print("PASS controles automáticos. Revisar clasificación, derechos y autorización antes de publicar.")
