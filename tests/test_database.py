import datetime
import os
import tempfile
import database as db


def fresh():
    db.DB_PATH = os.path.join(tempfile.mkdtemp(), "t.duckdb")
    db.init_db()


def test_register_and_login():
    fresh()
    assert db.create_user("Ada", "ada@shop.ng", "Sunshine77")
    assert not db.create_user("ada", "other@shop.ng", "Sunshine77")
    assert db.verify_user("ADA", "Sunshine77") == "ada"
    assert db.verify_user("ada@shop.ng", "Sunshine77") == "ada"
    assert db.verify_user("ada", "wrong-pass") is None


def test_weak_passwords_rejected():
    fresh()
    for bad in ("short1", "12345678", "password"):
        assert db.password_problem(bad)
    assert not db.create_user("zed", "z@z.ng", "12345678")


def test_sessions():
    fresh()
    db.create_user("ada", "ada@shop.ng", "Sunshine77")
    t = db.create_session("ada")
    assert db.get_session_user(t) == "ada"
    db.delete_session(t)
    assert db.get_session_user(t) is None


def test_scenarios_roundtrip():
    fresh()
    db.save_scenario_db("ada", "Price +5%", "k1", {"revenue": 10.0, "costs": 5.0, "net_profit": 5.0, "profit_margin": 50.0})
    got = db.load_scenarios_db("ada", "k1")
    assert got[0]["scenario_name"] == "Price +5%"
    assert got[0]["margin"] == 50.0