import json
from google import genai
from google.genai import types
from google.adk.agents.context import Context
from app.schemas import ClassifierOutput
from app.tools.pii_masker import mask_pii
from app.tools.model_routing import get_model_id
from app.guardrails.policy import validate_input_intent

async def intake_classifier(ctx: Context, node_input: str) -> ClassifierOutput:
    """
    WHY: This node acts as the system entrypoint. It performs regex-based PII masking
    first to prevent raw user sensitive data from being sent to the LLM or persistent store.
    It then uses gemini-3.1-flash-lite to classify the sanitized text, determining scam status,
    confidence, category, extracting surface-level red flag hints, and detecting the input
    language (ISO 639-1) so the report can be written in the same language.
    """
    # 1. Mask PII immediately to protect user privacy
    masked = mask_pii(node_input)
    
    # 1.5 Check intent safety (prevent offensive use or safety bypass requests)
    if not validate_input_intent(node_input):
        ctx.state["blocked"] = True
        result = ClassifierOutput(
            is_scam=True,
            confidence=1.0,
            category="unknown",
            red_flag_hints=["Safety Policy Violation"],
            masked_text=masked,
            detected_language="en"
        )
        ctx.state["classifier_output"] = result.model_dump()
        ctx.state["detected_language"] = "en"
        return result
        
    # 2. Query gemini-3.1-flash-lite for structured classification + language detection
    client = genai.Client()
    prompt = (
        f"Analyze this forwarded message and classify it according to safety rules:\n\n"
        f"Message: {masked}\n\n"
        f"Determine:\n"
        f"- is_scam (boolean)\n"
        f"- confidence (float, 0.0 to 1.0)\n"
        f"- category (one of: crypto_investment, romance, phishing, prize_lottery, tech_support, advance_fee, impersonation_bec, or 'unknown')\n"
        f"- red_flag_hints (list of strings representing surface red flags, e.g., deadline pressure, unsolicited wire change request)\n"
        f"- detected_language (ISO 639-1 two-letter code of the message language, e.g. 'en', 'es', 'fr', 'tl')\n"
    )
    
    response = client.models.generate_content(
        model=get_model_id("flash-lite"),
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ClassifierOutput,
            temperature=0.0
        )
    )
    
    # Validate and parse response
    result = ClassifierOutput.model_validate_json(response.text.strip())
    # Hard-enforce that masked_text contains our Python-masked text
    result.masked_text = masked
    
    # Store in context state for downstream nodes (like report generator)
    ctx.state["classifier_output"] = result.model_dump()
    # WHY: Store detected_language separately so the Report Generator can write in
    # the same language as the input, making the report useful to non-English speakers
    ctx.state["detected_language"] = result.detected_language
    
    return result
