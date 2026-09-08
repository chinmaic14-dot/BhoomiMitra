import os
import uuid
import traceback

import fitz
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

from services.ai_service import (
    extract_land_data_from_text,
    generate_land_explanation,
    ask_bhoomimitra
)

from services.verification_engine import (
    find_reference_record,
    calculate_verification
)


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

print("\n========== BHOOMIMITRA CONFIG ==========")
print(
    "OPENROUTER_API_KEY configured:",
    bool(os.getenv("OPENROUTER_API_KEY"))
)
print(
    "OPENROUTER_MODEL:",
    os.getenv("OPENROUTER_MODEL", "NOT SET")
)
print("========================================\n")


# ============================================================
# FLASK APP
# ============================================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "development-secret"
)


# ============================================================
# UPLOAD CONFIGURATION
# ============================================================

UPLOAD_FOLDER = "uploads"

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ============================================================
# TEMPORARY DEMO DATABASE
# ============================================================

PROPERTIES = []


# ============================================================
# BASIC PAGES
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/seller")
def seller():
    return render_template("seller.html")


@app.route("/buyer")
def buyer():
    return render_template(
        "buyer.html",
        properties=PROPERTIES
    )


@app.route("/verify")
def verify():
    return render_template("verify.html")


# ============================================================
# PDF TEXT EXTRACTION
# ============================================================

def extract_pdf_text(file_path):

    document = fitz.open(file_path)

    pages = []

    for page in document:
        pages.append(
            page.get_text()
        )

    document.close()

    return "\n".join(pages)


# ============================================================
# LAND VERIFICATION
# ============================================================

