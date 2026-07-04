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
        f"CRITICAL SAFETY RULES:\n"
        f"- Describe the stages exclusively as direct, second-person WARNINGS TO THE VICTIM (e.g., 'They will try to get you to enter your PIN or one-time code on a fake page; never do this' or 'They will instruct you to pay a release fee to withdraw your money; do not pay them').\n"
        f"- NEVER generate operational scripts, ready-to-send templates, or any copy-pasteable messages a scammer could use. Describe the actions analytically from the outside.\n"
        f"{lang_instruction}\n\n"
        f"Provide the output as JSON matching the EscalationForecastWrapper schema:\n"
        f"- stage: sequence number (1, 2, 3)\n"
        f"- what_to_expect: what the scammer will do and request next, written as a direct second-person warning to the victim.\n"
        f"- red_flag: a specific warning indicator/signal the user should watch out for at this stage."
    )

    # 4. Invoke the pro model to generate the structured forecast with a retry loop
    client = genai.Client()
    forecast_list = []
    
    # Try up to 3 times to get a forecast that fully passes the semantic policy gate
    for attempt in range(3):
        current_prompt = prompt
        if attempt > 0:
            current_prompt += (
                f"\n\nSTRICT SAFETY WARNING (Attempt {attempt+1}): The previous generation failed "
                "the safety gate. You must make sure every field is purely an analytical warning "
                "to the victim. Avoid any copy-pasteable scam dialog or direct requests."
            )
        try:
            response = client.models.generate_content(
                model=get_model_id("pro"),
                contents=current_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=EscalationForecastWrapper,
                    temperature=0.1 * attempt
                )
            )
            parsed = EscalationForecastWrapper.model_validate_json(response.text.strip())
            candidate_list = parsed.forecast
            
            # Verify if all stages pass the semantic policy gate
            all_ok = True
            for item in candidate_list:
                if not validate_text_semantic(item.what_to_expect, is_warning=True) or not validate_text_semantic(item.red_flag, is_warning=True):
                    all_ok = False
                    break
            
            if all_ok and len(candidate_list) == 3:
                forecast_list = candidate_list
                break
        except Exception:
            pass

    # 5. If it still fails, fall back to safe generic warnings (guarantees NO [CONTENT BLOCKED] strings)
    if not forecast_list or len(forecast_list) != 3:
        if detected_lang == "es":
            forecast_list = [
                EscalationStage(
                    stage=1,
                    what_to_expect="Intentarán ganarse su confianza y alejarlo de los canales oficiales. Nunca comparta sus datos de acceso ni códigos recibidos.",
                    red_flag="Solicitud de pasar a un chat privado fuera de la plataforma segura."
                ),
                EscalationStage(
                    stage=2,
                    what_to_expect="Le pedirán un pequeño pago o depósito inicial bajo falsos pretextos como tarifas de activación.",
                    red_flag="Solicitud de transferencia de dinero, recarga de saldo o depósitos criptográficos."
                ),
                EscalationStage(
                    stage=3,
                    what_to_expect="Le dirán que ha surgido una crisis o que requiere pagar impuestos adicionales para poder liberar o retirar sus fondos.",
                    red_flag="Exigencia de cargos de liberación para retirar dinero."
                )
            ]
        else: # Default English fallback
            forecast_list = [
                EscalationStage(
                    stage=1,
                    what_to_expect="They will try to build trust and isolate you from official platforms. Never share credentials or validation codes.",
                    red_flag="Request to move to a private messaging app."
                ),
                EscalationStage(
                    stage=2,
                    what_to_expect="They will request a small initial payment or deposit under false pretenses such as account activation fees.",
                    red_flag="Direct request for money transfers or crypto deposits."
                ),
                EscalationStage(
                    stage=3,
                    what_to_expect="They will invent a crisis or claim you must pay additional release fees or taxes to withdraw your funds.",
                    red_flag="Demanding advance fees or tax payments to retrieve money."
                )
            ]

    # 6. Save back to ctx.state for the Report Generator to include in the final JSON output
    ctx.state["escalation_forecast"] = forecast_list

    # Return the tactics list unchanged to maintain backward compatibility
    return node_input
