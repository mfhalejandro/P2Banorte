"""Credenciales y límites del único destino de inferencia autorizado."""
import os
import re
import sqlite3
import stat
from contextlib import closing
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, SecretStr, ValidationError

from .agent import ProviderUnavailable

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = "https://api.deepseek.com"
PREFIX = "DEEPSEEK_"


class DeepSeekSettings(BaseModel):
    api_key: SecretStr = SecretStr("")
    base_url: Literal["https://api.deepseek.com"] = DESTINATION
    model: Literal["deepseek-flash"] = "deepseek-flash"
    allow_real_data: bool = False
    synthetic: bool = False
    max_calls: int = Field(default=6, ge=1, le=10)
    max_rounds: int = Field(default=5, ge=1, le=9)
    max_tools: int = Field(default=12, ge=1, le=24)
    max_input_tokens: int = Field(default=12000, ge=2048, le=32000)
    max_output_tokens: int = Field(default=384, ge=64, le=1024)
    concurrency: int = Field(default=1, ge=1, le=4)
    call_timeout: float = Field(default=6, gt=0, le=15)
    deadline: float = Field(default=15, gt=0, le=15)
    budget_usd: Decimal = Field(default=Decimal("0.10"), gt=0, le=10)
    budget_file: Path = Field(default_factory=lambda: Path(
        os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state"
    ) / "p2banorte/deepseek-budget.sqlite3")


def runtime_env():
    """Leer asignaciones permitidas, sin expansión, shell ni modificación del entorno."""
    names = {"LLM_PROVIDER", *(PREFIX + key.upper() for key in DeepSeekSettings.model_fields)}
    env = {key: os.environ[key] for key in names if key in os.environ}
    if env.get("LLM_PROVIDER", "deepseek") != "deepseek":
        return env
    path = Path(os.environ.get("P2BANORTE_ENV_FILE", ROOT / ".env"))
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return env
    except OSError:
        raise ProviderUnavailable("No se pudo abrir el archivo de configuración protegido.") from None
    with os.fdopen(fd, encoding="utf-8") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) & 0o077 or info.st_size > 65536):
            raise ProviderUnavailable("El archivo de configuración exige propietario local y permisos 0600.")
        for line in stream:
            match = re.fullmatch(r"\s*(?:export\s+)?([A-Z_][A-Z0-9_]*)\s*=\s*(.*?)\s*", line)
            if not match or match[1] not in names or match[1] in env:
                continue
            value = match[2]
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            env[match[1]] = value
    return env


def settings_from_env(env):
    values = {key: env[PREFIX + key.upper()] for key in DeepSeekSettings.model_fields
              if PREFIX + key.upper() in env}
    for flag in ("allow_real_data", "synthetic"):
        if flag in values and values[flag].casefold() not in {"true", "false"}:
            raise ProviderUnavailable("Los indicadores de autorización requieren true o false.")
    try:
        return DeepSeekSettings.model_validate(values)
    except ValidationError:
        raise ProviderUnavailable("Configuración de DeepSeek inválida.") from None


# Tarifas máximas Flash en USD por millón, sin descuento de caché. Importes internos
# en nanodólares para reservar y conciliar de forma atómica y sin float.
INPUT_PRICE = 300
OUTPUT_PRICE = 1200
USD_NANO = 1_000_000_000


class SpendLedger:
    def __init__(self, path, limit):
        self.path = path.expanduser()
        if self.path.is_symlink() or self.path.resolve().is_relative_to(ROOT / "docs/requirements"):
            raise ProviderUnavailable("El presupuesto requiere una ruta de estado privada.")
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        directory = self.path.parent.stat()
        if directory.st_uid != os.geteuid() or stat.S_IMODE(directory.st_mode) & 0o022:
            raise ProviderUnavailable("El directorio de presupuesto debe estar bajo control del usuario local.")
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
                raise ProviderUnavailable("El estado de presupuesto exige permisos privados.")
        finally:
            os.close(fd)
        self.limit = int(limit * USD_NANO)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS spend (id INTEGER PRIMARY KEY CHECK(id=1), nano INTEGER NOT NULL)")
            db.execute("INSERT OR IGNORE INTO spend VALUES (1, 0)")

    def reserve(self, amount):
        with closing(sqlite3.connect(self.path)) as db, db:
            result = db.execute("UPDATE spend SET nano=nano+? WHERE id=1 AND nano+?<=?",
                                (amount, amount, self.limit))
            if not result.rowcount:
                raise ProviderUnavailable("Se agotó el presupuesto autorizado para DeepSeek.")

    def reconcile(self, reserved, actual):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE spend SET nano=nano+? WHERE id=1", (actual - reserved,))
