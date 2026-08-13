import re

from presidio_analyzer import (
    AnalyzerEngine,
    PatternRecognizer,
    Pattern
)

from presidio_analyzer.nlp_engine import NlpEngineProvider


# =========================================================
# MICROSOFT PRESIDIO SETUP
# =========================================================

configuration = {
    "nlp_engine_name": "spacy",
    "models": [
        {
            "lang_code": "en",
            "model_name": "en_core_web_lg"
        }
    ]
}

provider = NlpEngineProvider(
    nlp_configuration=configuration
)

nlp_engine = provider.create_engine()

analyzer = AnalyzerEngine(
    nlp_engine=nlp_engine,
    supported_languages=["en"]
)


# =========================================================
# EMAIL
# =========================================================

EMAIL_PATTERN = r"[\w.-]+@[\w.-]+\.\w+"


def detect_emails(text: str) -> list:

    results = []

    for match in re.finditer(EMAIL_PATTERN, text):

        results.append({
            "text": match.group(),
            "type": "EMAIL",
            "start": match.start(),
            "end": match.end()
        })

    return results


# =========================================================
# PHONE
# =========================================================

PHONE_PATTERN = (
    r"(?<!\d)"
    r"(?:"
        r"[6-9]\d{9}"
        r"|"
        r"\+\s*91(?:[-\s]+)"
        r"(?:"
            r"[6-9]\d{9}"
            r"|"
            r"\d{2}\s*\d{8}"
            r"|"
            r"\d{2}\s*\d{4}\s*\d{4}"
        ")"
    ")"
    r"(?!\d)"
)


def detect_phones(text: str) -> list:

    results = []

    for match in re.finditer(PHONE_PATTERN, text):

        results.append({
            "text": match.group(),
            "type": "PHONE",
            "start": match.start(),
            "end": match.end()
        })

    return results


def normalize_phone(phone: str) -> str:
    return re.sub(r"\D", "", phone)


# =========================================================
# IP ADDRESS
# =========================================================

IP_PATTERN = (
    r"(?<![\d.])"
    r"(?:\d{1,3}\.){3}"
    r"\d{1,3}"
    r"(?![\d.])"
)


def detect_ips(text: str) -> list:

    results = []

    for match in re.finditer(IP_PATTERN, text):

        ip = match.group()
        octets = ip.split(".")

        if all(0 <= int(x) <= 255 for x in octets):

            results.append({
                "text": ip,
                "type": "IP_ADDRESS",
                "start": match.start(),
                "end": match.end()
            })

    return results


# =========================================================
# CREDIT CARD
# =========================================================

CREDIT_CARD_PATTERN = (
    r"(?<!\d)"
    r"(?:\d[ -]?){13,19}"
    r"(?!\d)"
)


def is_valid_credit_card(number: str) -> bool:

    digits = re.sub(r"\D", "", number)

    if not 13 <= len(digits) <= 19:
        return False

    total = 0

    for i, digit in enumerate(digits[::-1]):

        value = int(digit)

        if i % 2 == 1:
            value *= 2

            if value > 9:
                value -= 9

        total += value

    return total % 10 == 0


def detect_credit_cards(text: str) -> list:

    results = []

    for match in re.finditer(
        CREDIT_CARD_PATTERN,
        text
    ):

        candidate = match.group()

        if is_valid_credit_card(candidate):

            results.append({
                "text": candidate,
                "type": "CREDIT_CARD",
                "start": match.start(),
                "end": match.end()
            })

    return results


# =========================================================
# SSN
# =========================================================

SSN_PATTERN = (
    r"(?<![\d-])"
    r"\d{3}-\d{2}-\d{4}"
    r"(?![\d-])"
)


def detect_ssns(text: str) -> list:

    results = []

    for match in re.finditer(
        SSN_PATTERN,
        text
    ):

        ssn = match.group()

        area, group, serial = map(
            int,
            ssn.split("-")
        )

        if area == 0:
            continue

        if area == 666:
            continue

        if area >= 900:
            continue

        if group == 0:
            continue

        if serial == 0:
            continue

        results.append({
            "text": ssn,
            "type": "SSN",
            "start": match.start(),
            "end": match.end()
        })

    return results


# =========================================================
# DATE OF BIRTH
# =========================================================

MONTHS = (
    r"January|February|March|April|May|June|July|August|"
    r"September|October|November|December"
)


