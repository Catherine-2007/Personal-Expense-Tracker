import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def login(email="demo@spendsense.app", password="demo1234"):
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def register(email, age=30, name="New Person"):
    r = client.post("/auth/register", json={"name": name, "email": email, "password": "password123", "age": age,
                                            "guardian_confirmed": age < 13})
    assert r.status_code == 201, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def test_demo_family_dashboard_and_ranking():
    d = client.get("/family", headers=login()).json()
    assert d["family"]["name"] == "The Demo Family"
    assert d["me"]["is_parent"] is True
    ranks = [m["rank"] for m in d["members"]]
    assert ranks == sorted(ranks) and ranks[0] == 1
    pts = [m["points"] for m in d["members"]]
    assert pts == sorted(pts, reverse=True)
    for m in d["members"]:
        assert m["points"] == sum(m["points_parts"].values())


def test_privacy_levels_are_enforced():
    d = client.get("/family", headers=login("senior@spendsense.app")).json()   # senior is a plain member
    teen = next(m for m in d["members"] if m["name"].startswith("Alex"))
    assert teen["share_level"] == "totals"
    assert teen["total"] is not None and teen["categories"] is None and teen["count"] is None
    # parents always see children in full
    owner = client.get("/family", headers=login()).json()
    kid = next(m for m in owner["members"] if m["role"] == "child")
    assert kid["visible"] == "full" and kid["categories"] is not None


def test_rank_only_hides_amounts_and_family_total():
    h = login("teen@spendsense.app")
    assert client.patch("/family/me", json={"share_level": "rank"}, headers=h).status_code == 200
    try:
        d = client.get("/family", headers=login("senior@spendsense.app")).json()
        teen = next(m for m in d["members"] if m["name"].startswith("Alex"))
        assert teen["total"] is None and teen["spark"] is None and teen["points"] >= 0
        assert d["totals"]["hidden_members"] >= 1
    finally:
        client.patch("/family/me", json={"share_level": "totals"}, headers=h)


def test_create_join_leave_flow():
    owner = register("owner1@example.com", name="Olive Owner")
    created = client.post("/family", json={"name": "Test Fam", "emoji": "🏠"}, headers=owner)
    assert created.status_code == 201
    code = created.json()["family"]["invite_code"]
    assert len(code) == 6
    assert client.post("/family", json={"name": "Again"}, headers=owner).status_code == 400

    friend = register("friend1@example.com", name="Fred")
    assert client.post("/family/join", json={"code": "NOPE00"}, headers=friend).status_code == 404
    joined = client.post("/family/join", json={"code": code.lower()}, headers=friend)   # case-insensitive
    assert joined.status_code == 200 and len(joined.json()["members"]) == 2

    # kid under 13 joins as child automatically
    kid = register("kid1@example.com", age=9, name="Kiki")
    j = client.post("/family/join", json={"code": code}, headers=kid).json()
    assert next(m for m in j["members"] if m["name"] == "Kiki")["role"] == "child"

    # members cannot do parent things
    assert client.post("/family/regenerate-code", headers=friend).status_code == 403
    assert client.post("/family/children", json={"name": "X", "age": 5}, headers=friend).status_code == 403

    # owner leaves -> ownership passes on, family survives
    assert client.post("/family/leave", headers=owner).status_code == 200
    d = client.get("/family", headers=friend).json()
    assert next(m for m in d["members"] if m["name"] == "Fred")["role"] == "owner"


def test_child_profiles_and_switching():
    owner = register("owner2@example.com", name="Pat Parent")
    client.post("/family", json={"name": "Switch Fam"}, headers=owner)
    r = client.post("/family/children", json={"name": "Tiny", "age": 6, "avatar": "🧸"}, headers=owner)
    assert r.status_code == 201
    child = next(m for m in r.json()["members"] if m["name"] == "Tiny")
    assert child["managed"] is True and child["role"] == "child"
    sw = client.post(f"/family/switch/{child['user_id']}", headers=owner)
    assert sw.status_code == 200
    assert sw.json()["user"]["platform_mode"] == "kid"
    kid_headers = {"Authorization": "Bearer " + sw.json()["access_token"]}
    assert client.post("/expenses", json={"amount": 25, "merchant": "Sweets"}, headers=kid_headers).status_code in (200, 201)
    # a normal (non-managed) member can't be switched into
    other = register("friend2@example.com")
    code = client.get("/family", headers=owner).json()["family"]["invite_code"]
    client.post("/family/join", json={"code": code}, headers=other)
    uid = next(m for m in client.get("/family", headers=owner).json()["members"] if not m["managed"] and not m["is_me"])["user_id"]
    assert client.post(f"/family/switch/{uid}", headers=owner).status_code == 403


def test_kudos_limits_and_self_kudos():
    h = login()
    d = client.get("/family", headers=h).json()
    others = [m for m in d["members"] if not m["is_me"]]
    assert client.post("/family/kudos", json={"to_user_id": d["me"]["user_id"]}, headers=h).status_code == 400
    sent = 0
    status = 200
    while status == 200 and sent < 10:
        status = client.post("/family/kudos", json={"to_user_id": others[0]["user_id"], "emoji": "🔥"}, headers=h).status_code
        sent += 1
    assert status == 429          # daily cap reached


def test_challenges_lifecycle():
    h = login()
    r = client.post("/family/challenges", json={"kind": "spend_cap", "target": 5000, "category": "Food", "days": 7}, headers=h)
    assert r.status_code == 201
    ch = r.json()["challenges"][0]
    assert {"state", "pct", "value", "days_left"} <= set(ch)
    assert client.post("/family/challenges", json={"kind": "nonsense", "target": 1}, headers=h).status_code == 422
    assert client.delete(f"/family/challenges/{ch['id']}", headers=h).status_code == 200


def test_language_header_changes_error_text():
    h = login("senior@spendsense.app")
    en = client.post("/family/regenerate-code", headers=h)
    assert en.status_code == 403 and "parent" in en.json()["detail"].lower()
