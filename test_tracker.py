"""Everyday personal-tracker flows: goals (add/take out money), expense edit/search."""
import datetime as dt
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def auth(email):
    r = client.post("/auth/register", json={"name": "Tracker Tester", "email": email, "password": "password123", "age": 30})
    assert r.status_code == 201, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def test_goal_add_and_withdraw_money_with_history():
    h = auth("goal-flow@example.com")
    g = client.post("/goals", headers=h, json={"title": "Trip", "target_amount": 1000, "saved_amount": 100,
                                              "deadline": (dt.datetime.utcnow() + dt.timedelta(days=90)).isoformat()}).json()
    r = client.post(f"/goals/{g['id']}/contribute", headers=h, json={"amount": 250, "note": "salary"})
    assert r.status_code == 200 and r.json()["saved_amount"] == 350
    r = client.post(f"/goals/{g['id']}/contribute", headers=h, json={"amount": -50})
    assert r.json()["saved_amount"] == 300
    assert client.post(f"/goals/{g['id']}/contribute", headers=h, json={"amount": -999}).status_code == 422
    assert client.post(f"/goals/{g['id']}/contribute", headers=h, json={"amount": 0}).status_code == 422
    hist = client.get(f"/goals/{g['id']}/history", headers=h).json()
    assert [x["amount"] for x in hist] == [-50, 250] or [x["amount"] for x in hist] == [250, -50]
    r = client.patch(f"/goals/{g['id']}", headers=h, json={"title": "Big trip", "target_amount": 2000})
    assert r.json()["title"] == "Big trip" and r.json()["target_amount"] == 2000 and r.json()["saved_amount"] == 300
    # another user cannot touch it
    other = auth("goal-other@example.com")
    assert client.post(f"/goals/{g['id']}/contribute", headers=other, json={"amount": 5}).status_code == 404
    assert client.delete(f"/goals/{g['id']}", headers=h).status_code == 204


def test_expense_edit_search_and_date_filter():
    h = auth("exp-flow@example.com")
    e = client.post("/expenses", headers=h, json={"amount": 200, "merchant": "Swiggy", "payment_method": "UPI",
                                                 "timestamp": "2026-03-05T12:00:00"}).json()
    client.post("/expenses", headers=h, json={"amount": 50, "merchant": "Metro", "timestamp": "2026-04-05T12:00:00"})
    r = client.patch(f"/expenses/{e['id']}", headers=h, json={"amount": 260, "note": "team lunch", "category": "Food"})
    assert r.status_code == 200 and r.json()["amount"] == 260 and r.json()["note"] == "team lunch"
    assert [x["merchant"] for x in client.get("/expenses?q=swig", headers=h).json()] == ["Swiggy"]
    assert [x["merchant"] for x in client.get("/expenses?start=2026-04-01&end=2026-04-30", headers=h).json()] == ["Metro"]
    assert client.patch("/expenses/999999", headers=h, json={"amount": 5}).status_code == 404
    assert client.patch(f"/expenses/{e['id']}", headers=h, json={"amount": -5}).status_code == 422


def test_budgets_status_and_pace():
    h = auth("budget-flow@example.com")
    now = __import__("datetime").datetime.utcnow()
    client.post("/expenses", headers=h, json={"amount": 900, "merchant": "Swiggy", "category": "Food", "timestamp": now.isoformat()})
    r = client.put("/budgets/Food", headers=h, json={"monthly_limit": 1000}).json()
    assert r["items"][0]["status"] == "warn" and r["items"][0]["pct"] == 90.0
    r = client.put("/budgets/ALL", headers=h, json={"monthly_limit": 800}).json()
    assert r["overall"]["status"] == "over" and r["overall"]["remaining"] == -100
    assert client.put("/budgets/Nonsense", headers=h, json={"monthly_limit": 5}).status_code == 422
    assert client.put("/budgets/Food", headers=h, json={"monthly_limit": 0}).status_code == 422
    r = client.delete("/budgets/Food", headers=h).json()
    assert r["items"] == [] and r["overall"] is not None


def test_csv_import_flexible_headers_and_duplicates():
    h = auth("csv-flow@example.com")
    text = "Date,Description,Debit,Category\n05/03/2026,Swiggy order,\"1,250.50\",\n2026-03-06,Metro,60,Transport\nbad,Row,xx,\n"
    r = client.post("/expenses/import-csv", headers=h, json={"csv_text": text}).json()
    assert r == {"added": 2, "skipped": 1, "duplicates": 0}
    r = client.post("/expenses/import-csv", headers=h, json={"csv_text": text}).json()
    assert r["added"] == 0 and r["duplicates"] == 2
    rows = client.get("/expenses", headers=h).json()
    assert sorted(x["amount"] for x in rows) == [60, 1250.5]
    assert client.post("/expenses/import-csv", headers=h, json={"csv_text": "a,b\n1,2"}).status_code == 422


def test_change_password_and_delete_account():
    h = auth("acct-flow@example.com")
    assert client.post("/auth/change-password", headers=h, json={"current_password": "nope", "new_password": "newpassword1"}).status_code == 400
    assert client.post("/auth/change-password", headers=h, json={"current_password": "password123", "new_password": "newpassword1"}).status_code == 204
    assert client.post("/auth/login", json={"email": "acct-flow@example.com", "password": "newpassword1"}).status_code == 200
    client.post("/expenses", headers=h, json={"amount": 5, "merchant": "x"})
    client.post("/family", headers=h, json={"name": "Solo"})
    assert client.post("/auth/delete-account", headers=h, json={"password": "wrong"}).status_code == 400
    assert client.post("/auth/delete-account", headers=h, json={"password": "newpassword1"}).status_code == 204
    assert client.post("/auth/login", json={"email": "acct-flow@example.com", "password": "newpassword1"}).status_code == 401


def test_deleting_a_family_member_keeps_family_for_others():
    owner = auth("fam-owner@example.com")
    code = client.post("/family", headers=owner, json={"name": "Pair"}).json()["family"]["invite_code"]
    other = auth("fam-other@example.com")
    assert client.post("/family/join", headers=other, json={"code": code}).status_code == 200
    assert client.post("/auth/delete-account", headers=owner, json={"password": "password123"}).status_code == 204
    d = client.get("/family", headers=other).json()
    assert d["me"]["role"] == "owner" and len(d["members"]) == 1


def test_health_is_public_and_leaks_no_counts():
    d = client.get("/health").json()
    assert "tables" not in d["database"]