DOB_CONTEXT_PATTERN = re.compile(
    r"(?i)"
    r"\b(?:"
        r"date\s+of\s+birth"
        r"|date\s+birth"
        r"|dob"
        r"|birth\s+date"
        r"|born"
    r")"
    r"\s*(?:is|:|-)?\s*"
    r"("
        # DD/MM/YYYY
        r"\d{1,2}[/-]\d{1,2}[/-]\d{4}"

        r"|"

        # DD/MM/YY
        r"\d{1,2}[/-]\d{1,2}[/-]\d{2}"

        r"|"

        # DD Month YYYY
        r"\d{1,2}\s+(?:"
            + MONTHS +
        r")\s+\d{4}"

        r"|"

        # Month DD YYYY
        r"(?:"
            + MONTHS +
        r")\s+\d{1,2},?\s+\d{4}"
    r")"
)


def detect_dobs(text: str) -> list:

    results = []

    for match in DOB_CONTEXT_PATTERN.finditer(text):

        dob = match.group(1)

        results.append({
            "text": dob,
            "type": "DATE_OF_BIRTH",
            "start": match.start(1),
            "end": match.end(1)
        })

    return results


# =========================================================
# NAME DETECTION
# =========================================================

def detect_names(text: str) -> list:
    """
    Detect person names using Microsoft Presidio in chunks.

    Processing the full 445k-character document at once can
    consume too much RAM with en_core_web_lg.
    """

    CHUNK_SIZE = 20000

    output = []

    for chunk_start in range(
        0,
        len(text),
        CHUNK_SIZE
    ):

        chunk_end = min(
            chunk_start + CHUNK_SIZE,
            len(text)
        )

        chunk = text[chunk_start:chunk_end]

        try:

            results = analyzer.analyze(
                text=chunk,
                entities=["PERSON"],
                language="en"
            )

        except Exception as e:

            print(
                f"Name detection failed for chunk "
                f"{chunk_start}-{chunk_end}: {e}"
            )

            continue

        for result in results:

            name = chunk[
                result.start:result.end
            ]

            if not is_valid_person_name(name):
                continue

            normalized_name = normalize_name(name)

            output.append({
                "text": normalized_name,
                "type": "NAME",
                "start": chunk_start + result.start,
                "end": chunk_start + result.end
            })

        print(
            f"Name detection progress: "
            f"{chunk_end}/{len(text)}"
        )

    # -----------------------------------------------------
    # Remove duplicates
    # -----------------------------------------------------

    unique = {}

    for item in output:

        key = (
            item["text"].lower(),
            item["start"],
            item["end"]
        )

        if key not in unique:
            unique[key] = item

    output = list(unique.values())

    output.sort(
        key=lambda x: x["start"]
    )

    return output


# =========================================================
# COMPANY DETECTION
# =========================================================

COMPANY_PATTERN = Pattern(
    name="company_name_pattern",

    regex=(
        r"\b"
        r"[A-Z][A-Za-z0-9&.-]*"
        r"(?:"
            r"[ \t]+"
            r"[A-Z][A-Za-z0-9&.-]*"
        "){0,6}"
        r"[ \t]+"
        r"(?:"
            r"Inc\.?"
            r"|Ltd\.?"
            r"|Limited"
            r"|Corporation"
            r"|Corp\.?"
            r"|Company"
            r"|Co\.?"
            r"|LLC"
            r"|LLP"
            r"|PLC"
            r"|Technologies"
            r"|Technology"
            r"|Solutions"
            r"|Systems"
            r"|Industries"
            r"|Enterprises"
            r"|Holdings"
            r"|Group"
            r"|Bank"
            r"|Trust"
            r"|Finance"
            r"|Capital"
            r"|Investments"
            r"|Securities"
        ")"
        r"\b"
    ),

    score=0.85
)


company_recognizer = PatternRecognizer(
    supported_entity="COMPANY",
    patterns=[
        COMPANY_PATTERN
    ]
)

analyzer.registry.add_recognizer(
    company_recognizer
)


def detect_companies(text: str) -> list:

    results = analyzer.analyze(
        text=text,
        entities=["COMPANY"],
        language="en"
    )

    output = []

    for result in results:

        company = text[result.start:result.end].strip()

        if not company:
            continue

        output.append({
            "text": company,
            "type": "COMPANY",
            "start": result.start,
            "end": result.end
        })

    # Deduplicate exact spans
    unique = {}

    for item in output:

        key = (
            item["start"],
            item["end"]
        )

        unique[key] = item

    output = list(unique.values())

    output.sort(
        key=lambda x: x["start"]
    )

    return output


