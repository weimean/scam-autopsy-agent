import asyncio
import time

from google.adk.agents.context import Context

from app.agents.guardian import query_guardian
from app.agents.scammer import query_scammer
from app.guardrails.policy import validate_scammer_output
from app.schemas import AdversarialTranscript, AdversarialTurn, ClassifierOutput


async def adversarial_core(
    ctx: Context, node_input: ClassifierOutput
) -> AdversarialTranscript:
    """
    WHY: Implements the bounded adversarial simulation loop (max 6 turns, 60s timeout, 8000 token limit)
    to replay the scam pitch defensively. The Policy Server gates each Scammer turn. If any
    limit or error occurs, it sets a degradation flag in state, enabling the system to fall back
    gracefully to static analysis.
    """
    turns = []
    start_time = time.time()
    total_chars = 0
    max_turns = 6
    token_ceiling = (
        8000  # standard token/char heuristic (4 chars per token -> ~32,000 chars)
    )
    max_chars_limit = token_ceiling * 4
    timeout_seconds = 60.0

    # Initialize state flags
    ctx.state["degraded"] = False
    ctx.state["degradation_reason"] = ""
    ctx.state["loop_turns_run"] = 0

    try:
        if ctx.state.get("blocked"):
            return AdversarialTranscript(turns=[])
        current_input = node_input.masked_text

        for turn_idx in range(max_turns):
            # Check timeout bounds
            if time.time() - start_time >= timeout_seconds:
                ctx.state["degraded"] = True
                ctx.state["degradation_reason"] = "Loop timeout exceeded"
                break

            # Check token/character ceilings
            if total_chars > max_chars_limit:
                ctx.state["degraded"] = True
                ctx.state["degradation_reason"] = "Token ceiling exceeded"
                break

            # Prior turns as dicts — the agents expect list[dict] and read them
            # with .get(); passing AdversarialTurn objects crashes on turn 2+.
            history = [t.model_dump() for t in turns]

            # 1. Scammer turn (Red-team pitch simulation)
            scammer_raw = await asyncio.to_thread(query_scammer, current_input, history)

            # Apply Policy Server safety checks (structural + semantic)
            scammer_clean = validate_scammer_output(scammer_raw)

            # 2. Guardian turn (Blue-team response & lever checking)
            guardian_res = await asyncio.to_thread(
                query_guardian, node_input.category, scammer_clean, history
            )

            # Log turn and track counts
            turns.append(AdversarialTurn(scammer=scammer_clean, guardian=guardian_res))
            total_chars += len(scammer_clean) + len(guardian_res)
            ctx.state["loop_turns_run"] = turn_idx + 1

            # Pass Guardian counter back to Scammer
            current_input = guardian_res

    except Exception as e:
        ctx.state["degraded"] = True
        ctx.state["degradation_reason"] = f"Loop execution error: {e!s}"

    transcript = AdversarialTranscript(turns=turns)
    ctx.state["adversarial_transcript"] = transcript.model_dump()
    return transcript
