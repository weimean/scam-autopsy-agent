# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import google.auth
from google.adk.apps import App
from google.adk.workflow import Workflow, START
from google.adk.events.event import Event

# Import custom nodes
from app.nodes.intake import intake_classifier
from app.nodes.adversarial import adversarial_core
from app.nodes.extractor import tactic_extractor
from app.nodes.generator import report_generator
from app.schemas import ClassifierOutput, ReportOutput

# Ensure GCP configuration is loaded
try:
    _, project_id = google.auth.default()
    if project_id:
        os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
except Exception:
    pass

# Default region and Vertex AI settings
if os.environ.get("GEMINI_API_KEY"):
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"
else:
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0290068239")
    os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

def check_scam(node_input: ClassifierOutput) -> Event:
    """Route based on whether a scam is detected with high confidence."""
    # Store classifier output in state for the generator node to access
    if node_input.is_scam and node_input.confidence >= 0.5:
        return Event(
            output=node_input,
            route="scam",
            state={"classifier_output": node_input}
        )
    return Event(
        output=node_input,
        route="no_scam",
        state={"classifier_output": node_input}
    )

# Edge definitions mapping the system flow
edges = [
    # 1. Intake & Classification
    (START, intake_classifier),
    (intake_classifier, check_scam),
    
    # 2. Conditional branch
    (check_scam, {
        "scam": adversarial_core,
        "no_scam": report_generator,
    }),
    
    # 3. Rest of the scam detection path
    (adversarial_core, tactic_extractor),
    (tactic_extractor, report_generator),
]

root_agent = Workflow(
    name="scam_autopsy_workflow",
    edges=edges,
    description="Multi-agent Graph simulating scam pitches defensively to extract tactics.",
    output_schema=ReportOutput,
)

app = App(
    root_agent=root_agent,
    name="app",
)
