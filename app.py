import os
import uuid

import fitz

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for
)

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


load_dotenv()


app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "development-secret"
)


UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# -------------------------------------------------------
# DEMO STORAGE
# -------------------------------------------------------

PROPERTIES = []


# -------------------------------------------------------
# HOME
# -------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# -------------------------------------------------------
# SELLER
# -------------------------------------------------------

@app.route("/seller")
def seller():
    return render_template("seller.html")


# -------------------------------------------------------
# BUYER
# -------------------------------------------------------

@app.route("/buyer")
def buyer():
    return render_template(
        "buyer.html",
        properties=PROPERTIES
    )


# -------------------------------------------------------
# VERIFY PAGE
# -------------------------------------------------------

@app.route("/verify")
def verify():
    return render_template("verify.html")


# -------------------------------------------------------
# EXTRACT PDF TEXT
# -------------------------------------------------------

def extract_pdf_text(file_path):

    document = fitz.open(file_path)

    pages = []

    for page in document:
        pages.append(page.get_text())

    document.close()

    return "\n".join(pages)


# -------------------------------------------------------
# VERIFY LAND
# -------------------------------------------------------

@app.route("/verify-land", methods=["POST"])
def verify_land():

    try:

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

        # ------------------------------------------------
        # SAVE DOCUMENT
        # ------------------------------------------------

        extension = os.path.splitext(
            uploaded_file.filename
        )[1].lower()

        file_id = str(uuid.uuid4())

        filename = file_id + extension

        file_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        uploaded_file.save(file_path)

        # ------------------------------------------------
        # READ DOCUMENT
        # ------------------------------------------------

        if extension == ".pdf":

            document_text = extract_pdf_text(
                file_path
            )

        elif extension in [".txt", ".text"]:

            with open(
                file_path,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as file:

                document_text = file.read()

        else:

            return jsonify({
                "success": False,
                "error": (
                    "For this demo, please upload "
                    "a PDF or TXT document."
                )
            }), 400

        if not document_text.strip():

            return jsonify({
                "success": False,
                "error": (
                    "No readable text was found. "
                    "Please upload a text-based PDF."
                )
            }), 400

        # ------------------------------------------------
        # GEMINI DOCUMENT EXTRACTION
        # ------------------------------------------------

        extracted = extract_land_data_from_text(
            document_text
        )

        # User-entered values can supplement
        # missing document values.

        if survey_number and not extracted.get(
            "survey_number"
        ):
            extracted["survey_number"] = survey_number

        if village and not extracted.get(
            "village"
        ):
            extracted["village"] = village

        if area and not extracted.get(
            "area_acres"
        ):
            try:
                extracted["area_acres"] = float(area)
            except ValueError:
                pass

        # ------------------------------------------------
        # FIND REFERENCE RECORD
        # ------------------------------------------------

        reference = find_reference_record(
            extracted.get("survey_number"),
            extracted.get("village")
        )

        if not reference:

            return jsonify({
                "success": False,
                "error": (
                    "No matching reference record "
                    "was found for this demo. "
                    "Try Survey No. 123/4 or 456/2."
                )
            }), 404

        # ------------------------------------------------
        # DETERMINISTIC VERIFICATION
        # ------------------------------------------------

        verification = calculate_verification(
            extracted,
            reference
        )

        # ------------------------------------------------
        # GEMINI EXPLANATION
        # ------------------------------------------------

        explanation = generate_land_explanation(
            extracted,
            reference,
            verification
        )

        # ------------------------------------------------
        # PROPERTY
        # ------------------------------------------------

        property_id = str(uuid.uuid4())[:8]

        property_data = {
            "id": property_id,
            "seller_name": seller_name,
            "price": price,
            "survey_number": extracted.get(
                "survey_number",
                ""
            ),
            "village": extracted.get(
                "village",
                ""
            ),
            "taluk": extracted.get(
                "taluk",
                ""
            ),
            "district": extracted.get(
                "district",
                ""
            ),
            "state": extracted.get(
                "state",
                ""
            ),
            "area_acres": extracted.get(
                "area_acres"
            ),
            "owner": extracted.get(
                "owner",
                ""
            ),
            "mutation_status": extracted.get(
                "mutation_status",
                ""
            ),
            "document_type": extracted.get(
                "document_type",
                ""
            ),
            "extracted": extracted,
            "reference": reference,
            "verification": verification,
            "explanation": explanation
        }

        PROPERTIES.append(property_data)

        return jsonify({
            "success": True,
            "property_id": property_id
        })

    except Exception as error:

        print("ERROR:", error)

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500


# -------------------------------------------------------
# PROPERTY
# -------------------------------------------------------

@app.route("/property/<property_id>")
def property_page(property_id):

    property_data = next(
        (
            item for item in PROPERTIES
            if item["id"] == property_id
        ),
        None
    )

    if not property_data:
        return "Property not found", 404

    return render_template(
        "property.html",
        property=property_data
    )


# -------------------------------------------------------
# ASK AI
# -------------------------------------------------------

@app.route("/ask-ai", methods=["POST"])
def ask_ai():

    data = request.get_json()

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
            "error": "Please enter a question."
        }), 400

    property_data = next(
        (
            item for item in PROPERTIES
            if item["id"] == property_id
        ),
        None
    )

    if not property_data:

        return jsonify({
            "success": False,
            "error": "Property not found."
        }), 404

    answer = ask_bhoomimitra(
        question,
        property_data
    )

    return jsonify({
        "success": True,
        "answer": answer
    })


# -------------------------------------------------------
# API
# -------------------------------------------------------

@app.route("/api/properties")
def api_properties():

    return jsonify(PROPERTIES)


# -------------------------------------------------------
# HEALTH CHECK
# -------------------------------------------------------

@app.route("/health")
def health():

    return jsonify({
        "status": "ok",
        "service": "BhoomiMitra AI"
    })


# -------------------------------------------------------
# RUN
# -------------------------------------------------------

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