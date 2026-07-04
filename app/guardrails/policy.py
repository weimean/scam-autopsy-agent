from google import genai
from google.genai import types
from app.schemas import ReportOutput

def validate_text_semantic(text: str) -> bool:
    """
    Performs the semantic layer check using gemini-3.1-pro.
    Returns True if OK, False if VIOLATION.
    """
    if not text:
        return True
        
    client = genai.Client()
    prompt = (
        "Analyze this text to see if it functions as a deployable scam a user could send to a victim. "
        "Strictly answer only with 'VIOLATION' if it is a deployable/usable scam pitch, "
        "or 'OK' if it is defensive, educational, or clearly locked under a safe analysis context.\n\n"
        f"Text to evaluate:\n{text}\n\n"
        "Response (VIOLATION or OK):"
    )
    
    try:
        response = client.models.generate_content(
            model="gemini-3.1-pro",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.0)
        )
        verdict = response.text.strip().upper()
        if "VIOLATION" in verdict:
            return False
    except Exception:
        # Fail-closed for safety
        return False
        
    return True

def validate_scammer_output(text: str) -> str:
    """
    Gates the red-team Scammer's simulated outputs to prevent operational scam generation.
    Checks:
    - Structural: Must start with 'SIMULATION:' and stay under 600 characters.
    - Semantic: Uses validate_text_semantic to detect deployable scams, reframing violations.
    """
    if not text:
        return "SIMULATION: [Empty]"

    # 1. Structural layer: Prefix check
    clean_text = text.strip()
    if not clean_text.upper().startswith("SIMULATION:"):
        clean_text = f"SIMULATION: {clean_text}"

    # 2. Structural layer: Length check
    if len(clean_text) > 600:
        clean_text = clean_text[:597] + "..."

    # 3. Semantic layer check
    if not validate_text_semantic(clean_text):
        return "SIMULATION: [Refused. This output has been blocked because it violates safety rules (functions as a deployable scam). Replaying instead as a defensive pattern description.]"

    return clean_text

def validate_report_output(report: ReportOutput) -> ReportOutput:
    """
    Gates the final Report output to ensure no deployable scam components leak in warnings or protect steps.
    """
    # Check warning text
    if report.warning and not validate_text_semantic(report.warning):
        report.warning = "[CONTENT BLOCKED by Policy Server - Reframed to defensive analysis of the scam pattern to prevent offensive generation]"
        
    # Check how_to_protect descriptions
    cleaned_steps = []
    for step in report.how_to_protect:
        if not validate_text_semantic(step):
            cleaned_steps.append("[Blocked step due to safety violation]")
        else:
            cleaned_steps.append(step)
    report.how_to_protect = cleaned_steps
    
    return report