@app.route("/verify-land", methods=["POST"])
def verify_land():

    try:

        print("\n========== VERIFY LAND REQUEST ==========")

        # ----------------------------------------------------
        # FORM DATA
        # ----------------------------------------------------

        seller_name = request.form.get(
            "seller_name",
            ""
        ).strip()

        price = request.form.get(
            "price",
            ""
        ).strip()

        survey_number = request.form.get(
            "survey_number",
            ""
        ).strip()

        village = request.form.get(
            "village",
            ""
        ).strip()

        area = request.form.get(
            "area",
            ""
        ).strip()

        uploaded_file = request.files.get(
            "document"
        )

        print("Seller:", seller_name)
        print("Survey:", survey_number)
        print("Village:", village)
        print("Area:", area)

        # ----------------------------------------------------
        # FILE VALIDATION
        # ----------------------------------------------------

        if not uploaded_file:

            return jsonify({
                "success": False,
                "error": "Please upload a land document."
            }), 400

        if uploaded_file.filename == "":

            return jsonify({
                "success": False,
                "error": "Please select a document."
            }), 400

        # ----------------------------------------------------
        # SAVE FILE
        # ----------------------------------------------------

        extension = os.path.splitext(
            uploaded_file.filename
        )[1].lower()

        allowed_extensions = [
            ".pdf",
            ".txt",
            ".text"
        ]

        if extension not in allowed_extensions:

            return jsonify({
                "success": False,
                "error":
                    "For this demo, please upload "
                    "a PDF or TXT document."
            }), 400

        file_id = str(
            uuid.uuid4()
        )

        filename = (
            file_id +
            extension
        )

        file_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        uploaded_file.save(
            file_path
        )

        print("File saved:", file_path)

        # ----------------------------------------------------
        # READ DOCUMENT
        # ----------------------------------------------------

        if extension == ".pdf":

            document_text = extract_pdf_text(
                file_path
            )

        else:

            with open(
                file_path,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as file:

                document_text = file.read()

        print(
            "Document characters:",
            len(document_text)
        )

        if not document_text.strip():

            return jsonify({
                "success": False,
                "error":
                    "No readable text was found. "
                    "Please upload a text-based PDF."
            }), 400

        # ----------------------------------------------------
        # AI EXTRACTION
        # ----------------------------------------------------

        print("Starting AI extraction...")

        extracted = extract_land_data_from_text(
            document_text
        )

        print(
            "AI extraction completed:",
            extracted
        )

        # ----------------------------------------------------
        # FORM FALLBACKS
        # ----------------------------------------------------

        if (
            survey_number
            and not extracted.get("survey_number")
        ):

            extracted["survey_number"] = (
                survey_number
            )

        if (
            village
            and not extracted.get("village")
        ):

            extracted["village"] = village

        if (
            area
            and not extracted.get("area_acres")
        ):

            try:

                extracted["area_acres"] = float(
                    area
                )

            except ValueError:

                pass

        # ----------------------------------------------------
        # FIND REFERENCE RECORD
        # ----------------------------------------------------

        print(
            "Searching reference record..."
        )

        reference = find_reference_record(
            extracted.get("survey_number"),
            extracted.get("village")
        )

        if not reference:

            return jsonify({
                "success": False,
                "error":
                    "No matching reference record "
                    "was found for this demo. "
                    "Try Survey No. 123/4 or 456/2."
            }), 404

        print(
            "Reference found:",
            reference
        )

        # ----------------------------------------------------
        # DETERMINISTIC VERIFICATION
        # ----------------------------------------------------

        print(
            "Running verification engine..."
        )

        verification = calculate_verification(
            extracted,
            reference
        )

        print(
            "Verification:",
            verification
        )

        # ----------------------------------------------------
        # AI EXPLANATION
        # ----------------------------------------------------

        print(
            "Generating AI explanation..."
        )

        explanation = generate_land_explanation(
            extracted,
            reference,
            verification
        )

        print(
            "AI explanation completed."
        )

        # ----------------------------------------------------
        # PROPERTY ID
        # ----------------------------------------------------

        property_id = str(
            uuid.uuid4()
        )[:8]

        # ----------------------------------------------------
        # PROPERTY DATA
        # ----------------------------------------------------

        property_data = {

            "id": property_id,

            "seller_name":
                seller_name,

            "price":
                price,

            "survey_number":
                extracted.get(
                    "survey_number",
                    ""
                ),

            "village":
                extracted.get(
                    "village",
                    ""
                ),

            "taluk":
                extracted.get(
                    "taluk",
                    ""
                ),

            "district":
                extracted.get(
                    "district",
                    ""
                ),

            "state":
                extracted.get(
                    "state",
                    ""
                ),

            "area_acres":
                extracted.get(
                    "area_acres"
                ),

            "owner":
                extracted.get(
                    "owner",
                    ""
                ),

            "mutation_status":
                extracted.get(
                    "mutation_status",
                    ""
                ),

            "document_type":
                extracted.get(
                    "document_type",
                    ""
                ),

            "extracted":
                extracted,

            "reference":
                reference,

            "verification":
                verification,

            "explanation":
                explanation
        }

        # ----------------------------------------------------
        # STORE PROPERTY
        # ----------------------------------------------------

        PROPERTIES.append(
            property_data
        )

        print(
            "Property created:",
            property_id
        )

        print(
            "========== VERIFY LAND SUCCESS ==========\n"
        )

        # ----------------------------------------------------
        # SUCCESS RESPONSE
        # ----------------------------------------------------

        return jsonify({

            "success": True,

            "property_id":
                property_id

        })

    # ========================================================
    # GLOBAL ERROR HANDLING FOR THIS ROUTE
    # ========================================================

    except Exception as error:

        print(
            "\n========== BHOOMIMITRA ERROR =========="
        )

        print(
            "ERROR TYPE:",
            type(error).__name__
        )

        print(
            "ERROR:",
            str(error)
        )

        traceback.print_exc()

        print(
            "=======================================\n"
        )

        return jsonify({

            "success": False,

            "error":
                f"{type(error).__name__}: "
                f"{str(error)}"

        }), 500


# ============================================================
# PROPERTY PAGE
# ============================================================

@app.route("/property/<property_id>")
def property_page(property_id):

    property_data = next(
        (
            item
            for item in PROPERTIES
            if item["id"] == property_id
        ),
        None
    )

    if not property_data:

        return (
            "Property not found",
            404
        )

    return render_template(
        "property.html",
        property=property_data
    )


# ============================================================
# AI BUYER CHAT
# ============================================================

@app.route("/ask-ai", methods=["POST"])
def ask_ai():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        question = data.get(
            "question",
            ""
        ).strip()

        property_id = data.get(
            "property_id"
        )

        if not question:

            return jsonify({
                "success": False,
                "error":
                    "Please enter a question."
            }), 400

        property_data = next(
            (
                item
                for item in PROPERTIES
                if item["id"] == property_id
            ),
            None
        )

        if not property_data:

            return jsonify({
                "success": False,
                "error":
                    "Property not found."
            }), 404

        answer = ask_bhoomimitra(
            question,
            property_data
        )

        return jsonify({

            "success": True,

            "answer":
                answer

        })

    except Exception as error:

        print(
            "\n========== ASK AI ERROR =========="
        )

        traceback.print_exc()

        return jsonify({

            "success": False,

            "error":
                f"{type(error).__name__}: "
                f"{str(error)}"

        }), 500


# ============================================================
# PROPERTIES API
# ============================================================

@app.route("/api/properties")
def api_properties():

    return jsonify(
        PROPERTIES
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    return jsonify({

        "status":
            "ok",

        "service":
            "BhoomiMitra AI",

        "openrouter_configured":
            bool(
                os.getenv(
                    "OPENROUTER_API_KEY"
                )
            ),

        "model":
            os.getenv(
                "OPENROUTER_MODEL",
                "openrouter/free"
            )

    })


# ============================================================
# API 404 HANDLER
# ============================================================

@app.errorhandler(404)
def handle_404(error):

    if request.path.startswith("/api") or \
       request.path == "/verify-land" or \
       request.path == "/ask-ai":

        return jsonify({

            "success": False,

            "error":
                "API endpoint not found."

        }), 404

    return error


# ============================================================
# API 500 HANDLER
# ============================================================

@app.errorhandler(500)
def handle_500(error):

    traceback.print_exc()

    if request.path.startswith("/api") or \
       request.path == "/verify-land" or \
       request.path == "/ask-ai":

        return jsonify({

            "success": False,

            "error":
                "Internal server error. "
                "Check Render logs."

        }), 500

    return error


# ============================================================
# LOCAL DEVELOPMENT
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )