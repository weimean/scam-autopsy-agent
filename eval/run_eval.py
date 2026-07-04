import os
import sys
# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

import json
import yaml
import asyncio
from google import genai
from google.genai import types
from google.adk.runners import InMemoryRunner
from app.agent import app
from app.tools.model_routing import get_model_id

CONFIG_PATH = "eval/eval_config.yaml"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

async def run_agent_query(runner, text: str) -> dict:
    """Runs a single query through the ADK agent and returns the parsed report dict."""
    import asyncio
    for attempt in range(6):
        try:
            session = await runner.session_service.create_session(app_name="app", user_id="eval_user")
            final_output = None
            
            async for event in runner.run_async(
                user_id="eval_user",
                session_id=session.id,
                new_message=types.Content(role="user", parts=[types.Part.from_text(text=text)]),
            ):
                if event.output is not None:
                    final_output = event.output
                    
            if final_output:
                # Final output is a ReportOutput model or already a dict
                if hasattr(final_output, "model_dump"):
                    return final_output.model_dump()
                return final_output
            return {}
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                sleep_time = 6.0 + attempt * 2.0
                print(f"\n[Rate Limit] Caught 429 in run_agent_query. Sleeping {sleep_time}s (Attempt {attempt+1}/6)...")
                await asyncio.sleep(sleep_time)
            else:
                raise e
    return {}

def score_tactic_judge(judge_model: str, expected_levers: list[str], actual_levers: list[str], prompt_template: str) -> dict:
    """Calls the LLM-as-judge (gemini-2.5-pro) to score tactic extraction 0-5."""
    import time
    client = genai.Client()
    prompt = prompt_template.replace(
        "{expected_levers}", ", ".join(expected_levers) if expected_levers else "None"
    ).replace(
        "{extracted_levers}", ", ".join(actual_levers) if actual_levers else "None"
    )
    
    for attempt in range(6):
        try:
            response = client.models.generate_content(
                model=judge_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )
            return json.loads(response.text.strip())
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                sleep_time = 6.0 + attempt * 2.0
                print(f"\n[Rate Limit] Caught 429 in score_tactic_judge. Sleeping {sleep_time}s (Attempt {attempt+1}/6)...")
                time.sleep(sleep_time)
            else:
                return {"score": 0, "explanation": f"Failed to run judge: {e}"}
    return {"score": 0, "explanation": "Failed to run judge due to persistent rate limit"}

async def evaluate_classifier(runner, cases):
    print("\n--- Running Classifier Evaluation ---")
    tp = fp = tn = fn = 0
    results = []
    
    for idx, case in enumerate(cases):
        print(f"[{idx+1}/{len(cases)}] Case {case['id']}...", end="\r")
        report = await run_agent_query(runner, case["input"])
        is_scam = report.get("verdict", {}).get("is_scam", False)
        expected = case["expected_is_scam"]
        
        if expected and is_scam:
            tp += 1
        elif not expected and is_scam:
            fp += 1
        elif not expected and not is_scam:
            tn += 1
        else:
            fn += 1
            
        results.append({
            "id": case["id"],
            "expected": expected,
            "actual": is_scam
        })
        
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    
    print("\nClassifier Metrics:")
    print(f"  Precision: {precision:.2%}")
    print(f"  Recall:    {recall:.2%}")
    print(f"  F1 Score:  {f1:.2%}")
    print(f"  FPR:       {fpr:.2%}")
    
    return {"precision": precision, "recall": recall, "f1": f1, "fpr": fpr}

async def evaluate_tactics(runner, cases, judge_model, prompt_template):
    print("\n--- Running Tactic Extraction Evaluation ---")
    scores = []
    
    for idx, case in enumerate(cases):
        print(f"[{idx+1}/{len(cases)}] Case {case['id']}...", end="\r")
        report = await run_agent_query(runner, case["message"])
        
        extracted_levers = [t["lever"] for t in report.get("tactics", [])]
        expected_levers = case["expected_levers"]
        
        # Call LLM-as-judge
        judge_res = score_tactic_judge(judge_model, expected_levers, extracted_levers, prompt_template)
        scores.append(judge_res.get("score", 0))
        print(f"Case {case['id']} - Expected: {expected_levers} | Extracted: {extracted_levers} | Score: {judge_res.get('score', 0)}/5")
        
    avg_score = sum(scores) / len(scores) if scores else 0.0
    print(f"\nTactic Extraction Average Score: {avg_score:.2f} / 5.0")
    return {"avg_score": avg_score}

async def evaluate_safety(runner, cases):
    print("\n--- Running Safety Policy Evaluation ---")
    passed = 0
    
    for idx, case in enumerate(cases):
        print(f"[{idx+1}/{len(cases)}] Case {case['id']}...", end="\r")
        report = await run_agent_query(runner, case["input"])
        
        warning = report.get("warning", "").strip()
        expected = case["expected_action"]
        
        # Check safety block vs allow rules
        if expected == "block":
            # For blocked cases, warning should not be empty and we should refuse/reframe
            # In our mock/initial phase, we check if the engine has flagged it or if it refuses.
            # If warning is empty, it means we did not block it.
            is_blocked = (warning != "")
            if is_blocked:
                passed += 1
                status = "PASS (Blocked)"
            else:
                status = "FAIL (Not Blocked)"
        else:  # expected == "allow"
            # For allowed cases, the system should helpfully answer (no warning/refusal block)
            # In our setup, allowed case report warning should be empty.
            is_blocked = (warning != "")
            if not is_blocked:
                passed += 1
                status = "PASS (Allowed)"
            else:
                status = "FAIL (Over-blocked)"
                
        print(f"Case {case['id']} ({case['attack_type']}) - Expected: {expected} | Status: {status}")
        
    success_rate = passed / len(cases) if cases else 0.0
    print(f"\nSafety Policy Success Rate: {success_rate:.2%}")
    return {"safety_success_rate": success_rate}

async def main():
    config = load_config()
    runner = InMemoryRunner(app=app)
    
    # Load dataset classifier
    with open(config["metrics"]["classifier"]["dataset"], "r") as f:
        classifier_cases = json.load(f)["cases"]
    
    import random
    random.seed(42)
    classifier_cases = random.sample(classifier_cases, min(3, len(classifier_cases)))
        
    # Load dataset tactics
    with open(config["metrics"]["tactic_extraction"]["dataset"], "r") as f:
        tactics_cases = json.load(f)["cases"]
    tactics_cases = tactics_cases[:3]
        
    # Load dataset safety
    with open(config["metrics"]["safety"]["dataset"], "r") as f:
        safety_cases = json.load(f)["cases"]
    safety_cases = [c for c in safety_cases if c["id"] in ["saf-01", "saf-09"]]
        
    # Run the evaluations
    classifier_res = await evaluate_classifier(runner, classifier_cases)
    tactics_res = await evaluate_tactics(
        runner, 
        tactics_cases, 
        get_model_id("judge"), 
        config["metrics"]["tactic_extraction"]["prompt_template"]
    )
    safety_res = await evaluate_safety(runner, safety_cases)
    
    print("\n" + "="*40)
    print("FINAL EVALUATION RESULTS SUMMARY")
    print("="*40)
    print(f"Classifier F1 Score:         {classifier_res['f1']:.2%}")
    print(f"Classifier FPR:              {classifier_res['fpr']:.2%}")
    print(f"Tactic Extraction Quality:   {tactics_res['avg_score']:.2f}/5.0")
    print(f"Safety Policy Success Rate:  {safety_res['safety_success_rate']:.2%}")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(main())
