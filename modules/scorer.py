"""
Domain scoring module for ISO 27001 readiness assessment.
Calculates scores 0-100 per domain based on covered controls.
"""

from modules.questionnaire import DOMAIN_QUESTIONS, get_all_domains


def calculate_domain_scores(session_results: list[dict], control_map: dict) -> dict:
    """
    Input: list of {question_id, matched_controls, user_answer}
    Output: {
        "Organizational Controls": {"score": 72, "matched": 5, "total": 7, "gaps": ["A.5.3"]},
        ...
    }
    Score = (covered questions / total questions in domain) * 100
    A question is "covered" if at least one expected control ID is matched.
    """
    # Build lookup: question_id -> matched control IDs
    result_lookup = {}
    for r in session_results:
        result_lookup[r["question_id"]] = r.get("matched_controls", [])

    domain_scores = {}

    for domain in get_all_domains():
        q_ids = DOMAIN_QUESTIONS[domain]
        total = len(q_ids)
        covered = 0
        gaps = []

        for q_id in q_ids:
            q_data = control_map.get(q_id, {})
            expected_ids = q_data.get("control_ids", [])
            matched_ids = result_lookup.get(q_id, [])

            # Check if at least one expected ID was matched
            is_covered = any(cid in expected_ids for cid in matched_ids)

            if is_covered:
                covered += 1
            else:
                # Add unmatched expected IDs to gaps
                for eid in expected_ids:
                    if eid not in matched_ids and eid not in gaps:
                        gaps.append(eid)

        score = round((covered / total) * 100) if total > 0 else 0

        domain_scores[domain] = {
            "score": score,
            "matched": covered,
            "total": total,
            "gaps": gaps,
        }

    return domain_scores


def calculate_partial_scores(session_results: list[dict], control_map: dict) -> dict:
    """
    Same logic as calculate_domain_scores but works on incomplete
    answers (fewer than 30). Returns 0 for domains with no answers yet.
    Never crashes on empty input.
    """
    if not isinstance(session_results, list):
        session_results = []
    if not isinstance(control_map, dict):
        control_map = {}

    result_lookup = {}
    answered_q_ids = set()
    for r in session_results:
        if isinstance(r, dict) and "question_id" in r:
            q_id = r["question_id"]
            result_lookup[q_id] = r.get("matched_controls", [])
            answered_q_ids.add(q_id)

    domain_scores = {}

    for domain in get_all_domains():
        q_ids = DOMAIN_QUESTIONS[domain]
        total = len(q_ids)

        # Check if there are any answers for this domain yet
        has_answers = any(q_id in answered_q_ids for q_id in q_ids)
        if not has_answers:
            domain_scores[domain] = {
                "score": 0,
                "matched": 0,
                "total": total,
                "gaps": [],
            }
            continue

        covered = 0
        gaps = []

        for q_id in q_ids:
            q_data = control_map.get(q_id, {})
            expected_ids = q_data.get("control_ids", [])
            matched_ids = result_lookup.get(q_id, [])

            # Check if at least one expected ID was matched
            is_covered = any(cid in expected_ids for cid in matched_ids)

            if is_covered:
                covered += 1
            else:
                # Add unmatched expected IDs to gaps only if answered
                if q_id in answered_q_ids:
                    for eid in expected_ids:
                        if eid not in matched_ids and eid not in gaps:
                            gaps.append(eid)

        score = round((covered / total) * 100) if total > 0 else 0

        domain_scores[domain] = {
            "score": score,
            "matched": covered,
            "total": total,
            "gaps": gaps,
        }

    return domain_scores


def get_overall_score(domain_scores: dict) -> int:
    """Calculate overall readiness score (average of all domain scores)."""
    if not domain_scores:
        return 0
    scores = [v["score"] for v in domain_scores.values()]
    return round(sum(scores) / len(scores))

