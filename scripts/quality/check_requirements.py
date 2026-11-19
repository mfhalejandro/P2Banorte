"""Verifica la entrega humana sin escribir ni actualizar su manifiesto."""
import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path


def inventory(source):
    entries = []
    paths = []
    def on_error(error):
        raise error

    for directory, folders, files in os.walk(source, onerror=on_error, followlinks=False):
        paths.extend(Path(directory) / name for name in folders + files)
    for path in sorted(paths, key=lambda p: p.relative_to(source).as_posix()):
        entry = {"path": path.relative_to(source).as_posix()}
        if path.is_symlink():
            entry.update(type="symlink", target=os.readlink(path))
        elif path.is_file():
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            entry.update(type="file", size=path.stat().st_size, sha256=digest)
        elif path.is_dir():
            entry.update(type="dir")
        else:
            raise ValueError(f"Tipo de entrada inesperado: {path.name}")
        entries.append(entry)
    return entries


def fingerprint(entries):
    payload = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify(root):
    source = root / "docs/requirements"
    manifest = json.loads((root / "docs/quality/REQUIREMENTS_INTEGRITY_MANIFEST.json").read_text())
    if not source.is_dir() or source.resolve() != source:
        raise ValueError("Raíz RCTF ausente o redirigida")
    if manifest["status"] != "CONFIRMED" or not manifest["confirmed_by"] or not manifest["delivery_date"]:
        raise ValueError("Falta confirmación de la entrega")
    baseline = manifest["entries"]
    if fingerprint(baseline) != manifest["sha256"]:
        raise ValueError("Manifiesto inconsistente")
    entries = inventory(source)
    errors = []
    if entries != baseline:
        before = {e["path"]: e for e in baseline}
        after = {e["path"]: e for e in entries}
        errors.extend(f"Cambio RCTF: {p}" for p in sorted(before.keys() | after.keys())
                      if before.get(p) != after.get(p))
    for path in [source, *(source / e["path"] for e in entries)]:
        on_readonly_mount = bool(os.statvfs(path).f_flag & os.ST_RDONLY) if not path.is_symlink() else False
        can_change_mode = not on_readonly_mount and path.lstat().st_uid == os.geteuid()
        if path.is_symlink() or can_change_mode or os.access(path, os.W_OK, effective_ids=True):
            errors.append(f"Protección insuficiente: {path.relative_to(source)}")
    # Un directorio protegido por ACL tampoco debe poder sustituirse desde su padre.
    if not os.statvfs(source).f_flag & os.ST_RDONLY:
        if os.access(source.parent, os.W_OK) or source.parent.stat().st_uid == os.geteuid():
            errors.append("La carpeta protegida puede reemplazarse desde su padre")
    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true",
                        help="Tras verificar los originales, comprobar escritura temporal en la raíz")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    try:
        errors = verify(root)
        if args.preflight and not errors:
            with tempfile.NamedTemporaryFile(dir=root, prefix=".arnes-preflight-") as probe:
                probe.write(b"preflight")
                probe.flush()
                probe.seek(0)
                if probe.read() != b"preflight":
                    errors.append("Falló la lectura del archivo temporal en la raíz")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors = [str(exc)]
    if errors:
        print("FAIL", *errors, sep="\n")
        sys.exit(1)
    print("PASS integridad y aislamiento de la entrega confirmada")
    if args.preflight:
        print("PASS escritura temporal en la raíz")
