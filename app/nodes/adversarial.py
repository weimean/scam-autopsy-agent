from google.adk.agents.context import Context
from app.schemas import ClassifierOutput, AdversarialTranscript

async def adversarial_core(ctx: Context, node_input: ClassifierOutput) -> AdversarialTranscript:
    """Orchestrates Scammer vs Guardian loop up to 6 turns with timeout & error bounds."""
    # TODO: Initialize agents
    # TODO: Execute loop turn-by-turn checking bounds
    # TODO: Implement Policy Server safety checks on Scammer outputs
    return AdversarialTranscript(turns=[])
