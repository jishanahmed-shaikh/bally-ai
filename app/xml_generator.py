"""
Tally XML generator.

Builds ENVELOPE > HEADER > BODY > IMPORTDATA > REQUESTDATA > TALLYMESSAGE > VOUCHER
per the Tally TDL import format.
"""
import xml.etree.ElementTree as ET
import xml.dom.minidom
from decimal import Decimal
from app.models import Transaction, TallyVoucher, VoucherType


def _determine_voucher_type(t: Transaction) -> VoucherType:
    if t.withdrawal > 0 and t.deposit == 0:
        return VoucherType.Payment
    elif t.deposit > 0 and t.withdrawal == 0:
        return VoucherType.Receipt
    else:
        return VoucherType.Contra


def _transaction_to_voucher(t: Transaction, bank_ledger_name: str) -> TallyVoucher:
    vtype = _determine_voucher_type(t)
    amount = t.withdrawal if t.withdrawal > 0 else t.deposit
    assigned = t.assigned_ledger or "Miscellaneous"

    if vtype == VoucherType.Receipt:
        debit = bank_ledger_name
        credit = assigned
    else:
        # Payment and Contra
        debit = assigned
        credit = bank_ledger_name

    return TallyVoucher(
        voucher_type=vtype,
        date=t.date,
        narration=t.narration,
        debit_ledger=debit,
        credit_ledger=credit,
        amount=amount,
    )


def _build_ledger_entry(parent: ET.Element, ledger_name: str, is_deemed_positive: str, amount: Decimal) -> None:
    entry = ET.SubElement(parent, "LEDGERENTRIES.LIST")
    ET.SubElement(entry, "LEDGERNAME").text = ledger_name
    ET.SubElement(entry, "ISDEEMEDPOSITIVE").text = is_deemed_positive
    ET.SubElement(entry, "AMOUNT").text = f"{amount:.2f}"


def _build_voucher_element(parent: ET.Element, voucher: TallyVoucher) -> None:
    v = ET.SubElement(parent, "VOUCHER")
    v.set("VCHTYPE", voucher.voucher_type.value)
    v.set("ACTION", "Create")

    ET.SubElement(v, "DATE").text = voucher.date
    ET.SubElement(v, "NARRATION").text = voucher.narration
    ET.SubElement(v, "VOUCHERTYPENAME").text = voucher.voucher_type.value

    # Debit entry: ISDEEMEDPOSITIVE=Yes, amount negative
    _build_ledger_entry(v, voucher.debit_ledger, "Yes", -voucher.amount)
    # Credit entry: ISDEEMEDPOSITIVE=No, amount positive
    _build_ledger_entry(v, voucher.credit_ledger, "No", voucher.amount)


def generate_tally_xml(transactions: list[Transaction], bank_ledger_name: str) -> str:
    """Generate Tally-compatible XML from a list of Transaction objects."""
    envelope = ET.Element("ENVELOPE")

    header = ET.SubElement(envelope, "HEADER")
    ET.SubElement(header, "TALLYREQUEST").text = "Import Data"

    body = ET.SubElement(envelope, "BODY")
    importdata = ET.SubElement(body, "IMPORTDATA")

    requestdesc = ET.SubElement(importdata, "REQUESTDESC")
    ET.SubElement(requestdesc, "REPORTNAME").text = "Vouchers"

    requestdata = ET.SubElement(importdata, "REQUESTDATA")

    for t in transactions:
        voucher = _transaction_to_voucher(t, bank_ledger_name)
        tallymessage = ET.SubElement(requestdata, "TALLYMESSAGE")
        tallymessage.set("xmlns:UDF", "TallyUDF")
        _build_voucher_element(tallymessage, voucher)

    raw = ET.tostring(envelope, encoding="unicode")
    pretty = xml.dom.minidom.parseString(raw).toprettyxml(indent="  ")
    # Remove the XML declaration line added by toprettyxml
    lines = pretty.split("\n")
    if lines[0].startswith("<?xml"):
        lines = lines[1:]
    return "\n".join(lines)


def generate_tally_xml_from_vouchers(vouchers: list[TallyVoucher], bank_ledger_name: str) -> str:
    """Generate Tally XML from pre-built TallyVoucher objects (used for round-trip testing)."""
    envelope = ET.Element("ENVELOPE")

    header = ET.SubElement(envelope, "HEADER")
    ET.SubElement(header, "TALLYREQUEST").text = "Import Data"

    body = ET.SubElement(envelope, "BODY")
    importdata = ET.SubElement(body, "IMPORTDATA")

    requestdesc = ET.SubElement(importdata, "REQUESTDESC")
    ET.SubElement(requestdesc, "REPORTNAME").text = "Vouchers"

    requestdata = ET.SubElement(importdata, "REQUESTDATA")

    for voucher in vouchers:
        tallymessage = ET.SubElement(requestdata, "TALLYMESSAGE")
        tallymessage.set("xmlns:UDF", "TallyUDF")
        _build_voucher_element(tallymessage, voucher)

    raw = ET.tostring(envelope, encoding="unicode")
    pretty = xml.dom.minidom.parseString(raw).toprettyxml(indent="  ")
    lines = pretty.split("\n")
    if lines[0].startswith("<?xml"):
        lines = lines[1:]
    return "\n".join(lines)


def parse_tally_xml(xml_str: str) -> list[TallyVoucher]:
    """Parse a Tally XML string back into TallyVoucher objects (for round-trip testing)."""
    root = ET.fromstring(xml_str)
    vouchers = []

    for tallymessage in root.findall(".//TALLYMESSAGE"):
        voucher_el = tallymessage.find("VOUCHER")
        if voucher_el is None:
            continue

        vchtype = voucher_el.get("VCHTYPE", "")
        date = voucher_el.findtext("DATE", "")
        narration = voucher_el.findtext("NARRATION", "")

        entries = voucher_el.findall("LEDGERENTRIES.LIST")
        debit_ledger = ""
        credit_ledger = ""
        amount = Decimal("0.00")

        for entry in entries:
            ledger_name = entry.findtext("LEDGERNAME", "")
            is_deemed = entry.findtext("ISDEEMEDPOSITIVE", "No")
            amt_text = entry.findtext("AMOUNT", "0")
            amt = Decimal(amt_text)

            if is_deemed == "Yes":
                debit_ledger = ledger_name
                amount = abs(amt)
            else:
                credit_ledger = ledger_name

        vouchers.append(TallyVoucher(
            voucher_type=VoucherType(vchtype),
            date=date,
            narration=narration,
            debit_ledger=debit_ledger,
            credit_ledger=credit_ledger,
            amount=amount,
        ))

    return vouchers
