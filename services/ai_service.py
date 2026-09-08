import json
import os
import requests

from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY"
)

MODEL_NAME = os.getenv(
    "OPENROUTER_MODEL",
    "openrouter/free"
)

OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
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

You must NEVER claim that ownership or legal title
has been legally certified by this system.

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

The deterministic Python verification engine calculates
the verification score.

You must NOT independently change, override, or invent
the verification score.

Your role is to extract, explain, summarize risks,
and provide sensible next steps.
"""


# ============================================================
# OPENROUTER CALL
# ============================================================

def call_openrouter(
    prompt,
    max_tokens=1500,
    temperature=0.2
):

    if not OPENROUTER_API_KEY:

        raise RuntimeError(
            "OPENROUTER_API_KEY is not configured."
        )

    headers = {

        "Authorization":
            f"Bearer {OPENROUTER_API_KEY}",

        "Content-Type":
            "application/json",

        "HTTP-Referer":
            "https://bhoomimitra-3.onrender.com",

        "X-Title":
            "BhoomiMitra AI"
    }

    payload = {

        "model":
            MODEL_NAME,

        "messages": [

            {
                "role":
                    "system",

                "content":
                    SYSTEM_INSTRUCTION
            },

            {
                "role":
                    "user",

                "content":
                    prompt
            }

        ],

        "temperature":
            temperature,

        "max_tokens":
            max_tokens
    }

    try:

        response = requests.post(

            OPENROUTER_URL,

            headers=headers,

            json=payload,

            timeout=90
        )

    except requests.Timeout:

        raise RuntimeError(
            "OpenRouter request timed out. "
            "Please try again."
        )

    except requests.RequestException as error:

        raise RuntimeError(
            "Unable to connect to OpenRouter: "
            f"{error}"
        )

    # --------------------------------------------------------
    # HTTP ERROR
    # --------------------------------------------------------

    if response.status_code != 200:

        try:

            error_data = response.json()

            error_object = error_data.get(
                "error",
                {}
            )

            error_message = error_object.get(
                "message",
                response.text
            )

        except Exception:

            error_message = response.text

        raise RuntimeError(
            f"OpenRouter API error "
            f"({response.status_code}): "
            f"{error_message}"
        )

    # --------------------------------------------------------
    # JSON RESPONSE
    # --------------------------------------------------------

    try:

        data = response.json()

    except ValueError:

        raise RuntimeError(
            "OpenRouter returned invalid JSON."
        )

    # --------------------------------------------------------
    # CHOICES
    # --------------------------------------------------------

    choices = data.get(
        "choices",
        []
    )

    if not choices:

        raise RuntimeError(
            "OpenRouter returned no choices."
        )

    message = choices[0].get(
        "message",
        {}
    )

    content = message.get(
        "content"
    )

    if isinstance(
        content,
        list
    ):

        content = "".join(

            item.get(
                "text",
                ""
            )

            for item in content

            if isinstance(
                item,
                dict
            )
        )

    if not content:

        raise RuntimeError(
            "OpenRouter returned an empty response."
        )

    return str(
        content
    ).strip()


# ============================================================
# CLEAN JSON
# ============================================================

def clean_json(text):

    if not text:

        raise ValueError(
            "AI returned an empty response."
        )

    text = text.strip()

    # Remove markdown code fences

    if text.startswith(
        "```json"
    ):

        text = text[7:].strip()

    elif text.startswith(
        "```"
    ):

        text = text[3:].strip()

    if text.endswith(
        "```"
    ):

        text = text[:-3].strip()

    # Find JSON object

    start = text.find(
        "{"
    )

    end = text.rfind(
        "}"
    )

    if (
        start != -1
        and end != -1
        and end > start
    ):

        text = text[
            start:end + 1
        ]

    try:

        return json.loads(
            text
        )

    except json.JSONDecodeError as error:

        raise ValueError(
            "AI returned invalid JSON.\n"
            f"Error: {error}\n"
            f"Response:\n{text}"
        )


# ============================================================
# EXTRACT LAND DATA
# ============================================================

def extract_land_data_from_text(
    document_text
):

    prompt = f"""
Analyze the following agricultural land document.

Extract ONLY information that is explicitly present
in the document.

Return ONLY a valid JSON object.

Do not use Markdown.

Use exactly these fields:

{{
    "survey_number": "",
    "village": "",
    "taluk": "",
    "district": "",
    "state": "",
    "area_acres": null,
    "owner": "",
    "mutation_status": "",
    "document_type": ""
}}

IMPORTANT:

- Do not guess.
- Do not invent missing information.
- If a value is missing, use an empty string.
- If area is missing, use null.
- area_acres must be a number when clearly available.
- Convert units to acres only when the conversion is
  completely unambiguous.
- Preserve the owner name exactly as written.
- Preserve the survey number exactly as written.

DOCUMENT:

{document_text[:30000]}
"""

    response = call_openrouter(

        prompt,

        max_tokens=1000,

        temperature=0
    )

    return clean_json(
        response
    )


# ============================================================
# GENERATE LAND EXPLANATION
# ============================================================

def generate_land_explanation(
    extracted,
    reference,
    verification
):

    prompt = f"""
Analyze this BhoomiMitra land verification result.

DOCUMENT-EXTRACTED INFORMATION:

{json.dumps(
    extracted,
    indent=2,
    ensure_ascii=False
)}

REFERENCE INFORMATION:

{json.dumps(
    reference,
    indent=2,
    ensure_ascii=False
)}

DETERMINISTIC VERIFICATION RESULT:

{json.dumps(
    verification,
    indent=2,
    ensure_ascii=False
)}

Return ONLY a valid JSON object.

Do not use Markdown.

Use exactly this structure:

{{
    "summary": "",
    "why_score": "",
    "risks": [],
    "buyer_actions": [],
    "seller_actions": [],
    "disclaimer": ""
}}

IMPORTANT:

- Explain the score using ONLY the supplied verification result.
- Do not change the score.
- Do not invent additional risks.
- Clearly mention important mismatches.
- If document and reference record disagree,
  explain exactly what differs.
- Never claim legal ownership is certified.
- Never claim government approval unless explicitly supplied.
- This is decision-support, not legal title certification.
"""

    response = call_openrouter(

        prompt,

        max_tokens=1500,

        temperature=0.1
    )

    return clean_json(
        response
    )


# ============================================================
# BUYER AI
# ============================================================

def ask_bhoomimitra(
    question,
    property_data
):

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

IMPORTANT RULES:

- Use only the supplied property information.
- Do not invent government information.
- Do not invent missing property information.
- Do not certify ownership.
- Do not provide definitive legal advice.
- If information is insufficient, clearly say so.
- Recommend appropriate human, legal, or government
  verification when necessary.
- Keep the answer understandable to a normal buyer.
"""

    return call_openrouter(

        prompt,

        max_tokens=700,

        temperature=0.2
    )


# ============================================================
# CONNECTION TEST
# ============================================================

def test_openrouter_connection():

    response = call_openrouter(

        """
Respond with exactly:

BhoomiMitra AI OpenRouter connection is working.
""",

        max_tokens=50,

        temperature=0
    )

    return response