from pydantic import BaseModel, Field

class ClassifierOutput(BaseModel):
    """Output schema of the Intake/Classifier node."""
    is_scam: bool
    confidence: float = Field(..., description="0.0 to 1.0 confidence score")
    category: str = Field(..., description="Tactics category or 'unknown'")
    red_flag_hints: list[str] = Field(default_factory=list, description="Cheap surface signals for fallback/degradation")
    masked_text: str = Field(..., description="Raw text with PII masked with placeholders")

class TacticInfo(BaseModel):
    """Details of a surfaced tactic in the final report."""
    name: str
    lever: str
    explanation: str

class ReportingLink(BaseModel):
    """Official channel for reporting the scam."""
    label: str
    url: str

class VerdictInfo(BaseModel):
    """Autopsy final verdict details."""
    is_scam: bool
    confidence: float
    category: str

class ReportOutput(BaseModel):
    """Final output schema produced by the Report Generator node."""
    verdict: VerdictInfo
    tactics: list[TacticInfo] = Field(default_factory=list)
    warning: str = Field(..., description="1-2 sentence plain-language bottom line warning")
    how_to_protect: list[str] = Field(default_factory=list)
    reporting_links: list[ReportingLink] = Field(default_factory=list)
    disclaimer: str = Field(default="educational, not legal/financial advice")
    kb_stat: str = Field(..., description="tactics catalogued: N")

class AdversarialTurn(BaseModel):
    """A single dialogue turn in the adversarial exchange."""
    scammer: str
    guardian: str

class AdversarialTranscript(BaseModel):
    """Transcript of the Scammer vs Guardian loop."""
    turns: list[AdversarialTurn] = Field(default_factory=list)
