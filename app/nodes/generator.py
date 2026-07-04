from google.adk.agents.context import Context
from app.schemas import ClassifierOutput, TacticInfo, ReportOutput, VerdictInfo
from typing import Union

async def report_generator(
    ctx: Context, 
    node_input: Union[list[TacticInfo], ClassifierOutput], 
    classifier_output: ClassifierOutput = None
) -> ReportOutput:
    """Assembles the final structured threat intelligence report."""
    # Determine the context inputs based on the predecessor route path
    if isinstance(node_input, list):
        tactics = node_input
        # classifier_output is bound from state automatically by ADK
    else:
        # Came directly from check_scam on the no_scam route
        tactics = []
        classifier_output = node_input

    # Safety default in case binding/state lookup failed
    if classifier_output is None:
        classifier_output = ClassifierOutput(
            is_scam=False,
            confidence=0.0,
            category="unknown",
            red_flag_hints=[],
            masked_text=""
        )

    # TODO: Synthesize final warning, protection steps, and official links
    return ReportOutput(
        verdict=VerdictInfo(
            is_scam=classifier_output.is_scam,
            confidence=classifier_output.confidence,
            category=classifier_output.category
        ),
        tactics=tactics,
        warning="",
        how_to_protect=[],
        reporting_links=[],
        disclaimer="educational, not legal/financial advice",
        kb_stat="tactics catalogued: 0"
    )
