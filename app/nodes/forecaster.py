from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from google.adk.agents.context import Context
from app.schemas import TacticInfo, EscalationStage, ClassifierOutput, AdversarialTranscript
from app.tools.model_routing import get_model_id
from app.guardrails.policy import validate_text_semantic

class EscalationForecastWrapper(BaseModel):
    forecast: list[EscalationStage] = Field(..., description="Staged forecast of likely escalation behaviors")

async def escalation_forecaster(ctx: Context, node_input: list[TacticInfo]) -> list[TacticInfo]:
    """
    WHY: Evaluates the adversarial replay transcript and identified tactics to predict
    defensively how the scam would likely escalate if the user continues to engage.
    This forecasting is written in the detected language of the input, uses gemini-3.1-pro,
    and describes the arc exclusively as a defensive warning from the victim's perspective.
    It passes every output field through the existing semantic Policy Server to ensure
    no operational scam content/scripts are ever generated.
    """
    classifier_output: ClassifierOutput = ctx.state.get("classifier_output")
    transcript: AdversarialTranscript = ctx.state.get("adversarial_transcript")
    detected_lang = ctx.state.get("detected_language", "en")
    is_degraded = ctx.state.get("degraded", False)

    # 1. Skip if the message is benign (no scam analysis needed)
    if classifier_output and not classifier_output.is_scam:
        ctx.state["escalation_forecast"] = []
        return node_input

    # 2. Build input context from either the adversarial transcript or fallback classifier info
    context_str = ""
    if is_degraded or not transcript or not transcript.turns:
        category = classifier_output.category if classifier_output else "unknown"
        hints = ", ".join(classifier_output.red_flag_hints) if classifier_output else "None"
        context_str = f"Scam Category: {category}\nRed Flag Hints: {hints}\nSanitized Message: {classifier_output.masked_text if classifier_output else ''}"
    else:
        transcript_str = ""
        for idx, turn in enumerate(transcript.turns):
            transcript_str += f"Turn {idx+1}:\nScammer: {turn.scammer}\nGuardian: {turn.guardian}\n"
        context_str = f"Scam Category: {classifier_output.category if classifier_output else 'unknown'}\nAdversarial Transcript:\n{transcript_str}"

    # 3. Create the prompt instructing the model to generate the forecast
    lang_instruction = ""
    if detected_lang != "en":
        lang_instruction = (
            f"\nIMPORTANT: Write all human-readable text in the 'what_to_expect' and 'red_flag' fields "
            f"in the language with ISO 639-1 code '{detected_lang}'."
        )

    prompt = (
        f"You are a defensive consumer-protection AI predicting a scam's potential escalation path.\n"
        f"Based on the following analysis of this scam attempt:\n\n"
        f"{context_str}\n\n"
        f"Generate a defensive escalation forecast detailing exactly how this scam would likely develop "
        f"if the victim engaged. Outline 3 progressive stages.\n\n"
        f"CRITICAL SAFETY RULE:\n"
        f"- Describe the stages exclusively from the victim's perspective as educational warnings (e.g., 'The scammer will ask you to pay...').\n"
        f"- NEVER generate operational scripts, ready-to-send templates, or any content a scammer could copy-paste to target a victim. Keep all descriptions strictly analytical and warning-focused.\n"
        f"{lang_instruction}\n\n"
        f"Provide the output as JSON matching the EscalationForecastWrapper schema:\n"
        f"- stage: sequence number (1, 2, 3)\n"
        f"- what_to_expect: what the scammer will do and request next, and how the scam builds pressure\n"
        f"- red_flag: a specific warning indicator/signal the user should watch out for at this stage"
    )

    # 4. Invoke the pro model to generate the structured forecast
    client = genai.Client()
    try:
        response = client.models.generate_content(
            model=get_model_id("pro"),
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=EscalationForecastWrapper,
                temperature=0.0
            )
        )
        parsed = EscalationForecastWrapper.model_validate_json(response.text.strip())
        forecast_list = parsed.forecast
    except Exception:
        # Fallback empty or default warning if API issues occur
        forecast_list = []

    # 5. Route every forecast field through the existing Policy Server gate
    cleaned_forecast = []
    for item in forecast_list:
        expect_ok = validate_text_semantic(item.what_to_expect)
        flag_ok = validate_text_semantic(item.red_flag)
        
        cleaned_expect = item.what_to_expect if expect_ok else "[CONTENT BLOCKED by Policy Server - Reframed to defensive warning to prevent operational leak]"
        cleaned_flag = item.red_flag if flag_ok else "[CONTENT BLOCKED by Policy Server - Security flag violation]"
        
        cleaned_forecast.append(EscalationStage(
            stage=item.stage,
            what_to_expect=cleaned_expect,
            red_flag=cleaned_flag
        ))

    # 6. Save back to ctx.state for the Report Generator to include in the final JSON output
    ctx.state["escalation_forecast"] = cleaned_forecast

    # Return the tactics list unchanged to maintain backward compatibility
    return node_input
