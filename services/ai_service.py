import json
import os

from dotenv import load_dotenv
from google import genai


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not configured. "
        "Please add it to your .env file."
    )


# ============================================================
# GEMINI CLIENT
# ============================================================

client = genai.Client(
    api_key=API_KEY
)


# IMPORTANT:
# Your previous API error specifically recommended
# gemini-3.6-flash. However, current Google documentation
# also documents gemini-3.7-flash for Interactions.
#
# We use the value from .env so you can change it without
# modifying this Python file.

MODEL_NAME = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.7-flash"
)


# ============================================================
# SYSTEM INSTRUCTION
# ============================================================

SYSTEM_INSTRUCTION = """
You are BhoomiMitra AI, an agricultural land
verification decision-support assistant.

Your job is to understand agricultural land documents,
extract factual information, compare supplied information,
and explain verification results.

IMPORTANT LIMITATIONS:

You are NOT a government authority.

You are NOT a lawyer.

You must NEVER claim that ownership or legal title has
been legally certified merely because the AI found a match.

You must distinguish clearly between:

1. Information extracted from the uploaded document
2. Information supplied by the reference dataset
3. Matching information
4. Mismatching information
5. Missing information
6. Information requiring human, legal, or government verification

Never invent:

- survey numbers
- owner names
- land areas
- villages
- government records
- mutation records
- boundary information
- legal conclusions

If information is missing, say that it is missing.

If information conflicts, clearly identify the conflict.

The deterministic verification engine calculates the
verification score. You must NOT independently change,
override, or invent the score.

Your role is to extract, explain, summarize risks,
and provide sensible next steps.
"""


# ============================================================
# JSON HELPERS
# ============================================================

def clean_json(text):
    """
    Convert Gemini JSON text into a Python dictionary.

    Handles occasional markdown code fences defensively.
    """

    if not text:
        return {}

    text = text.strip()

    if text.startswith("```json"):
        text = text[len("```json"):].strip()

    elif text.startswith("```"):
        text = text[len("```"):].strip()

    if text.endswith("```"):
        text = text[:-3].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Gemini returned invalid JSON: {error}\n"
            f"Response was:\n{text}"
        )


# ============================================================
# GENERIC INTERACTIONS API CALL
# ============================================================

def create_interaction(
    prompt,
    response_schema=None,
    max_output_tokens=1500
):
    """
    Send a request using the current Gemini Interactions API.

    This replaces the old:

        client.models.generate_content(...)

    approach.
    """

    request = {
        "model": MODEL_NAME,
        "system_instruction": SYSTEM_INSTRUCTION,
        "input": prompt,
        "generation_config": {
            "max_output_tokens": max_output_tokens
        }
    }

    # Structured JSON response when a schema is supplied.
    if response_schema is not None:
        request["response_format"] = {
            "type": "text",
            "mime_type": "application/json",
            "schema": response_schema
        }

    interaction = client.interactions.create(
        **request
    )

    # Current SDK convenience property.
    output_text = getattr(
        interaction,
        "output_text",
        None
    )

    if output_text:
        return output_text

    # Defensive fallback for SDK/schema variations.
    try:
        for step in reversed(interaction.steps):
            if getattr(step, "type", "") == "model_output":

                content = getattr(
                    step,
                    "content",
                    []
                )

                for item in content:
                    text = getattr(
                        item,
                        "text",
                        None
                    )

                    if text:
                        return text
    except Exception:
        pass

    raise RuntimeError(
        "Gemini returned an interaction without "
        "usable text output."
    )


# ============================================================
# 1. DOCUMENT EXTRACTION
# ============================================================

