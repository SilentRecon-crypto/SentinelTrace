"""
Investigation dossier schema (Stage 9).

Deliberately reuses the existing, already-established response schemas for
every section instead of redefining parallel copies — per the explicit
instruction to "use existing schema/model semantics wherever possible" and
to avoid arbitrary JSON blobs as the primary structure:

  case        -> app.schemas.case.CaseOut
  notes       -> app.schemas.case.CaseNoteOut
  evidence    -> app.schemas.evidence.CaseEvidenceOut
  resolution  -> app.schemas.resolution.CaseResolutionOut (nullable)
  alert       -> app.schemas.alert.AlertOut (nullable — see dossier_engine.py)
  risk        -> app.schemas.risk.RiskScoreOut (nullable)
  intervention-> app.schemas.intervention.InterventionWindowOut (nullable)
  prediction  -> app.schemas.prediction.RankedCandidateOut (nullable)

`limitations` is a plain list of human-readable strings explaining any
section that came back null/empty and why, per the "document the
limitation" instruction — never a silent gap.
"""
from pydantic import BaseModel

from app.schemas.alert import AlertOut
from app.schemas.case import CaseNoteOut, CaseOut
from app.schemas.evidence import CaseEvidenceOut
from app.schemas.intervention import InterventionWindowOut
from app.schemas.prediction import RankedCandidateOut
from app.schemas.resolution import CaseResolutionOut
from app.schemas.risk import RiskScoreOut


class DossierOut(BaseModel):
    case: CaseOut
    notes: list[CaseNoteOut]
    evidence: list[CaseEvidenceOut]
    resolution: CaseResolutionOut | None
    alert: AlertOut | None
    risk: RiskScoreOut | None
    intervention: InterventionWindowOut | None
    prediction: RankedCandidateOut | None
    limitations: list[str]
