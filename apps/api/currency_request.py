"""Reconocer moneda pedida sin ampliar las monedas verificables en una fuente."""
import re

from .finance import Abstain

# Códigos ISO 4217 para detectar requisitos, no para efectuar conversiones.
ISO_CODES = set((
    "AED AFN ALL AMD ANG AOA ARS AUD AWG AZN BAM BBD BDT BGN BHD BIF BMD BND BOB BOV BRL "
    "BSD BTN BWP BYN BZD CAD CDF CHE CHF CHW CLF CLP CNY COP COU CRC CUC CUP CVE CZK DJF "
    "DKK DOP DZD EGP ERN ETB EUR FJD FKP GBP GEL GHS GIP GMD GNF GTQ GYD HKD HNL HRK HTG "
    "HUF IDR ILS INR IQD IRR ISK JMD JOD JPY KES KGS KHR KMF KPW KRW KWD KYD KZT LAK LBP "
    "LKR LRD LSL LYD MAD MDL MGA MKD MMK MNT MOP MRU MUR MVR MWK MXN MXV MYR MZN NAD NGN "
    "NIO NOK NPR NZD OMR PAB PEN PGK PHP PKR PLN PYG QAR RON RSD RUB RWF SAR SBD SCR SDG "
    "SEK SGD SHP SLE SLL SOS SRD SSP STN SVC SYP SZL THB TJS TMT TND TOP TRY TTD TWD TZS "
    "UAH UGX USD USN UYI UYU UYW UZS VED VES VND VUV WST XAF XAG XAU XBA XBB XBC XBD XCD "
    "XDR XOF XPD XPF XPT XSU XTS XUA XXX YER ZAR ZMW ZWL "
).split())
SUPPORTED = {"MXN", "USD", "EUR"}
MARKER = r"\b(?:en|a|moneda|usa|utiliza|expresa|expresad[oa])\s+(?:(?:solo|solamente|unicamente|exclusivamente|moneda|millones(?: de)?|miles(?: de)?)\s+)*"
FOREIGN_NAME = re.compile(
    r"\b(?:francos?|libras?|yen(?:es)?|yuan(?:es)?|renminbi|rublos?|reales? brasileños|rupias?|coronas?|"
    r"won(?:es)?|dirhams?|dinares?|riyal(?:es)?|soles peruanos|quetzales?|colones?|bol[ií]vares?|"
    r"pesos (?!mexicanos\b)[^\W\d_]+|d[oó]lares (?!estadounidenses\b)[^\W\d_]+)\b",
    re.I,
)
# Una expresión vecina puede ser parte de la frase, no un gentilicio.
CONNECTORS = {"entre", "del", "de", "por", "para", "con", "desde", "hasta", "al", "respecto", "nominales",
              "corrientes", "y", "o", "como", "publicados", "indicados", "originales", "adicionales"}
CODE_REQUIREMENT = re.compile(MARKER + r"(?:\(?)([a-z]{3})\b", re.I)
EXPLICIT_UNIT = re.compile(
    r"\b(?:moneda\s*[:=]\s*|(?:en|a)\s+(?:moneda|exclusivamente|unicamente|solo)\s+)([^\W\d_]+)", re.I,
)


def verify_currency_request(question):
    # Un gentilicio o nombre de divisa entre paréntesis sigue siendo un requisito.
    text = re.sub(r"[()]", " ", question)
    text = " ".join(text.split())
    if re.search(
        r"\b(?:pesos|d[oó]lares) (?:de|del) "
        r"(?!grupo\b|banco\b|gfnorte\b|(?:la )?tenedora\b)(?=[^\W\d_])", text, re.I,
    ):
        raise Abstain("No se puede acreditar un resultado en la moneda solicitada.")
    codes = [hit[1] for hit in CODE_REQUIREMENT.finditer(question)]
    codes.extend(re.findall(r"\(([A-Za-z]{3})\)", question))
    codes.extend(re.findall(r"\b[A-Z]{3}\b", question))
    for token in codes:
        code = token.upper()
        if code in ISO_CODES - SUPPORTED:
            raise Abstain(f"No se puede acreditar un resultado en la moneda solicitada ({code}).")
    for match in FOREIGN_NAME.finditer(text):
        label = match[0].lower().split()
        if label[0] in {"pesos", "dólares", "dolares"} and label[-1] in CONNECTORS:
            continue
        raise Abstain("No se puede acreditar un resultado en la moneda solicitada.")
    for match in EXPLICIT_UNIT.finditer(question):
        if match[1].lower() not in {"mxn", "usd", "eur", "pesos", "dólares", "dolares", "euros", "millones", "miles"}:
            raise Abstain("No se puede acreditar un resultado en la moneda solicitada.")
