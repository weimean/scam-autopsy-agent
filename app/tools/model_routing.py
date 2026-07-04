import os

def get_model_id(role: str) -> str:
    """
    WHY: Handles differences in model names and quota availability between Vertex AI and AI Studio.
    AI Studio free tier keys have 0 quota for pro models (gemini-3.1-pro/gemini-2.5-pro).
    Therefore, when GOOGLE_GENAI_USE_VERTEXAI is False, we route:
    - 'pro' tasks to 'gemini-3.5-flash' (which has a high quota and excellent extraction quality)
    - 'flash-lite' to 'gemini-3.1-flash-lite'
    - 'judge' to 'gemini-3.5-flash'
    """
    use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "True") == "True"
    
    if role == "pro":
        return "gemini-3.1-pro" if use_vertex else "gemini-3.5-flash"
    elif role == "flash-lite":
        return "gemini-3.1-flash-lite"
    elif role == "judge":
        return "gemini-2.5-pro" if use_vertex else "gemini-3.5-flash"
        
    return "gemini-3.1-flash-lite"
