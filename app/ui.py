import json
import os
import sqlite3

import gradio as gr
from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from google.genai import types

from app.agent import app as adk_app

load_dotenv()


def get_tactics_count() -> int:
    try:
        with sqlite3.connect("data/scam_intel.db") as conn:
            return conn.execute("SELECT COUNT(*) FROM tactics").fetchone()[0]
    except Exception:
        return 0


async def analyze_message(message: str, api_key: str):
    if not message or not message.strip():
        return (
            "Please enter a message to analyze.",
            "{}",
            f"tactics catalogued: {get_tactics_count()}",
        )

    env_key = os.environ.get("GEMINI_API_KEY")
    active_key = api_key.strip() if api_key else env_key
    if not active_key:
        return (
            "❌ Error: GEMINI_API_KEY is not set. Please provide it in the input box or set it as an env var.",
            "{}",
            f"tactics catalogued: {get_tactics_count()}",
        )

    os.environ["GEMINI_API_KEY"] = active_key
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"

    runner = InMemoryRunner(app=adk_app)
    session = await runner.session_service.create_session(
        app_name=runner.app_name, user_id="ui_user"
    )

    result = None
    async for event in runner.run_async(
        user_id="ui_user",
        session_id=session.id,
        new_message=types.Content(
            role="user", parts=[types.Part.from_text(text=message)]
        ),
    ):
        if event.output is not None:
            result = event.output

    if not result:
        return (
            "No report generated.",
            "{}",
            f"tactics catalogued: {get_tactics_count()}",
        )

    data = result.model_dump() if hasattr(result, "model_dump") else result
    verdict = data.get("verdict", {})
    is_scam = verdict.get("is_scam", False)
    conf = verdict.get("confidence", 0.0)
    category = verdict.get("category", "unknown")

    verdict_str = (
        f"🛑 SCAM (Confidence: {conf * 100:.1f}%)"
        if is_scam
        else f"✅ NOT A SCAM (Confidence: {conf * 100:.1f}%)"
    )
    badge_color = "#ea4335" if is_scam else "#34a853"

    # Single-line HTML (no leading indentation) so gr.Markdown renders it as a
    # styled banner instead of treating the indented block as a code block.
    report_html = (
        f'<div style="border: 2px solid {badge_color}; border-radius: 8px; padding: 15px; margin-bottom: 20px; background-color: {badge_color}10;">'
        f'<h2 style="margin: 0; color: {badge_color};">{verdict_str}</h2>'
        f'<p style="margin: 5px 0 0 0;"><b>Category:</b> {category.upper()} | <b>Language:</b> {data.get("language", "en").upper()}</p>'
        f"</div>"
    )

    tactics_md = "### Detected Tactics\n| Name | Lever | Explanation |\n|---|---|---|\n"
    for t in data.get("tactics", []):
        tactics_md += (
            f"| `{t.get('name')}` | **{t.get('lever')}** | {t.get('explanation')} |\n"
        )
    if not data.get("tactics"):
        tactics_md = "### Detected Tactics\n*No specific tactics detected.*\n"

    forecast_md = "### Escalation Forecast\n"
    for f in sorted(
        data.get("escalation_forecast", []), key=lambda x: x.get("stage", 0)
    ):
        forecast_md += f"**Stage {f.get('stage')}: Expectation**\n{f.get('what_to_expect')}\n🚩 *Red Flag:* {f.get('red_flag')}\n\n"
    if not data.get("escalation_forecast"):
        forecast_md = "### Escalation Forecast\n*No escalation forecast available.*\n"

    protect_md = "### How to Protect Yourself\n" + "\n".join(
        [f"- {item}" for item in data.get("how_to_protect", [])]
    )
    links_md = "### Official Reporting Channels\n" + "\n".join(
        [
            f"- [{link.get('label')}]({link.get('url')})"
            for link in data.get("reporting_links", [])
        ]
    )

    report_md = f"""{report_html}

### Warning

> ⚠️ {data.get("warning", "")}

{tactics_md}
{forecast_md}
{protect_md}

{links_md}

---
*Disclaimer: {data.get("disclaimer")}*
"""
    return (
        report_md,
        json.dumps(data, indent=2, ensure_ascii=False),
        f"tactics catalogued: {get_tactics_count()}",
    )


with gr.Blocks(title="Scam Autopsy Demo UI") as demo:
    gr.Markdown("# 🔬 Scam Autopsy Demo UI")
    gr.Markdown(
        "Analyze suspicious messages using the defensive red-team replay simulation."
    )

    with gr.Row():
        txt_input = gr.Textbox(
            label="Suspicious Message", placeholder="Paste the message here...", lines=5
        )
        txt_key = gr.Textbox(
            label="Gemini API Key (optional if set in env)",
            type="password",
            placeholder="AI Studio Key...",
        )

    with gr.Row():
        btn_analyze = gr.Button("Analyze", variant="primary")
        txt_counter = gr.Textbox(
            label="Database Status",
            value=f"tactics catalogued: {get_tactics_count()}",
            interactive=False,
        )

    with gr.Row():
        md_output = gr.Markdown(label="Report Output")

    with gr.Accordion("Raw JSON", open=False):
        json_output = gr.JSON(label="Raw Output")

    btn_analyze.click(
        fn=analyze_message,
        inputs=[txt_input, txt_key],
        outputs=[md_output, json_output, txt_counter],
    )

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)
