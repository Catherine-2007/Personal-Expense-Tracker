import datetime as dt
from app.services.receipt_parser import parse_receipt_text, parse_quick_text, _to_float

TODAY = dt.date(2026, 10, 6)

RESTAURANT = """
SPICE GARDEN RESTAURANT
12, MG Road, New Delhi 110001
GSTIN: 07AABCS1234F1Z5
Tax Invoice
Bill No: 4521        Date: 03/10/2026
Time: 20:42
Table 7
Item            Qty   Rate    Amount
Paneer Butter Masala  1  320.00  320.00
Butter Naan     4   45.00   180.00
Jeera Rice      1  150.00  150.00
Sweet Lassi     2   90.00   180.00
Sub Total                  830.00
CGST 2.5%                   20.75
SGST 2.5%                   20.75
Round off                    0.50-
Grand Total               Rs 872.00
Paid by UPI (GPay)
Thank you, visit again
"""

SUPERMARKET = """
D MART
Avenue Supermarts Ltd
Ph: 022 12345678
INVOICE 12-09-26 06:15 PM
Amul Milk 1L        2 x 68.00     136.00
Brown Bread         1             45.00
Eggs 12pc           1             84.00
Atta 5kg            1            265.00
TOTAL ITEMS 4  QTY 5
Total Savings 22.00
NET PAYABLE         530.00
CASH                600.00
CHANGE               70.00
"""

US_STYLE = """
STARBUCKS COFFEE
Store #1432
09/28/2026 08:14 AM
Latte Grande        5.45
Blueberry Muffin    3.25
Subtotal            8.70
Tax                 0.70
Total               $9.40
VISA ****1234
"""

NOISY = """
Z0MAT0 ORDER
Order lD 99887766
l5 Sep 2O26
Burger Combo   250.OO
Delivery fee   30.00
TOTAL          2B0.00
"""


def test_money_parsing():
    assert _to_float("1,250.50") == 1250.50
    assert _to_float("12,50") == 12.5
    assert _to_float("1,25,000") == 125000
    assert _to_float("1,250") == 1250


def test_restaurant_bill():
    r = parse_receipt_text(RESTAURANT, today=TODAY)
    assert r["ok"]
    assert r["merchant"].lower().startswith("spice garden")
    assert r["amount"] == 872.00
    assert r["timestamp"].startswith("2026-10-03T20:42")
    assert r["payment_method"] == "UPI"
    assert r["category"] == "Food"
    assert r["tax"] == 41.5
    assert len(r["items"]) == 4
    assert r["currency_hint"] == "INR"
    assert r["confidence"]["amount"] >= 0.9


def test_supermarket_bill():
    r = parse_receipt_text(SUPERMARKET, today=TODAY)
    assert r["amount"] == 530.00                      # NET PAYABLE, not CASH 600 / savings
    assert r["merchant"].lower().replace(" ", "") in ("dmart",)
    assert r["category"] == "Groceries"
    assert r["timestamp"].startswith("2026-09-12T18:15")
    assert r["payment_method"] == "Cash"
    assert [i["amount"] for i in r["items"]] == [136.0, 45.0, 84.0, 265.0]


def test_us_style_receipt():
    r = parse_receipt_text(US_STYLE, today=TODAY)
    assert r["amount"] == 9.40
    assert r["timestamp"].startswith("2026-09-28T08:14")   # 28 > 12 forces mm/dd
    assert r["payment_method"] == "Card"
    assert r["currency_hint"] == "USD"
    assert r["category"] == "Food"


def test_total_never_picks_subtotal_or_change():
    r = parse_receipt_text("Cafe X\nSubtotal 100\nTax 5\nTotal 105\nCash 200\nChange 95", today=TODAY)
    assert r["amount"] == 105


def test_future_date_rejected():
    r = parse_receipt_text("Shop\nTotal 50\n01/01/2031", today=TODAY)
    assert r["timestamp"] is None


def test_no_total_is_graceful():
    r = parse_receipt_text("hello world", today=TODAY)
    assert r["ok"] is False and r["reason"]
    assert parse_receipt_text("", today=TODAY)["ok"] is False


def test_duplicate_detection():
    existing = [{"id": 7, "amount": 872.0, "merchant": "Spice Garden", "timestamp": dt.datetime(2026, 10, 3, 21, 0)}]
    r = parse_receipt_text(RESTAURANT, existing, today=TODAY)
    assert r["possible_duplicates"] and r["possible_duplicates"][0]["id"] == 7
    other = [{"id": 8, "amount": 872.0, "merchant": "Totally Different", "timestamp": dt.datetime(2026, 10, 3, 21, 0)}]
    assert parse_receipt_text(RESTAURANT, other, today=TODAY)["possible_duplicates"] == []


def test_quick_text():
    r = parse_quick_text("450 swiggy dinner upi yesterday", today=TODAY)
    assert r["amount"] == 450 and r["merchant"] == "Swiggy"
    assert r["payment_method"] == "UPI" and r["category"] == "Food"
    assert r["timestamp"].startswith("2026-10-05")
    assert "dinner" in r["note"]

    r = parse_quick_text("spent rs 1.5k on uber to airport", today=TODAY)
    assert r["amount"] == 1500 and r["merchant"] == "Uber" and r["category"] == "Transport"

    r = parse_quick_text("paid 2,300 cash for electricity 3 days ago", today=TODAY)
    assert r["amount"] == 2300 and r["payment_method"] == "Cash" and r["timestamp"].startswith("2026-10-03")

    assert parse_quick_text("just some words", today=TODAY)["ok"] is False


