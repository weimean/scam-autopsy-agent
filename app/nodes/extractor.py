from google.adk.agents.context import Context
from app.schemas import AdversarialTranscript, TacticInfo

async def tactic_extractor(ctx: Context, node_input: AdversarialTranscript) -> list[TacticInfo]:
    """Maps the surfaced dialogue history to the tactical taxonomy and queries/saves to MCP."""
    # TODO: Perform extraction using gemini-3.1-pro
    # TODO: Interact with SQLite scam-intel MCP to query and add new tactics
    return []
