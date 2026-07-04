from google.adk.agents.context import Context
from app.schemas import ClassifierOutput, TacticInfo, ReportOutput, VerdictInfo

async def report_generator(ctx: Context, node_input: list[TacticInfo], classifier_output: ClassifierOutput) -> ReportOutput:
    """Assembles the final structured threat intelligence report."""
    # TODO: Synthesize final warning, protection steps, and official links
    return ReportOutput(
        verdict=VerdictInfo(
            is_scam=classifier_output.is_scam,
            confidence=classifier_output.confidence,
            category=classifier_output.category
        ),
        tactics=node_input,
        warning="",
        how_to_protect=[],
        reporting_links=[],
        disclaimer="educational, not legal/financial advice",
        kb_stat="tactics catalogued: 0"
    )
