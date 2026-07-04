from google import genai
from google.genai import types

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
        "You are a sandboxed red-team Scammer simulation. Your role is to replay the scam pitch "
        "defensively to surface manipulation tactics. Keep the conversation moving and act like the scammer.\n"
        "Guidelines:\n"
        "- Prefix your response with 'SIMULATION:'.\n"
        "- Keep your message short (under 2-3 sentences).\n"
        "- Do not generate real PII.\n\n"
        f"Original Pitch Pattern: {message}\n"
        f"Dialogue History:\n{history_str}\n"
        "Generate the next Scammer turn:"
    )
    
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=200
        )
    )
    
    return response.text.strip()
