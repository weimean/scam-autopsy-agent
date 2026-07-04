import sqlite3
from typing import Union
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.adk.agents.context import Context
from app.schemas import ClassifierOutput, TacticInfo, ReportOutput, VerdictInfo, ReportingLink
from app.guardrails.policy import validate_report_output
from app.tools.model_routing import get_model_id

class SynthesizedReport(BaseModel):
    warning: str = Field(..., description="1-2 sentence warning about this specific scam")
    how_to_protect: list[str] = Field(..., description="List of concrete steps to take")
    reporting_links: list[ReportingLink] = Field(..., description="Official reporting channels")

def get_stats_total() -> int:
    """Queries the SQLite tactics table to get the total number of catalogued tactics."""
    try:
        conn = sqlite3.connect("data/scam_intel.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tactics")
        total = cursor.fetchone()[0]
        return total
    except Exception:
        return 0
    finally:
        try:
            conn.close()
        except Exception:
            pass

async def report_generator(
    ctx: Context, 
    node_input: Union[list[TacticInfo], ClassifierOutput], 
    classifier_output: ClassifierOutput = None
) -> ReportOutput:
    """
    WHY: Assembles the final threat intelligence report following specs/03_schemas.md.
    For scam messages, it queries gemini-3.1-pro to synthesize context-aware, plain-language
    advisories, how-to-protect tips, and official links. Benign messages bypass the LLM synthesis
    to save tokens. Integrates SQLite row count dynamically for the 'kb_stat' UI element.
    WHY (language): Reads detected_language from ctx.state and instructs the LLM to write
    the report in that language, so a non-English speaker receives guidance they can read.
    """
    # 1. Parse branching logic inputs
    if isinstance(node_input, list):
        tactics = node_input
    else:
        tactics = []
        classifier_output = node_input

    # Fallback defaults if binding/state was empty
    if classifier_output is None:
        classifier_output = ClassifierOutput(
            is_scam=False,
            confidence=0.0,
            category="unknown",
            red_flag_hints=[],
            masked_text=""
        )

    # 1.5 Read the detected language from context state (set by Intake)
    detected_lang = ctx.state.get("detected_language", "en")

    # 2. Get database statistics for collective-intelligence counter
    total_catalogued = get_stats_total()
    kb_stat = f"tactics catalogued: {total_catalogued}"

    # 2.5 If safety blocked, return security warning immediately
    if ctx.state.get("blocked"):
        return validate_report_output(ReportOutput(
            verdict=VerdictInfo(
                is_scam=True,
                confidence=1.0,
                category="unknown"
            ),
            tactics=[],
            warning="[CONTENT BLOCKED by Policy Server - Reframed to defensive analysis of the scam pattern to prevent offensive generation]",
            how_to_protect=[
                "Do not interact with or attempt to generate malicious content.",
                "Report potential online abuse or security issues to appropriate authorities."
            ],
            reporting_links=[],
            disclaimer="educational, not legal/financial advice",
            kb_stat=kb_stat,
            language=detected_lang
        ))

    # 3. Handle benign messages (ham) without calling LLM (token optimization)
    if not classifier_output.is_scam:
        return validate_report_output(ReportOutput(
            verdict=VerdictInfo(
                is_scam=False,
                confidence=classifier_output.confidence,
                category=classifier_output.category
            ),
            tactics=[],
            warning="This message does not appear to be a scam. No safety threats identified.",
            how_to_protect=[
                "Keep personal details secure.",
                "Avoid clicking on links sent from unsolicited numbers or emails."
            ],
            reporting_links=[
                ReportingLink(label="FTC Consumer Advice", url="https://consumer.ftc.gov")
            ],
            disclaimer="educational, not legal/financial advice",
            kb_stat=kb_stat,
            language=detected_lang
        ))

    # 4. Synthesize scam warning/guidance using gemini-3.1-pro
    client = genai.Client()
    tactics_summary = ", ".join([f"{t.name} (lever: {t.lever})" for t in tactics])
    
    # WHY: We instruct the LLM to write in the detected language so non-English speakers
    # receive actionable protection guidance they can actually read. Taxonomy identifiers
    # (lever names, categories) remain English because they are language-agnostic codes.
    lang_instruction = ""
    if detected_lang != "en":
        lang_instruction = (
            f"\n\nIMPORTANT: Write ALL human-readable text (warning, how_to_protect steps, "
            f"reporting_links labels, disclaimer) in the language with ISO 639-1 code '{detected_lang}'. "
            f"Do NOT translate field names or lever/category identifiers — only the values."
        )
    
    prompt = (
        f"You are a consumer protection threat analyst writing an educational safety advisory.\n"
        f"Analyze this scam category '{classifier_output.category}' with text:\n"
        f"'{classifier_output.masked_text}'\n\n"
        f"Identified persuasion tactics: {tactics_summary}\n\n"
        f"Synthesize the following fields precisely:\n"
        f"1. warning: 1-2 sentence plain-language warning summarizing the core threat.\n"
        f"2. how_to_protect: list of concrete, actionable safety steps the user should take immediately.\n"
        f"3. reporting_links: list of official channels to report this category of scam (e.g. FTC at https://reportfraud.ftc.gov, IC3 at https://www.ic3.gov, etc. with label and url fields).\n"
        f"{lang_instruction}"
    )
    
    response = client.models.generate_content(
        model=get_model_id("pro"),
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SynthesizedReport,
            temperature=0.0
        )
    )
    
    synthesized = SynthesizedReport.model_validate_json(response.text.strip())
    
    return validate_report_output(ReportOutput(
        verdict=VerdictInfo(
            is_scam=True,
            confidence=classifier_output.confidence,
            category=classifier_output.category
        ),
        tactics=tactics,
        warning=synthesized.warning,
        how_to_protect=synthesized.how_to_protect,
        reporting_links=synthesized.reporting_links,
        disclaimer="educational, not legal/financial advice",
        kb_stat=kb_stat,
        language=detected_lang
    ))