def extract_land_data_from_text(document_text):

    prompt = f"""
Analyze the following agricultural land document.

Extract ONLY information that is explicitly present
in the document.

Return structured information using the requested schema.

IMPORTANT:

- Do not guess.
- Do not infer missing values.
- If a value is missing, return an empty string.
- area_acres must be a number when clearly available.
- Convert units to acres only when the conversion is
  unambiguous.
- Preserve the actual owner name exactly as written.
- Preserve the survey number exactly as written.

DOCUMENT:

{document_text[:30000]}
"""

    response_schema = {
        "type": "object",
        "properties": {
            "survey_number": {
                "type": "string"
            },
            "village": {
                "type": "string"
            },
            "taluk": {
                "type": "string"
            },
            "district": {
                "type": "string"
            },
            "state": {
                "type": "string"
            },
            "area_acres": {
                "type": [
                    "number",
                    "null"
                ]
            },
            "owner": {
                "type": "string"
            },
            "mutation_status": {
                "type": "string"
            },
            "document_type": {
                "type": "string"
            }
        },
        "required": [
            "survey_number",
            "village",
            "taluk",
            "district",
            "state",
            "area_acres",
            "owner",
            "mutation_status",
            "document_type"
        ]
    }

    response = create_interaction(
        prompt=prompt,
        response_schema=response_schema,
        max_output_tokens=1000
    )

    return clean_json(response)


# ============================================================
# 2. VERIFICATION EXPLANATION
# ============================================================

def generate_land_explanation(
    extracted,
    reference,
    verification
):

    prompt = f"""
Analyze this BhoomiMitra land verification result.

DOCUMENT-EXTRACTED INFORMATION:
{json.dumps(extracted, indent=2, ensure_ascii=False)}

REFERENCE INFORMATION:
{json.dumps(reference, indent=2, ensure_ascii=False)}

DETERMINISTIC VERIFICATION RESULT:
{json.dumps(verification, indent=2, ensure_ascii=False)}

Explain the result for a normal agricultural land buyer.

Return:

1. A short summary
2. Why the verification score has this value
3. Important risks
4. Actions the buyer should take
5. Actions the seller should take
6. A legal/verification disclaimer

IMPORTANT:

- Explain the score using ONLY the supplied verification result.
- Do not change the score.
- Do not invent additional risks.
- Clearly mention important mismatches.
- If the document and reference record disagree,
  explain exactly what differs.
- Never claim legal ownership is certified.
- Never claim government approval unless it is explicitly
  present in the supplied information.
- This is decision-support, not legal title certification.
"""

    response_schema = {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string"
            },
            "why_score": {
                "type": "string"
            },
            "risks": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            "buyer_actions": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            "seller_actions": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            "disclaimer": {
                "type": "string"
            }
        },
        "required": [
            "summary",
            "why_score",
            "risks",
            "buyer_actions",
            "seller_actions",
            "disclaimer"
        ]
    }

    response = create_interaction(
        prompt=prompt,
        response_schema=response_schema,
        max_output_tokens=1500
    )

    return clean_json(response)


# ============================================================
# 3. BUYER AI ASSISTANT
# ============================================================

def ask_bhoomimitra(question, property_data):

    prompt = f"""
A buyer is asking a question about an agricultural
land property.

PROPERTY INFORMATION:

{json.dumps(
    property_data,
    indent=2,
    ensure_ascii=False
)}

BUYER QUESTION:

{question}

Answer the buyer clearly and conservatively.

RULES:

- Use only the supplied property information.
- Do not invent government information.
- Do not invent missing property information.
- Do not certify ownership.
- Do not provide definitive legal advice.
- If the information is insufficient, clearly say so.
- Recommend appropriate human, legal, or government
  verification when necessary.
- Keep the answer understandable to a normal buyer.
"""

    response = create_interaction(
        prompt=prompt,
        response_schema=None,
        max_output_tokens=700
    )

    return response


# ============================================================
# GEMINI CONNECTION TEST
# ============================================================

def test_gemini_connection():

    response = create_interaction(
        prompt=(
            "Respond with exactly: "
            "BhoomiMitra AI Gemini connection is working."
        ),
        response_schema=None,
        max_output_tokens=50
    )

    return response