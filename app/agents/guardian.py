import sqlite3
from google import genai
from google.genai import types
from app.tools.model_routing import get_model_id

def get_known_tactics(category: str) -> list[dict]:
    """Queries the local sqlite KB to retrieve known tactics for a category."""
    try:
        conn = sqlite3.connect("data/scam_intel.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name, lever, description FROM tactics WHERE category = ?", (category,))
        rows = cursor.fetchall()
        return [{"name": r[0], "lever": r[1], "description": r[2]} for r in rows]
    except Exception:
        return []

def query_guardian(category: str, scammer_turn: str, history: list[dict]) -> str:
    """
    WHY: Simulates the blue-team Guardian agent using gemini-3.1-flash-lite.
    The Guardian counters the scammer's move, names the persuasion lever using the known KB tactics,
    and probes for details.
    """
    client = genai.Client()
    known_tactics = get_known_tactics(category)
    
    # Reference only tactic names+levers (not full scam descriptions) to keep the
    # prompt's scam-content low — the accumulated history/descriptions reliably trip
    # the small model's safety filter and cause empty responses. Each move is
    # analysed independently, so the running dialogue history is not needed here.
    lever_hint = ", ".join(sorted({t["lever"] for t in known_tactics})) or "urgency, authority, fear, scarcity, reciprocity, liking, trust-building"

    prompt = (
        "You are the blue-team Guardian, a defensive consumer-protection analyst. A red-team analyst has "
        "described one manipulation move a scammer uses. Your job is purely educational: name the psychological "
        "lever, explain in one or two sentences how it works on a victim, and state the red flag to watch for.\n"
        "Guidelines:\n"
        f"- Choose the lever from: {lever_hint}.\n"
        "- Write only defensive, protective analysis. Never produce a scam message.\n\n"
        f"Manipulation move to analyse: {scammer_turn}\n\n"
        "Guardian analysis (lever, how it works, red flag):"
    )
    
    # Retry once on an empty response: flash-lite intermittently returns no text
    # for scam-adjacent prompts (model-level safety), and a resample usually succeeds.
    text = ""
    for attempt in range(2):
        response = client.models.generate_content(
            model=get_model_id("flash-lite"),
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2 + 0.3 * attempt, max_output_tokens=250),
        )
        text = (response.text or "").strip()
        if text:
            break
    return text
