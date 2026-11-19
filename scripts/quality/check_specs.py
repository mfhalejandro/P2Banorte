"""Verificar documentos SPEC y sus relaciones desde la raíz del proyecto."""
import re
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SPEC_DIR = ROOT / "specs"
STATES = set("DRAFT IN_REVIEW APPROVED IN_PROGRESS IMPLEMENTED VERIFIED BLOCKED REJECTED SUPERSEDED ARCHIVED".split())
APPROVED_STATES = {"APPROVED", "IN_PROGRESS", "IMPLEMENTED", "VERIFIED"}
LINK = re.compile(r"\[[^\]]+\]\(([^)\s]+)\)")
FIELDS = set("""
    id title status owner reviewers created_at updated_at prd_requirements adrs sdds dependencies
    implementation_plan sprint_tasks quality_gates supersedes superseded_by
""".split())


def check(path, seen, registry, matrix):
    parts = path.read_text().split("---\n", 2)
    if len(parts) != 3 or parts[0]:
        raise ValueError("falta frontmatter YAML")
    _, header, body = parts
    meta = yaml.safe_load(header)
    if not isinstance(meta, dict) or FIELDS - meta.keys():
        raise ValueError("faltan metadatos obligatorios")
    ident = meta["id"]
    if not re.fullmatch(r"SPEC-\d{3}", str(ident)) or not path.name.startswith(f"{ident}-") or ident in seen:
        raise ValueError("ID inválido, duplicado o distinto del nombre")
    seen.add(ident)
    status = meta["status"]
    if status not in STATES or not meta["owner"] or not meta["title"]:
        raise ValueError("estado, título o propietario inválido")
    for field in ("prd_requirements", "adrs", "sdds", "dependencies", "reviewers", "sprint_tasks", "quality_gates"):
        if not isinstance(meta[field], list):
            raise ValueError(f"{field} debe ser una lista")
    if date.fromisoformat(str(meta["updated_at"])) < date.fromisoformat(str(meta["created_at"])):
        raise ValueError("orden de fechas inválido")
    relative = path.relative_to(SPEC_DIR).as_posix()
    rows = [line for line in registry.splitlines() if f"]({relative})" in line]
    if len(rows) != 1 or status not in [s.strip() for s in rows[0].split("|")]:
        raise ValueError("ruta o estado divergente en el registro")
    criteria = set(re.findall(rf"\b{ident}-AC-\d+\b", body))
    if not meta["prd_requirements"] or not criteria or any(c not in matrix for c in criteria):
        raise ValueError("faltan referencias al PRD o criterios en trazabilidad")
    for target in LINK.findall(body):
        if target.startswith(("https://", "http://", "#")):
            continue
        dest = (path.parent / target.split("#")[0]).resolve()
        if not dest.is_relative_to(ROOT) or not dest.is_file():
            raise ValueError(f"enlace local inválido: {target}")
    if status in APPROVED_STATES:
        approval = meta.get("approval")
        if not isinstance(approval, dict) or not all(approval.get(k) for k in ("by", "date", "evidence")):
            raise ValueError("falta aprobación identificable")
        if not meta["reviewers"] or re.search(r"\bTBD\b", body):
            raise ValueError("revisores o pendientes sin resolver")


def main():
    registry = (SPEC_DIR / "SPEC_REGISTRY.md").read_text()
    matrix = (ROOT / "docs/quality/TRACEABILITY_MATRIX.md").read_text()
    errors = []
    seen = set()
    for path in sorted(SPEC_DIR.rglob("SPEC-*.md")):
        try:
            check(path, seen, registry, matrix)
        except (ValueError, TypeError, OSError, yaml.YAMLError) as exc:
            errors.append(f"{path.name}: {exc}")
    for target in LINK.findall(registry):
        dest = (SPEC_DIR / target).resolve()
        if not dest.is_relative_to(SPEC_DIR) or not dest.is_file():
            errors.append(f"Registro con enlace inválido: {target}")
    if errors:
        print("FAIL", *errors, sep="\n")
        return 1
    print(f"PASS estructura y trazabilidad de {len(seen)} especificaciones")
    return 0


if __name__ == "__main__":
    sys.exit(main())
