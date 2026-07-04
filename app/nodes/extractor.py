import sqlite3
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.adk.agents.context import Context
from app.schemas import AdversarialTranscript, TacticInfo, ClassifierOutput
from app.tools.model_routing import get_model_id

from typing import Literal

class ExtractedTactic(BaseModel):
    name: str = Field(..., description="Snake_case name of the tactic")
    lever: Literal[
        "authority", "urgency", "scarcity", "social_proof", "reciprocity",
        "liking", "commitment", "fear", "unrealistic_returns", "trust_building", "isolation"
    ] = Field(..., description="The persuasion lever used")
    description: str = Field(..., description="Detailed description")
    explanation: str = Field(..., description="Plain-language explanation for a non-expert")
    example_masked: str = Field(..., description="PII-masked example of the tactic")
    category: Literal[
        "crypto_investment", "romance", "phishing", "prize_lottery",
        "tech_support", "advance_fee", "impersonation_bec", "unknown"
    ] = Field(..., description="Fraud category")

class ExtractedTacticsWrapper(BaseModel):
    tactics: list[ExtractedTactic]

def save_tactic_to_db(t: ExtractedTactic) -> bool:
    """Inserts a new tactic into the SQLite tactics table, utilizing UNIQUE constraint for dedup."""
    try:
        conn = sqlite3.connect("data/scam_intel.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tactics (name, category, lever, description, example_masked) VALUES (?, ?, ?, ?, ?)",
            (t.name, t.category, t.lever, t.description, t.example_masked)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Deduplication handled via UNIQUE constraint
        return False
    except Exception:
        return False
    finally:
        conn.close()

async def tactic_extractor(ctx: Context, node_input: AdversarialTranscript) -> list[TacticInfo]:
    """
    WHY: Uses gemini-3.1-pro to map dialogue histories (or fallback classifier hints if the
    adversarial loop was degraded) into the persuasion lever taxonomy. New tactics are persisted
    globally into the SQLite knowledge base using deduplication on (name, category) via UNIQUE constraints.
    """
    classifier_output: ClassifierOutput = ctx.state.get("classifier_output")
    is_degraded = ctx.state.get("degraded", False)
    
    # 1.5 Get detected language to write explanations in the correct language
    detected_lang = ctx.state.get("detected_language", "en")
    
    # 2. Build prompt based on whether loop execution succeeded or degraded
    if is_degraded or not node_input.turns:
        hints_str = ", ".join(classifier_output.red_flag_hints) if classifier_output else "None"
        prompt = (
            f"The adversarial replay loop was degraded/bypassed. Analyze these classifier-extracted red flag hints "
            f"and categorize the primary persuasion tactics for category '{classifier_output.category if classifier_output else 'unknown'}':\n\n"
            f"Red flag hints: {hints_str}\n\n"
            f"Sanitized message text: {classifier_output.masked_text if classifier_output else 'None'}\n"
        )
    else:
        transcript_str = ""
        for turn in node_input.turns:
            transcript_str += f"Scammer: {turn.scammer}\nGuardian: {turn.guardian}\n"
            
        prompt = (
            f"Analyze the following adversarial dialogue transcript for category '{classifier_output.category if classifier_output else 'unknown'}'. "
            f"Extract all persuasion tactics demonstrated:\n\n"
            f"{transcript_str}\n"
        )
        
    lang_instruction = ""
    if detected_lang != "en":
        lang_instruction = (
            f"\nIMPORTANT: Write the 'explanation' field for each tactic in the language "
            f"with ISO 639-1 code '{detected_lang}'. Do NOT translate the 'name', 'lever', or 'category' identifiers - only translate the explanation value."
        )

    prompt += (
        "\nFormat your output as a structured list of tactics. For each tactic determine:\n"
        "- name: lowercase snake_case identifier (e.g. guaranteed_returns)\n"
        "- lever: one of [authority, urgency, scarcity, social_proof, reciprocity, liking, commitment, fear, unrealistic_returns, trust_building, isolation]\n"
        "- description: technical explanation of the tactic\n"
        "- explanation: plain language explanation for a non-expert victim\n"
        "- example_masked: example text snippet matching the tactic\n"
        "- category: the fraud category\n"
        f"{lang_instruction}"
    )
    
    client = genai.Client()
    response = client.models.generate_content(
        model=get_model_id("pro"),
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ExtractedTacticsWrapper,
            temperature=0.0
        )
    )
    
    parsed = ExtractedTacticsWrapper.model_validate_json(response.text.strip())
    
    tactic_infos = []
    for t in parsed.tactics:
        save_tactic_to_db(t)
        tactic_infos.append(TacticInfo(
            name=t.name,
            lever=t.lever,
            explanation=t.explanation
        ))
        
    return tactic_infos
