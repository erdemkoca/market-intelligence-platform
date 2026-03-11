import re
from dataclasses import dataclass


@dataclass
class ClassificationResult:
    noga_code: str | None
    industry: str | None
    industry_detail: str | None


# Keyword patterns for trade classification (DE/FR/IT)
TRADE_PATTERNS: list[tuple[str, str, str, str]] = [
    # (regex_pattern, noga_code, industry, industry_detail)
    (r"\b(maler|malerei|anstrich|peinture|pittore|pittura)\b", "43.34", "MALEREI", "Malerei / Anstrich"),
    (r"\b(gipser|gipserei|gips|pl[âa]tr|gessator|gessatura)\b", "43.31", "GIPSEREI", "Gipserei / Verputzerei"),
    (r"\b(fassade|fassadenbau|façade|facciata)\b", "43.31", "FASSADENBAU", "Fassadenbau"),
    (r"\b(verputz|verputzerei|putz|crépissage|intonac)\b", "43.31", "VERPUTZEREI", "Verputzerei"),
    (r"\b(stuck|stuckateur|stuccat)\b", "43.31", "STUCKATEUR", "Stuckateur / Stuckaturen"),
    (r"\b(tapez|tapezierer|tapissier)\b", "43.34", "TAPEZIEREREI", "Tapeziererei"),
    (r"\b(glaser|glaserei|vitr)\b", "43.34", "GLASEREI", "Glaserei"),
    # Broader construction trades (for future expansion)
    (r"\b(elektr|electrici|elettric)\b", "43.21", "ELEKTRO", "Elektroinstallationen"),
    (r"\b(sanit[äa]r|plomb|idraulic)\b", "43.22", "SANITAER", "Sanitärinstallationen"),
    (r"\b(heizung|chauffage|riscaldamento)\b", "43.22", "HEIZUNG", "Heizungsinstallationen"),
    (r"\b(dachdecker|couvreur|copritetto)\b", "43.91", "DACHDECKER", "Dachdeckerarbeiten"),
    (r"\b(zimmermann|zimmer|charpent|carpent)\b", "43.91", "ZIMMEREI", "Zimmerei / Holzbau"),
    (r"\b(schreiner|menuisier|falegnam)\b", "43.32", "SCHREINEREI", "Schreinerei"),
    (r"\b(bodenleger|parquet|paviment)\b", "43.33", "BODENLEGER", "Bodenbeläge"),
    (r"\b(bauunternehm|entreprise.*(construct|bâtiment)|impresa.*costruzion)\b", "41.20", "GENERALUNTERNEHMER", "Generalunternehmer / Hochbau"),
]

# NOGA code to industry mapping (for known NOGA codes)
NOGA_MAP: dict[str, tuple[str, str]] = {
    "43.31": ("GIPSEREI", "Gipserei / Verputzerei / Stuckateur"),
    "43.34": ("MALEREI", "Malerei / Glaserei"),
    "43.39": ("AUSBAU", "Sonstiger Ausbau"),
    "43.21": ("ELEKTRO", "Elektroinstallationen"),
    "43.22": ("SANITAER", "Sanitär- und Heizungsinstallationen"),
    "43.91": ("DACH_ZIMMEREI", "Dachdeckerei / Zimmerei"),
    "43.32": ("SCHREINEREI", "Schreinerei / Bautischlerei"),
    "43.33": ("BODENLEGER", "Fussboden / Fliesen / Platten"),
    "41.20": ("HOCHBAU", "Hochbau / Generalunternehmer"),
}


class IndustryClassifier:
    """Classifies companies by industry based on name, purpose, and NOGA code."""

    def classify(self, name: str | None, purpose: str | None, noga_code: str | None = None) -> ClassificationResult:
        # 1. Try NOGA code first
        if noga_code and noga_code in NOGA_MAP:
            industry, detail = NOGA_MAP[noga_code]
            return ClassificationResult(noga_code=noga_code, industry=industry, industry_detail=detail)

        # 2. Try keyword matching on name + purpose
        text = f"{name or ''} {purpose or ''}".lower()

        for pattern, code, industry, detail in TRADE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return ClassificationResult(noga_code=code, industry=industry, industry_detail=detail)

        # 3. Unknown
        return ClassificationResult(noga_code=noga_code, industry=None, industry_detail=None)

    def is_target_trade(self, name: str | None, purpose: str | None, noga_code: str | None = None) -> bool:
        """Check if company belongs to target trades (Maler/Gipser/Fassaden)."""
        result = self.classify(name, purpose, noga_code)
        return result.noga_code in ("43.31", "43.34") and result.industry is not None
