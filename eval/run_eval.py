"""
Evaluation runner for ISO 27001 chatbot.
Tests the LLM mapper against 20 ambiguous answers and reports pass/fail.
Expects ≥ 16/20 to pass.
"""

import json
import sys
import os

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.llm_mapper import map_answer_to_controls

# Load test cases
eval_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(eval_dir, "ambiguous_answers.json")) as f:
    cases = json.load(f)

# Load control map
with open(os.path.join(os.path.dirname(eval_dir), "data", "control_map.json")) as f:
    control_map = json.load(f)

results = []
passed = 0
total = len(cases)

print("=" * 60)
print("ISO 27001 Chatbot — Adversarial Evaluation")
print("=" * 60)
print()

for case in cases:
    predicted = map_answer_to_controls(case["question_id"], case["answer"], control_map)
    expected = set(case["expected_ids"])
    got = set(predicted)

    # Check for hallucinated IDs (IDs not in the control map at all)
    all_known_ids = set()
    for q_data in control_map.values():
        for cid in q_data["control_ids"]:
            all_known_ids.add(cid)

    hallucinated = got - all_known_ids

    if hallucinated:
        correct = False
        reason = f"HALLUCINATED IDs: {hallucinated}"
    else:
        correct = expected == got
        reason = ""

    if correct:
        passed += 1

    status = "✓" if correct else "✗"
    print(f"  {status} {case['id']} (Q{case['question_id']}): expected={case['expected_ids']} got={sorted(got)}")
    if reason:
        print(f"       Reason: {reason}")
    print()

    results.append({
        "id": case["id"],
        "question_id": case["question_id"],
        "answer": case["answer"],
        "expected": case["expected_ids"],
        "predicted": sorted(got),
        "pass": correct,
        "reason": reason if reason else "",
    })

print("=" * 60)
print(f"  Result: {passed}/{total} passed")
print("=" * 60)

# Determine overall pass/fail
threshold = 16
overall_pass = passed >= threshold
print(f"  Threshold: {threshold}/20")
print(f"  Overall: {'✓ PASS' if overall_pass else '✗ FAIL'}")
print("=" * 60)

# Write mapping.json artefact
output = {
    "score": f"{passed}/{total}",
    "threshold": f"{threshold}/{total}",
    "overall_pass": overall_pass,
    "results": results,
}

with open(os.path.join(eval_dir, "mapping.json"), "w") as f:
    json.dump(output, f, indent=2)

sys.exit(0 if overall_pass else 1)
