"""
Tally XML validator.

Validates that a generated XML string conforms to the expected
Tally TDL import structure before returning it to the user.
"""
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.valid


REQUIRED_PATH = [
    "ENVELOPE",
    "BODY",
    "IMPORTDATA",
    "REQUESTDATA",
]

REQUIRED_VOUCHER_FIELDS = ["DATE", "NARRATION", "VOUCHERTYPENAME"]
VALID_VOUCHER_TYPES = {"Payment", "Receipt", "Contra"}


def validate_tally_xml(xml_str: str) -> ValidationResult:
    """
    Validate a Tally XML string for structural correctness.

    Checks:
    - Parseable XML
    - Required element hierarchy exists
    - At least one TALLYMESSAGE with a VOUCHER
    - Each VOUCHER has DATE, NARRATION, VOUCHERTYPENAME
    - Each VOUCHER has exactly 2 LEDGERENTRIES.LIST elements
    - ISDEEMEDPOSITIVE values are "Yes" or "No"
    """
    errors: list[str] = []

    # 1. Parse XML
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError as e:
        return ValidationResult(valid=False, errors=[f"XML parse error: {e}"])

    # 2. Check root tag
    if root.tag != "ENVELOPE":
        errors.append(f"Root element must be ENVELOPE, got {root.tag!r}")

    # 3. Check required hierarchy
    body = root.find("BODY")
    if body is None:
        errors.append("Missing BODY element")
    else:
        importdata = body.find("IMPORTDATA")
        if importdata is None:
            errors.append("Missing BODY > IMPORTDATA element")
        else:
            requestdata = importdata.find("REQUESTDATA")
            if requestdata is None:
                errors.append("Missing BODY > IMPORTDATA > REQUESTDATA element")
            else:
                messages = requestdata.findall("TALLYMESSAGE")
                if not messages:
                    errors.append("No TALLYMESSAGE elements found in REQUESTDATA")

                for i, msg in enumerate(messages):
                    voucher = msg.find("VOUCHER")
                    if voucher is None:
                        errors.append(f"TALLYMESSAGE[{i}] has no VOUCHER element")
                        continue

                    # Check voucher type
                    vchtype = voucher.get("VCHTYPE", "")
                    if vchtype not in VALID_VOUCHER_TYPES:
                        errors.append(f"VOUCHER[{i}] has invalid VCHTYPE={vchtype!r}")

                    # Check required fields
                    for field_name in REQUIRED_VOUCHER_FIELDS:
                        if voucher.find(field_name) is None:
                            errors.append(f"VOUCHER[{i}] missing {field_name}")

                    # Check ledger entries
                    entries = voucher.findall("LEDGERENTRIES.LIST")
                    if len(entries) != 2:
                        errors.append(
                            f"VOUCHER[{i}] must have exactly 2 LEDGERENTRIES.LIST, got {len(entries)}"
                        )
                    for j, entry in enumerate(entries):
                        is_deemed = entry.findtext("ISDEEMEDPOSITIVE", "")
                        if is_deemed not in ("Yes", "No"):
                            errors.append(
                                f"VOUCHER[{i}] LEDGERENTRIES.LIST[{j}] has invalid "
                                f"ISDEEMEDPOSITIVE={is_deemed!r}"
                            )

    return ValidationResult(valid=len(errors) == 0, errors=errors)
