import os


def get_model_id(role: str) -> str:
    """
    WHY: Handles differences in model names and quota limits between Vertex AI and AI Studio.
    AI Studio free-tier has a very strict 20 RPD (requests per day) limit on gemini-3.5-flash and
    0 RPD for pro models. To allow complete, high-volume evaluations, we map all roles to
    'gemini-2.5-flash' on AI Studio free tier, which offers 1500 RPD and fast structured output.
    """
    use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "True") == "True"

    if use_vertex:
        if role == "pro":
            # gemini-3.1-pro is published under its preview id on this project;
            # the bare "gemini-3.1-pro" returns 404. Stays distinct from the
            # gemini-2.5-pro judge, preserving judge independence.
            return "gemini-3.1-pro-preview"
        elif role == "flash-lite":
            return "gemini-3.1-flash-lite"
        elif role == "judge":
            return "gemini-2.5-pro"
    else:
        # AI Studio free tier fallbacks to avoid the limit
        return "gemini-3.1-flash-lite"

    return "gemini-3.1-flash-lite"
