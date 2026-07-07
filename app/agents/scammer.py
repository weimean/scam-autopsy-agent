from google import genai
from google.genai import types
from app.tools.model_routing import get_model_id

def query_scammer(message: str, history: list[dict]) -> str:
    """
    WHY: Simulates the red-team scammer agent dynamically using gemini-3.1-flash-lite.
    It takes the initial scam message and the running dialogue history to generate
    the next turn of the scam pitch.
    """
    client = genai.Client()
    
    # Construct conversation context
    history_str = ""
    for turn in history:
        history_str += f"Scammer: {turn.get('scammer', '')}\nGuardian: {turn.get('guardian', '')}\n"
        
    prompt = (
        "You are a sandboxed red-team analyst in a DEFENSIVE simulation. You do NOT write messages a "
        "scammer could send. Instead you EXPOSE the scammer's next manipulation move so a Guardian can "
        "learn to recognise it. Reveal the playbook one move at a time.\n"
        "Guidelines:\n"
        "- Prefix your response with 'SIMULATION:'.\n"
        "- Describe the scammer's NEXT move in the third person, e.g. "
        "'The scammer escalates with a false authority cue, claiming to be the bank's fraud desk, to pressure a fast reply.'\n"
        "- Name the psychological lever it exploits (urgency, authority, fear, scarcity, liking, reciprocity, trust-building).\n"
        "- Do NOT produce a ready-to-send scam message, links, or real PII. One or two sentences.\n\n"
        f"Scam under analysis: {message}\n"
        f"Dialogue so far:\n{history_str}\n"
        "Expose the scammer's next manipulation move (start with 'SIMULATION:'):"
    )
    
    # Retry once on an empty response: flash-lite intermittently returns no text
    # for scam-adjacent prompts (model-level safety), and a resample usually succeeds.
    text = ""
    for _ in range(2):
        response = client.models.generate_content(
            model=get_model_id("flash-lite"),
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.7, max_output_tokens=200),
        )
        text = (response.text or "").strip()
        if text:
            break
    return text
