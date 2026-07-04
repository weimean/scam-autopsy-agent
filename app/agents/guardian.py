import sqlite3
from google import genai
from google.genai import types

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
    
    # Format known tactics for context
    tactics_str = "\n".join([f"- Tactic '{t['name']}' (lever: {t['lever']}): {t['description']}" for t in known_tactics])
    
    # Format dialogue history
    history_str = ""
    for turn in history:
        history_str += f"Scammer: {turn.get('scammer', '')}\nGuardian: {turn.get('guardian', '')}\n"
        
    prompt = (
        "You are the blue-team Guardian (a defensive consumer-protection expert). "
        "Your task is to counter the scammer's move, identify the persuasion levers, and probe them.\n"
        "Guidelines:\n"
        "- Do not comply or agree to send money, details, or download anything.\n"
        "- Name the lever used (e.g. urgency, unrealistic_returns, commitment, fear, etc.).\n"
        f"- Reference known tactics in this category if applicable:\n{tactics_str}\n\n"
        f"Dialogue History:\n{history_str}"
        f"Latest Scammer Move: {scammer_turn}\n\n"
        "Generate your Guardian response (counter and probe):"
    )
    
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=250
        )
    )
    
    return response.text.strip()
