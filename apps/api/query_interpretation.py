"""Contrato local de solicitudes. La interpretación no acredita hechos ni celdas."""
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .corpus import documentary_query, terms
from .finance import normalize
from .financial_agent import Intent

TOPIC_ALIASES = {
    "coeficiente cobertura liquidez": ("ccl", "activos", "liquidos", "salidas", "netas", "efectivo", "relacion"),
    "riesgo credito": ("perdida", "potencial", "pago", "contraparte", "acreditado"),
    "margen operativo": ("proporcion", "ingresos", "gastos", "operativos"),
    "portafolio credito": ("segmentamos",),
}

REQUEST = (
    r"(?:indica|describe|explica|define|enumera|señala|identifica|presenta|calcula|compara|"
    r"interpreta|muestra|dame|determina|reporta|averigua|distingue|cuantifica|qué|cuál(?:es)?|cómo|a quién)"
)
MARKER = r"(?:por separado|por otro lado|por otra parte|en otr[oa] (?:apartado|secci[oó]n|bloque)|en segundo lugar|a continuación|después|luego|segundo)"
BOUNDARY = re.compile(
    rf"(?:[.;!?]\s+|,?\s+y,?\s+)(?=[¿¡]?(?:{MARKER}\b|{REQUEST}\b))", re.I
)
MARKER_LEAD = re.compile(rf"^{MARKER}\b[ ,:]*", re.I)
ENUMERATED = re.compile(
    r"\b(?:dos|tres|cuatro|[2-4])\s+(?:apartados?|aspectos?|temas?|solicitudes?|resultados?|necesidades?)"
    r"(?:\s+(?:independientes?|diferentes?))?(?:\s+de\b[^:;.?!]{1,120})?\s*:", re.I
)
RESULT_FACET = re.compile(
    r"^(?:qu[eé]|cu[aá]nto)\s+(?:crecimiento|cambio|variaci[oó]n)\s+(?:relativ[oa]|porcentual)\s+"
    r"(?:representa|implica|supone)\s*[.?!]?(?:\s|$)", re.I
)
NOMINAL_BOUNDARY = re.compile(r"\s+y\s+(?=(?:el|la|los|las)\b)", re.I)
ATTACHMENT = re.compile(
    r"^(?:(?:cita|documenta|sustenta|fundamenta|justifica)\b"
    r"|explica\s+(?:(?:el|ese|este)\s+concepto|cada\s+procedimiento)\b"
    r"|separa\s+claramente\s+lo\s+documentado\b"
    r"|dist[ií]nguelo\b"
    r"|presenta\s+la\s+base(?:,|\s+y)\s+el\s+valor\s+final\b"
    r"|c[oó]mo se define\s*[?.!]"
    r"|calcula\s+(?:(?:la\s+participaci[oó]n\s+solo)|(?:su\s+participaci[oó]n))\s+si\b"
    r"|(?:expresa|exprésal[oa]|usa|conserva|comprueba|verifica|incluye|indica|muestra|menciona|señala|identifica)\b\s+"
    r"(?:(?:en|la|el|las|los|su|sus|amb[oa]s|esta|este|si)\s+)*"
    r"(?:fuente|procedencia|evidencia|página|documento|nota|definici[oó]n|comparabilidad|"
    r"base del cálculo|resultado|escala|unidad|moneda|porcentaje|millones|miles|puntos)\w*\b"
    r"|(?:incluye|indica|muestra)\s+(?:(?:amb[oa]s|los|las|dos|cuatro)\s+)*(?:cifra|valor|tasa|importe)\w*"
    r"(?:\s+(?:original\w*|usad\w*|utilizad\w*|de partida|que usaste)\b|[.!?]?\s*$))",
    re.I,
)


class QuerySpan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str = Field(min_length=1)


class DocumentNeed(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    topic: str = Field(min_length=2, max_length=150)
    kind: Literal["definition", "list", "passage", "scope"]
    scope: str | None = None
    year: int | None = None
    report: Literal["annual", "financial"] | None = None
    facets: tuple[tuple[str, ...], ...] = ()
    anchor: str | None = None
    current_report: bool = False

    @property
    def keywords(self):
        return tuple(terms(self.topic))

    @property
    def permitted(self):
        return sorted(set(self.keywords) | set(TOPIC_ALIASES.get(normalize(self.topic), ()))
                      | {word for group in self.facets for word in group})


class QueryPart(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    span: QuerySpan
    kind: Literal["financial", "documentary"]
    status: Literal["valid", "ambiguous", "unsupported", "incompatible"]
    financial: Intent | None = None
    documentary: DocumentNeed | None = None
    reason: str | None = None
    context: QuerySpan | None = None
    presentation: tuple[str, ...] = ()


class QueryInterpretation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    parts: tuple[QueryPart, ...]

    @property
    def unresolved(self):
        return tuple(i for i, part in enumerate(self.parts) if part.status in {"ambiguous", "unsupported"})

    @property
    def status(self):
        statuses = {part.status for part in self.parts}
        return statuses.pop() if len(statuses) == 1 else "partial"


def request_spans(question: str) -> tuple[QuerySpan, ...]:
    """Contabilizar coordinaciones explícitas antes de elegir los temas."""
    spans = []
    start = 0
    candidates = list(BOUNDARY.finditer(question))
    if enumeration := ENUMERATED.search(question):
        candidates.extend(NOMINAL_BOUNDARY.finditer(question, enumeration.end()))
        candidates.sort(key=lambda match: match.start())
    for boundary in candidates:
        if boundary.start() < start:
            continue
        tail = question[boundary.end():].lstrip("¿¡ ")
        explicit = MARKER_LEAD.match(tail)
        if explicit:
            tail = tail[explicit.end():]
        # Formato y restricciones se conservan en el mismo tramo. Solo una
        # solicitud independiente abre otro requisito de cobertura.
        if not explicit and (
            re.match(r"c[oó]mo se (?:denomina|llama)\b", tail, re.I)
            and not re.search(r"[¿?]", question[start:boundary.start()])
        ):
            continue
        if not explicit and (
            ATTACHMENT.match(tail) or RESULT_FACET.match(tail) or not documentary_query(tail)
            or re.match(r"explica\s+(?:si|qu[eé] efecto|por qu[eé])\b", tail, re.I)
            or re.match(r"(?:trata|considera|sup[oó]n)\b[^;?!]+\bcomo si\b",
                        question[start:boundary.start()].lstrip("¿¡ "), re.I)
        ):
            continue
        if not question[start:boundary.start()].strip(" ¿¡.,;:"):
            continue
        spans.append(QuerySpan(start=start, end=boundary.start(), text=question[start:boundary.start()]))
        start = boundary.end()
    spans.append(QuerySpan(start=start, end=len(question), text=question[start:]))
    return tuple(spans)


def presentation_requirements(text: str) -> tuple[str, ...]:
    """Extraer instrucciones de salida del tramo sin borrarlas de la solicitud."""
    return tuple(clause.strip() for clause in re.split(r"(?<=[.!?;])\s+", text)
                 if ATTACHMENT.match(clause.lstrip("¿¡ ")))
