import json
import os


# ============================================================
# REFERENCE DATA LOCATION
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATA_FILE = os.path.join(
    BASE_DIR,
    "data",
    "demo_land_records.json"
)


# ============================================================
# LOAD REFERENCE RECORDS
# ============================================================

def load_reference_records():

    with open(
        DATA_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# FIND REFERENCE RECORD
# ============================================================

def find_reference_record(
    survey_number,
    village=None
):

    records = load_reference_records()

    survey_number = str(
        survey_number or ""
    ).strip().lower()

    for record in records:

        record_survey = str(
            record["survey_number"]
        ).strip().lower()

        if record_survey != survey_number:
            continue

        if village:

            if (
                record["village"]
                .strip()
                .lower()
                !=
                village.strip().lower()
            ):

                continue

        return record

    return None


# ============================================================
# VERIFICATION ENGINE
# ============================================================

def calculate_verification(
    extracted,
    reference
):

    score = 100

    checks = []

    # --------------------------------------------------------
    # SURVEY NUMBER
    # --------------------------------------------------------

    extracted_survey = str(
        extracted.get(
            "survey_number",
            ""
        )
    ).strip().lower()

    reference_survey = str(
        reference.get(
            "survey_number",
            ""
        )
    ).strip().lower()

    if extracted_survey == reference_survey:

        checks.append({

            "name":
                "Survey Number",

            "status":
                "MATCH",

            "message":
                "Survey number matches reference record."

        })

    else:

        score -= 25

        checks.append({

            "name":
                "Survey Number",

            "status":
                "MISMATCH",

            "message":
                "Survey number does not match reference record."

        })

    # --------------------------------------------------------
    # VILLAGE
    # --------------------------------------------------------

    extracted_village = str(
        extracted.get(
            "village",
            ""
        )
    ).strip().lower()

    reference_village = str(
        reference.get(
            "village",
            ""
        )
    ).strip().lower()

    if extracted_village == reference_village:

        checks.append({

            "name":
                "Village",

            "status":
                "MATCH",

            "message":
                "Village matches reference record."

        })

    else:

        score -= 10

        checks.append({

            "name":
                "Village",

            "status":
                "MISMATCH",

            "message":
                "Village differs from reference record."

        })

    # --------------------------------------------------------
    # LAND AREA
    # --------------------------------------------------------

    try:

        extracted_area = float(
            extracted.get(
                "area_acres"
            )
        )

        reference_area = float(
            reference.get(
                "area_acres"
            )
        )

        difference = abs(
            extracted_area -
            reference_area
        )

        if difference <= 0.05:

            checks.append({

                "name":
                    "Land Area",

                "status":
                    "MATCH",

                "message":
                    f"Area difference is only "
                    f"{difference:.2f} acres."

            })

        else:

            score -= 20

            checks.append({

                "name":
                    "Land Area",

                "status":
                    "MISMATCH",

                "message":
                    f"Document: "
                    f"{extracted_area} acres | "
                    f"Reference: "
                    f"{reference_area} acres | "
                    f"Difference: "
                    f"{difference:.2f} acres"

            })

    except (
        TypeError,
        ValueError
    ):

        score -= 20

        checks.append({

            "name":
                "Land Area",

            "status":
                "UNAVAILABLE",

            "message":
                "Area could not be reliably verified."

        })

    # --------------------------------------------------------
    # MUTATION
    # --------------------------------------------------------

    mutation = str(
        reference.get(
            "mutation_status",
            ""
        )
    ).strip().lower()

    if mutation == "available":

        checks.append({

            "name":
                "Mutation",

            "status":
                "MATCH",

            "message":
                "Mutation information is available."

        })

    else:

        score -= 10

        checks.append({

            "name":
                "Mutation",

            "status":
                "REVIEW",

            "message":
                "Mutation information requires review."

        })

    # --------------------------------------------------------
    # BOUNDARY
    # --------------------------------------------------------

    boundary = str(
        reference.get(
            "boundary_status",
            ""
        )
    ).strip().lower()

    if boundary == "consistent":

        checks.append({

            "name":
                "Boundary",

            "status":
                "MATCH",

            "message":
                "Boundary information is marked consistent."

        })

    else:

        score -= 15

        checks.append({

            "name":
                "Boundary",

            "status":
                "REVIEW",

            "message":
                "Boundary information requires further review."

        })

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    score = max(
        0,
        min(
            100,
            score
        )
    )

    if score >= 80:

        risk_level = "LOW"

    elif score >= 60:

        risk_level = "MEDIUM"

    else:

        risk_level = "HIGH"

    return {

        "score":
            score,

        "risk_level":
            risk_level,

        "checks":
            checks,

        "reference_source":
            reference.get(
                "source",
                "Reference Dataset"
            )
    }