"""
LLM mapping module — calls Google Gemini Flash to map user answers
to ISO 27001:2022 Annex A control IDs.
Strictly filters output to only allowed IDs from control_map.json.
"""

import json
import re
import google.generativeai as genai


def map_answer_to_controls(question_id: str, user_answer: str, control_map: dict) -> list[str]:
    """
    Calls Gemini Flash with a strict system prompt.
    Returns list of matched control IDs from control_map only.
    Never returns IDs not in the map.
    """
    question_data = control_map.get(question_id)
    if not question_data:
        return []

    allowed_ids = list(question_data["control_ids"])
    question_text = question_data["question"]
    domain = question_data["domain"]
    keywords = question_data.get("keywords", [])

    # Build a strict system prompt to prevent hallucination
    prompt = f"""You are an ISO 27001:2022 compliance analyst. Your task is to map a user's freeform answer to the correct Annex A control IDs.

QUESTION: {question_text}
DOMAIN: {domain}
USER ANSWER: {user_answer}

ALLOWED CONTROL IDs (ONLY choose from this list — do NOT invent any IDs): {json.dumps(allowed_ids)}

RELEVANT KEYWORDS (for context): {json.dumps(keywords)}

RULES — You MUST follow these exactly:
1. Return ONLY a valid JSON array of strings (e.g., ["A.5.1"] or []).
2. ONLY include control IDs from the ALLOWED list above. NEVER invent or add any control ID not in the list.
3. If the user answer mentions practices that suggest a control is in place, include the matching ID.
4. If the answer is vague, partial, or non-existent, still pick only from the allowed list based on what is described.
5. If nothing matches at all, return an empty array [].
6. Do NOT include any text outside the JSON array — no markdown, no explanation.

Respond with ONLY the JSON array:"""

    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        # Try to extract JSON array from response
        # Handle cases where Gemini might wrap in markdown code blocks
        json_match = re.search(r'\[.*?\]', raw_text, re.DOTALL)
        if json_match:
            raw_text = json_match.group()

        parsed = json.loads(raw_text)
        if not isinstance(parsed, list):
            return []

        # Filter: only return IDs that are in the allowed list
        result = [cid for cid in parsed if cid in allowed_ids]
        if result:
            return result
        # If Gemini returned empty but we think there's a match, try fallback
        return _keyword_fallback(user_answer, allowed_ids, keywords)

    except (json.JSONDecodeError, AttributeError, Exception) as e:
        # If parsing fails, try a keyword-based fallback approach
        return _keyword_fallback(user_answer, allowed_ids, keywords)


def _keyword_fallback(user_answer: str, allowed_ids: list[str], keywords: list[str]) -> list[str]:
    """
    Intelligent keyword-based fallback if Gemini parsing fails.
    Uses word-level matching, stemming, and context analysis.
    """
    answer_lower = user_answer.lower().strip()
    if not answer_lower:
        return []

    # ===== STEP 1: Exact keyword match =====
    for keyword in keywords:
        if keyword.lower() in answer_lower:
            return allowed_ids

    # ===== STEP 2: Word-level partial matching =====
    # Split keywords into individual meaningful words and check if any appear
    answer_words = set(re.findall(r'\b\w+\b', answer_lower))
    keyword_words = set()
    for kw in keywords:
        for w in kw.lower().split():
            # Clean punctuation
            w_clean = re.sub(r'[^a-z0-9]', '', w)
            if len(w_clean) > 2:  # Skip very short words
                keyword_words.add(w_clean)

    # Check for word overlap between answer and keywords
    for kw_word in keyword_words:
        for ans_word in answer_words:
            # Check if keyword word is contained in answer word or vice versa
            if kw_word in ans_word or ans_word in kw_word:
                return allowed_ids
            # Check for common stems (first 4+ chars)
            min_len = min(len(kw_word), len(ans_word))
            if min_len >= 4 and kw_word[:min_len] == ans_word[:min_len]:
                return allowed_ids

    # ===== STEP 3: Check for negative/reactive patterns that indicate ABSENCE =====
    # These patterns suggest the control is NOT in place — check BEFORE positive
    negative_patterns = [
        "no plan", "no process", "no policy", "no formal",
        "don't have", "do not have", "haven't got",
        "we don't", "we do not", "not implemented",
        "we figure it out", "as we go", "when something breaks",
        "ad-hoc", "ad hoc", "not documented",
        "we don't know", "we have no", "we've no",
        "there is no", "there's no", "isn't any",
        "no real", "not really a", "not any",
        "nothing in place", "nothing formal",
        "we wing it", "we improvise", "we make it up",
        "no one knows", "not assigned",
        "we don't track", "we don't log",
    ]

    for neg in negative_patterns:
        if neg in answer_lower:
            return []

    # ===== STEP 4: Context-based positive matching =====
    # Check for positive action verbs that suggest the practice exists
    positive_actions = [
        "we ", "we've", "we're", "we have", "we do", "we use", "we apply",
        "we conduct", "we perform", "we maintain", "we enforce",
        "we require", "we provide", "we review", "we test",
        "we monitor", "we check", "we run", "we do",
        "we implemented", "we set up", "we built",
        "we did", "we try", "we usually", "we sometimes",
        "it is", "it's", "they are", "there is",
        "implemented", "in place", "covered",
        "automatically", "automatic", "regularly",
        "new hires", "onboarding", "when someone",
        "by default", "counts right",
    ]

    for action in positive_actions:
        if action in answer_lower:
            return allowed_ids

    # ===== STEP 5: Hedging/partial indicators =====
    hedging = [
        "kind of", "sort of", "generally", "mostly",
        "i think", "not sure", "probably",
        "pretty much", "on and off",
        "for the most part", "as needed",
        "when necessary", "if required",
        "unless", "not really", "not exactly",
        "we tell", "we handle",
        "once", "sometimes",
    ]

    for h in hedging:
        if h in answer_lower:
            return allowed_ids

    # ===== STEP 6: Last resort — check for any meaningful content =====
    # If the answer has substantial content (more than a few words), be lenient
    meaningful_words = [w for w in answer_words if len(w) > 3]
    if len(meaningful_words) >= 3:
        # Check for negation patterns that would indicate absence
        negation = ["no ", "not ", "don't", "doesn't", "haven't", "hasn't",
                     "won't", "can't", "lack", "absent", "missing", "none",
                     "nothing", "nobody", "we don't", "we do not",
                     "we haven't", "we have not", "not implemented"]
        is_negative = any(n in answer_lower for n in negation)
        if not is_negative:
            return allowed_ids

    return []


def _contains_word_stem(word: str, text: str) -> bool:
    """Check if a word stem appears in text, matching whole words or parts."""
    pattern = r'\b' + re.escape(word) + r'\w*\b'
    return bool(re.search(pattern, text, re.IGNORECASE))
