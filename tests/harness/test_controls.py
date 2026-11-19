"""Pruebas de gates con directorios desechables. Ejecutar como usuario de desarrollo."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[2]
CHECK = PROJECT / "scripts/quality/check_requirements.py"
PUBLISH = Path("scripts/security/check_publication.py")
MANIFEST = Path("docs/execution/APPLICATION_FILE_MANIFEST.md")


def module(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


integrity = module(CHECK)


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / "docs/requirements"
        self.source.mkdir(parents=True)
        self.path = self.source / "original.md"
        self.path.write_text("entrega de prueba")
        self.manifest = self.root / "docs/quality/REQUIREMENTS_INTEGRITY_MANIFEST.json"
        self.manifest.parent.mkdir()
        entries = integrity.inventory(self.source)
        self.manifest.write_text(json.dumps(dict(status="CONFIRMED", confirmed_by="fixture",
                                                 delivery_date="2026-11-19", entries=entries,
                                                 sha256=integrity.fingerprint(entries))))

    def test_writable_source_blocks_matching_contents(self):
        errors = integrity.verify(self.root)
        self.assertTrue(any("Protección" in m for m in errors))
        self.assertFalse(any("Cambio RCTF" in m for m in errors))

    def test_intact_readonly_copy(self):
        if os.geteuid() == 0:
            self.skipTest("root puede escribir bajo permisos DAC de prueba")
        for p in (self.source.parent, self.source, self.path):
            saved = p.stat().st_mode
            p.chmod(0o444 if p.is_file() else 0o555)
            self.addCleanup(p.chmod, saved)
        # El dueño aún puede cambiar el modo de sus propias copias.
        self.assertTrue(integrity.verify(self.root))
        # Modelar un árbol administrado por otra identidad. La lectura y la
        # comprobación de permisos efectivos se hacen sobre los archivos reales.
        with patch.object(integrity.os, "geteuid", return_value=os.geteuid() + 1):
            self.assertEqual([], integrity.verify(self.root))

    def test_inventory_changes(self):
        original = self.path.read_bytes()
        moved = self.source / "nuevo.md"
        for change in ("edit", "add", "remove", "rename", "symlink"):
            with self.subTest(change=change):
                if change == "edit":
                    self.path.write_bytes(b"otra entrega")
                elif change == "add":
                    moved.mkdir()
                elif change == "remove":
                    self.path.unlink()
                elif change == "rename":
                    self.path.rename(moved)
                else:
                    self.path.unlink()
                    self.path.symlink_to(self.manifest)
                self.assertTrue(any("Cambio RCTF" in m for m in integrity.verify(self.root)))
                if moved.is_dir():
                    moved.rmdir()
                elif moved.exists():
                    moved.unlink()
                if self.path.is_symlink():
                    self.path.unlink()
                self.path.write_bytes(original)

    def test_unconfirmed_baseline(self):
        doc = json.loads(self.manifest.read_text())
        doc["status"] = "DRAFT"
        self.manifest.write_text(json.dumps(doc))
        with self.assertRaises(ValueError):
            integrity.verify(self.root)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.git("init", "-q")
        for rel in (PUBLISH, MANIFEST):
            dest = self.root / rel
            dest.parent.mkdir(parents=True)
            shutil.copyfile(PROJECT / rel, dest)
        self.skill = self.root / ".agents/skills/ejemplo/SKILL.md"
        self.skill.parent.mkdir(parents=True)
        self.skill.write_text("---\nname: ejemplo\ndescription: Revisar un ejemplo local.\n---\n")

    def git(self, *args):
        return subprocess.check_output(["git", "-c", "user.name=Fixture", "-c",
                                        "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false",
                                        *args], cwd=self.root)

    def check(self, code, *extra):
        result = subprocess.run([sys.executable, "-B", self.root / PUBLISH, *extra],
                                text=True, capture_output=True)
        self.assertEqual(code, result.returncode, result.stdout + result.stderr)
        return result.stdout

    def test_valid_skill(self):
        self.check(0)
        self.git("add", ".")
        self.check(0)

    def test_env_and_pdf(self):
        for name in (".env", "documento.pdf"):
            (self.root / name).touch()
            self.assertIn(name, self.check(1))
            (self.root / name).unlink()

    def test_index_only(self):
        path = self.root / "entrega.zip"
        path.touch()
        self.git("add", path.name)
        path.unlink()
        self.assertIn("índice", self.check(1))

    def test_outgoing_history(self):
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        base = self.git("rev-parse", "HEAD").decode().strip()
        self.skill.write_text("token=" + '"' + "abcdefghijklmnop" + '"')
        self.git("add", ".")
        self.git("commit", "-qm", "intermedio")
        bad = self.git("rev-parse", "--short=12", "HEAD").decode().strip()
        self.skill.write_text("restablecido")
        self.git("add", ".")
        self.git("commit", "-qm", "posterior")
        self.assertIn(bad, self.check(1, "--base", base))
        self.assertNotIn("abcdefghijklmnop", self.check(1))


if __name__ == "__main__":
    unittest.main()