# =========================================================
# NAME FALSE POSITIVES
# =========================================================

NAME_FALSE_POSITIVES = {

    "ahilyanagar",
    "ahmednagar",
    "vikhroli",
    "kanjurmarg",
    "lower parel",
    "shivaji nagar",
    "erandawane",
    "chakan",
    "supa",

    "fiscals",
    "email",
    "cap price",
    "circular",
    "challan",
    "slip",
    "scrr",
    "listing sebi bhavan",
    "schedule xiii",
    "the lok sabha",

    "supa facility",
    "supa parner industrial park",
    "mauje palve khurd",
    "taluka parner",
    "taluka khed",
    "taluka-khed",
    "chakan taluka - khed",
    "chakan taluka-khed",
    "birdewadi chakan",

    "gopal house",
    "gopal bo",
    "tanishq showroom",
    "chitra raste",
    "appasaheb marathe marg",
    "gopalkrupa apartment",
    "unpai",
    "raj esh branch",
    "rajesh branch",
    "dear",
    "bill",
    "bill bill",
    "grill pat",
    "pat cagr",
    "urja suraksha",
    "utthaan mahabhiyan",
}


def normalize_name(name: str) -> str:

    name = name.replace("\n", " ")
    name = re.sub(r"\s+", " ", name)

    return name.strip()


def is_valid_person_name(name: str) -> bool:

    normalized = normalize_name(name)
    lower_name = normalized.lower()

    if not normalized:
        return False

    if len(normalized) < 3:
        return False

    if lower_name in NAME_FALSE_POSITIVES:
        return False

    if "@" in normalized:
        return False

    if "http://" in lower_name:
        return False

    if "https://" in lower_name:
        return False

    if "/" in normalized:
        return False

    if "\n" in name:
        return False

    if not re.fullmatch(
        r"[A-Za-z]+(?:[ .'-][A-Za-z]+)*",
        normalized
    ):
        return False

    document_words = {
        "email",
        "sebi",
        "registration",
        "number",
        "price",
        "schedule",
        "circular",
        "facility",
        "industrial",
        "park",
        "taluka",
        "house",
        "showroom",
        "branch",
        "fiscals",
        "fiscal",
        "listing",
        "challan",
        "slip",
        "cagr",
        "lok",
        "sabha",
    }

    words = lower_name.split()

    if any(
        word in document_words
        for word in words
    ):
        return False

    if len(words) < 2:
        return False

    if len(words) > 5:
        return False

    if normalized.isupper() and len(words) == 1:
        return False

    return True


# =========================================================
# PHYSICAL / MAILING ADDRESS
# =========================================================

ADDRESS_PATTERNS = [

    # Indian PIN code with surrounding address
    re.compile(
        r"\b"
        r"(?=[^.\n]{5,200}\b\d{6}\b)"
        r"[^.\n]{5,200}"
        r"\b\d{6}\b",
        re.IGNORECASE
    ),

    # Flat / House / Plot / Office / Unit addresses
    re.compile(
        r"\b(?:Flat|House|Plot|Shop|Office|Unit|Building|"
        r"Bldg|Floor|Apartment|Apt)\s*"
        r"(?:No\.?|Number)?\s*"
        r"[\w/-]+"
        r"(?:[,\s]+[^.\n]{3,150})?"
        r"(?:[-,\s]+\d{6})?\b",
        re.IGNORECASE
    ),

    # Road / Street / Marg / Nagar etc. with locality
    re.compile(
        r"\b[^.\n]{5,150}"
        r"(?:Road|Rd\.|Street|St\.|Marg|Nagar|"
        r"Colony|Layout|Park|Society|Complex)"
        r"[^.\n]{0,100}"
        r"(?:\b\d{6}\b)?",
        re.IGNORECASE
    ),
]


def detect_addresses(text: str) -> list:

    detections = []

    for pattern in ADDRESS_PATTERNS:

        for match in pattern.finditer(text):

            value = match.group().strip()

            if len(value) < 10:
                continue

            # Avoid enormous accidental matches
            if len(value) > 220:
                continue

            detections.append({
                "text": value,
                "type": "ADDRESS",
                "start": match.start(),
                "end": match.end()
            })

    # -----------------------------------------------------
    # Deduplicate
    # -----------------------------------------------------

    unique = {}

    for item in detections:

        key = (
            item["start"],
            item["end"]
        )

        unique[key] = item

    results = list(unique.values())

    results.sort(
        key=lambda x: x["start"]
    )

    return results