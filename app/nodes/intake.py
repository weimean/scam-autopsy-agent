from google.adk.agents.context import Context
from app.schemas import ClassifierOutput

async def intake_classifier(ctx: Context, node_input: str) -> ClassifierOutput:
    """Normalizes input, masks PII, and runs initial scam classification."""
    # TODO: Implement PII masking using regex
    # TODO: Run gemini-3.1-flash-lite classifier
    return ClassifierOutput(
        is_scam=False,
        confidence=0.0,
        category="unknown",
        red_flag_hints=[],
        masked_text=node_input
    )
