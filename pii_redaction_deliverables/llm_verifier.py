import os
import json
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq


# ============================================================
# PROJECT / ENVIRONMENT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise RuntimeError(
        f"GROQ_API_KEY not found.\n"
        f"Expected .env file at: {ENV_FILE}"
    )

client = Groq(api_key=api_key)

MODEL = "llama-3.1-8b-instant"


# ============================================================
# CONSTANTS
# ============================================================

LLM_TYPES = {"NAME", "COMPANY"}

MIN_CONFIDENCE = 0.85

CONTEXT_SIZE = 120

BATCH_SIZE = 8


# ============================================================
# CLEAN JSON
# ============================================================

def clean_json_response(result_text):

    result_text = result_text.strip()

    if result_text.startswith("```json"):
        result_text = result_text[7:]

    elif result_text.startswith("```"):
        result_text = result_text[3:]

    if result_text.strip().endswith("```"):
        result_text = result_text.strip()[:-3]

    return result_text.strip()


# ============================================================
# VERIFY CANDIDATES
# ============================================================

def verify_candidates(
    text,
    candidates,
    batch_size=BATCH_SIZE
):

    verified = []

    # ========================================================
    # ONLY NAME + COMPANY
    # ========================================================

    candidates = [
        c
        for c in candidates
        if isinstance(c, dict)
        and c.get("type") in LLM_TYPES
    ]

    # ========================================================
    # FILTER
    # ========================================================

    filtered = []

    blocked_phrases = [
        "the company",
        "a company",
        "our company",
        "company",
        "limited",
        "private limited",
        "llp",
        "corporation",
        "board of directors",
        "shareholders",
        "management",
        "department",
        "committee",
        "director of",
        "employee of",
        "office of",
        "appointed by",
        "appointed as",
        "chartered engineer",
        "managing director",
        "executive director",
        "whole-time director"
    ]

    for candidate in candidates:

        value = str(
            candidate.get("text", "")
        ).strip()

        if not value:
            continue

        lower_value = value.lower()

        # Reject obvious generic phrases.
        #
        # IMPORTANT:
        # We do NOT reject "limited" blindly here because
        # legitimate company names can contain "Limited".
        if lower_value in {
            "the company",
            "a company",
            "our company",
            "the group",
            "promoter group",
            "management",
            "shareholders",
            "board of directors"
        }:
            continue

        if len(value) > 100:
            continue

        if any(
            char in value
            for char in [":", ";", "(", ")", "/"]
        ):
            continue

        filtered.append(candidate)

    # ========================================================
    # DEDUPLICATE
    # ========================================================

    unique = {}

    for candidate in filtered:

        key = (
            candidate["text"].strip().lower(),
            candidate["type"]
        )

        if key not in unique:
            unique[key] = candidate

    candidates = list(unique.values())

    print(
        f"\nLLM candidates after filtering: "
        f"{len(candidates)}"
    )

    # ========================================================
    # BATCH PROCESSING
    # ========================================================

    for i in range(
        0,
        len(candidates),
        batch_size
    ):

        batch = candidates[
            i:i + batch_size
        ]

        items = []

        for index, candidate in enumerate(batch):

            start = max(
                0,
                candidate["start"] - CONTEXT_SIZE
            )

            end = min(
                len(text),
                candidate["end"] + CONTEXT_SIZE
            )

            context = text[start:end]

            items.append({
                "id": index,
                "candidate": candidate["text"],
                "detected_type": candidate["type"],
                "context": context
            })

        # ====================================================
        # PROMPT
        # ====================================================

        prompt = f"""
You are a STRICT PII verification system.

Classify each candidate as either:

PERSON
or
COMPANY

Return is_pii=true ONLY when the candidate itself is
an identifiable person or identifiable organization.

==================================================
PERSON
==================================================

Valid:

"Sarthak Malvadkar"
"Rajesh Kushal Hegde"
"Pushpa Kushal Hegde"

Invalid:

"Board of Directors"
"Managing Director"
"shareholders"
"the Company"
"independent chartered engineer"

==================================================
COMPANY
==================================================

Valid examples:

"KSH International Limited"
"Bharat Bijlee Limited"
"ICICI Securities Limited"
"HDFC Bank Limited"
"Nuvama Wealth Management Limited"

A company can contain:

Limited
Ltd
LLP
Bank
Securities
Technologies
Industries
Holdings
Corporation

These are NOT automatically false positives.

Invalid:

"the Company"
"our Company"
"a company"
"the Group"
"Promoter Group"
"management"
"shareholders"
"customers"
"financial institution"

==================================================
CRITICAL RULE
==================================================

The candidate itself must be the entity.

Do NOT extract a person from a larger phrase.

Do NOT classify a generic phrase as a company.

Be conservative.

If uncertain:

is_pii=false

When is_pii=true:

PERSON -> type must be "PERSON"

COMPANY -> type must be "COMPANY"

Return ONLY valid JSON.

Required format:

{{
    "results": [
        {{
            "id": 0,
            "is_pii": true,
            "type": "PERSON",
            "confidence": 0.95,
            "reason": "Actual person's name"
        }},
        {{
            "id": 1,
            "is_pii": true,
            "type": "COMPANY",
            "confidence": 0.95,
            "reason": "Identifiable company"
        }}
    ]
}}

Candidates:

{json.dumps(items, ensure_ascii=False)}
"""

        # ====================================================
        # API CALL
        # ====================================================

        try:

            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a strict PII classifier. "
                            "Return JSON only."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0,
                max_tokens=1200
            )

            result_text = (
                response
                .choices[0]
                .message
                .content
                .strip()
            )

            result_text = clean_json_response(
                result_text
            )

            result = json.loads(result_text)

            # =================================================
            # HANDLE BOTH:
            #
            # {"results": [...]}
            #
            # OR
            #
            # [...]
            # =================================================

            if isinstance(result, dict):

                results = result.get(
                    "results",
                    []
                )

            elif isinstance(result, list):

                results = result

            else:

                results = []

            if not isinstance(results, list):

                results = []

            # =================================================
            # PROCESS RESULTS
            # =================================================

            for item in results:

                # Prevent:
                # 'list' object has no attribute 'get'

                if not isinstance(item, dict):
                    continue

                if item.get("is_pii") is not True:
                    continue

                idx = item.get("id")

                if not isinstance(idx, int):
                    continue

                if idx < 0 or idx >= len(batch):
                    continue

                original = batch[idx]

                original_type = original.get(
                    "type"
                )

                returned_type = item.get(
                    "type"
                )

                # =================================================
                # TYPE MUST MATCH
                # =================================================

                if original_type == "NAME":

                    if returned_type != "PERSON":
                        continue

                elif original_type == "COMPANY":

                    if returned_type != "COMPANY":
                        continue

                else:
                    continue

                # =================================================
                # CONFIDENCE
                # =================================================

                try:

                    confidence = float(
                        item.get(
                            "confidence",
                            0
                        )
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    confidence = 0

                if confidence < MIN_CONFIDENCE:
                    continue

                # =================================================
                # SAVE VERIFIED ENTITY
                # =================================================

                candidate_text = (
                    original["text"]
                    .strip()
                )

                verified.append({

                    "text": candidate_text,

                    "type": returned_type,

                    "start": original["start"],

                    "end": original["end"],

                    "confidence": confidence,

                    "reason": item.get(
                        "reason",
                        "Verified PII"
                    )
                })

            print(
                f"LLM batch "
                f"{i // batch_size + 1} completed "
                f"({len(batch)} candidates)"
            )

        except json.JSONDecodeError as e:

            print(
                f"LLM batch "
                f"{i // batch_size + 1} failed: "
                f"Invalid JSON: {e}"
            )

        except Exception as e:

            print(
                f"LLM batch "
                f"{i // batch_size + 1} failed: {e}"
            )

    # ========================================================
    # DEDUPLICATE
    # ========================================================

    final_unique = {}

    for item in verified:

        key = (
            item["text"].lower(),
            item["type"],
            item["start"],
            item["end"]
        )

        if key not in final_unique:
            final_unique[key] = item

    verified = list(
        final_unique.values()
    )

    # ========================================================
    # SORT
    # ========================================================

    verified.sort(
        key=lambda x: x["start"]
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    person_count = sum(
        1
        for x in verified
        if x["type"] == "PERSON"
    )

    company_count = sum(
        1
        for x in verified
        if x["type"] == "COMPANY"
    )

    print("\n==========================================")
    print("FINAL VERIFIED PII")
    print("==========================================")

    print(
        "Verified persons:",
        person_count
    )

    print(
        "Verified companies:",
        company_count
    )

    print(
        "Total verified:",
        len(verified)
    )

    for item in verified:

        print(
            f"{item['type']} | "
            f"{item['text']} | "
            f"confidence={item['confidence']}"
        )

    return verified