# ---------------- accuracy hardening ----------------
from app.services.receipt_parser import parse_receipt_texts, _repair_token


def test_ocr_digit_repair():
    assert _repair_token("2B0.00") == "280.00"
    assert _repair_token("872.OO") == "872.00"
    assert _repair_token("l5") == "15"
    assert _repair_token("Rs.1,2S0.00") == "Rs.1,250.00"
    assert _repair_token("Paneer") == "Paneer"          # words untouched
    assert _repair_token("Z0MAT0") == "Z0MAT0"          # mixed brand name untouched


def test_noisy_receipt():
    r = parse_receipt_text("Z0MAT0 ORDER\nl5 Sep 2O26\nBurger Combo 250.OO\nDelivery fee 30.00\nTOTAL 2B0.00\nUPI", today=TODAY)
    assert r["amount"] == 280.0
    assert r["timestamp"].startswith("2026-09-15")


def test_split_decimal_rejoined():
    assert parse_receipt_text("Cafe Blue\nGrand Total Rs 872 .00\n", today=TODAY)["amount"] == 872.0


def test_date_prefers_labelled_line_over_expiry():
    r = parse_receipt_text("Chemist\nExp: 01/12/2026\nBill Date: 05/10/2026\nTotal 120.00", today=TODAY)
    assert r["timestamp"].startswith("2026-10-05")


def test_date_digit_misread_repaired():
    r = parse_receipt_text("Apollo Pharmacy\nBill Date: 28/09/2626\nTOTAL 1,245.50", today=TODAY)
    assert r["timestamp"].startswith("2026-09-28")
    assert parse_receipt_text("D Mart\nDate 12092026\nTOTAL 530.00", today=TODAY)["timestamp"].startswith("2026-09-12")


def test_arithmetic_check_fixes_dropped_digit():
    txt = "Spice Garden\nPaneer 320.00\nNaan 180.00\nRice 150.00\nLassi 180.00\nSub Total 830.00\nCGST 20.75\nSGST 20.75\nGrand Total 87.00\nNet Payable 872.00"
    r = parse_receipt_text(txt, today=TODAY)
    assert r["amount"] == 872.0 and 87.0 in r["amount_alternatives"]


def test_history_snaps_spelling_and_learns_category():
    hist = [{"merchant": "Apollo Pharmacy", "category": "Health"}] * 2
    r = parse_receipt_text("Apollo Pharmcy\nTotal 340.00\n05/10/2026", today=TODAY, history=hist)
    assert r["merchant"] == "Apollo Pharmacy" and r["merchant_source"] == "history"
    assert r["category"] == "Health" and r["category_source"] == "history"


def test_fuzzy_brand_from_typo():
    assert parse_receipt_text("Starbuoks\n05/10/2026\nTotal 450.00", today=TODAY)["merchant"].lower() == "starbucks"


def test_garbage_header_not_used_as_merchant():
    r = parse_receipt_text("Ne J 3\nBill Date: 12/09/2026\nNET PAYABLE 530.00", today=TODAY)
    assert r["merchant"] != "Ne J 3"


def test_multi_pass_prefers_consistent_parse():
    good = "Spice Garden\nPaneer 320.00\nNaan 180.00\nSub Total 500.00\nGrand Total 500.00\nUPI\n03/10/2026"
    bad = "Spice Garden\nPaneer 32O.00\nNaan 18O.00\nSub Total 5OO.00\nGrand Tota1 5.00\n"
    r = parse_receipt_texts([bad, good], today=TODAY)
    assert r["amount"] == 500.0 and r["passes"] == 2


def test_multi_pass_date_vote():
    a = "Cafe Blue\nDate: 03/16/2026\nTotal 100.00"       # misread day
    b = "Cafe Blue\nDate: 03/10/2026\nTotal 100.00"
    c = "Cafe Blue\nDate: 03/10/2026\nTotal 100.00"
    assert parse_receipt_texts([a, b, c], today=TODAY)["timestamp"].startswith("2026-10-03")


# ---------------- Insight Lab ----------------
def test_lab_endpoints_on_demo_data(tmp_path, monkeypatch):
    import shutil, os
    # a fresh database: the app seeds the demo account on first start
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 't.db'}")
    import importlib, sys
    for m in [k for k in sys.modules if k == "app" or k.startswith("app.")]:
        del sys.modules[m]
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    tok = c.post("/auth/login", json={"email": "demo@spendsense.app", "password": "demo1234"}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    p = c.get("/insights/persona", headers=h).json()
    assert p["available"] and p["name"] and p["traits"]
    r = c.get("/insights/roundup?step=10", headers=h).json()
    assert r["available"] and 0 < r["avg_per_purchase"] < 10 and r["projected_year"] > 0
    f = c.get("/insights/forecast", headers=h).json()
    assert f["available"] and len(f["days"]) == 14
    assert all(f["days"][i]["cumulative"] <= f["days"][i + 1]["cumulative"] for i in range(13))
