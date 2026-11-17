from app.services.scoring import SeverityInput, Threshold, density_level, density_value, severity


# ---------------- auth ----------------
def test_register_login_me(client):
    r = client.post("/api/auth/register", json={"email": "a@test.in", "password": "Secret123!", "full_name": "Anil"})
    assert r.status_code == 201
    assert client.post("/api/auth/register", json={"email": "a@test.in", "password": "Secret123!",
                                                    "full_name": "Anil"}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "a@test.in", "password": "wrong"}).status_code == 401
    tok = client.post("/api/auth/login", json={"email": "A@test.in", "password": "Secret123!"}).json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"}).json()
    assert me["email"] == "a@test.in" and me["role"] == "farmer"
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_validation_errors(client):
    assert client.post("/api/auth/register", json={"email": "bad", "password": "x", "full_name": "A"}).status_code == 422


def test_forgot_and_reset_password(client):
    client.post("/api/auth/register", json={"email": "reset@test.in", "password": "Secret123!", "full_name": "Reset"})
    r = client.post("/api/auth/forgot-password", json={"email": "reset@test.in"}).json()
    assert "dev_reset_link" in r  # dev mode without SMTP
    token = r["dev_reset_link"].split("token=")[1]
    assert client.post("/api/auth/reset-password", json={"token": token, "new_password": "NewSecret123"}).status_code == 200
    assert client.post("/api/auth/reset-password", json={"token": token, "new_password": "Again12345"}).status_code == 400
    assert client.post("/api/auth/login", json={"email": "reset@test.in", "password": "NewSecret123"}).status_code == 200
    # unknown email gives the same message, no link
    r2 = client.post("/api/auth/forgot-password", json={"email": "nobody@test.in"}).json()
    assert "dev_reset_link" not in r2


# ---------------- profile ----------------
def test_profile_update(client, auth):
    crops = client.get("/api/crops").json()
    rice = next(c for c in crops if c["key"] == "rice")
    r = client.patch("/api/profile", headers=auth, json={
        "language": "hinglish", "crop_ids": [rice["id"]],
        "farm": {"name": "Khet 1", "location_name": "Nagpur", "latitude": 21.15, "longitude": 79.09}})
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["language"] == "hinglish" and p["crops"][0]["key"] == "rice" and p["farms"][0]["latitude"] == 21.15


# ---------------- scoring units ----------------
def test_density_methodology():
    assert density_value(4, "field_photo", None, None) == (4.0, "pests/image", "image_count")
    # 20 pests on a 200 cm² trap over 48 h -> 20 / 2 / 2 = 5 per 100 cm² per day
    assert density_value(20, "sticky_trap", 200, 48) == (5.0, "pests/100cm²/day", "trap_rate")
    # trap without metadata falls back to image count
    assert density_value(20, "sticky_trap", None, 48)[2] == "image_count"
    t = Threshold(1, 3, 6, 10)
    assert [density_level(v, t) for v in (0, 1, 3, 6, 10, 50)] == ["none", "low", "moderate", "high", "critical", "critical"]


def test_severity_scoring():
    t = Threshold(1, 3, 6, 10)
    assert severity(SeverityInput(densities=[], total_count=0, mean_confidence=None, stage=None))["level"] == "safe"
    s = severity(SeverityInput(densities=[{"pest": "bph", "value": 10, "unit": "pests/image", "level": "critical",
                                           "threshold": t, "weight": 1.4}], total_count=10, mean_confidence=0.8,
                               stage="flowering", stage_factor=1.4))
    assert s["level"] == "critical" and s["score"] == 100  # 60*1.4*1.4 = 117.6 -> capped
    low = severity(SeverityInput(densities=[{"pest": "x", "value": 1, "unit": "pests/image", "level": "low",
                                             "threshold": t, "weight": 1.0}], total_count=1, mean_confidence=0.9, stage=None))
    assert low["level"] == "low" and low["score"] == 6.0
    rising = severity(SeverityInput(densities=[{"pest": "x", "value": 5, "unit": "pests/image", "level": "moderate",
                                                "threshold": t, "weight": 1.0}], total_count=5, mean_confidence=0.9,
                                    stage=None, history={"x": [1, 2, 3]}))
    assert rising["score"] == 45.0 and any(f["name"] == "Trend" and f["value"] == "+15" for f in rising["factors"])


# ---------------- detection pipeline ----------------
def test_analyze_full_pipeline(client, auth, jpeg):
    crops = client.get("/api/crops").json()
    rice = next(c for c in crops if c["key"] == "rice")
    r = client.post("/api/detections/analyze", headers=auth,
                    files={"image": ("field.jpg", jpeg, "image/jpeg")},
                    data={"crop_id": rice["id"], "growth_stage": "flowering"})
    assert r.status_code == 201, r.text
    d = r.json()
    # stub: 6 candidates -> 1 below conf, 1 suppressed by NMS -> 4 detections
    assert d["total_count"] == 4
    assert d["class_counts"] == {"brown plant hopper": 3, "aphids": 1}
    assert d["low_confidence_count"] == 1
    # boxes mapped back from letterbox (800x600 -> scale 0.8, pad y 80): first BPH cx=100 -> 125px
    bph = max((i for i in d["instances"] if i["pest_class"] == "brown plant hopper"), key=lambda i: i["confidence"])
    assert abs((bph["x1"] + bph["x2"]) / 2 - 125) < 1 and abs((bph["y1"] + bph["y2"]) / 2 - 150) < 1
    assert d["severity"]["level"] in ("low", "moderate", "high", "critical")
    assert {x["pest_class"] for x in d["densities"]} == {"brown plant hopper", "aphids"}
    assert all(x["unit"] == "pests/image" for x in d["densities"])
    assert d["inference_ms"] >= 0 and d["model_version"] == "test-0"
    img = client.get(d["annotated_url"])
    assert img.status_code == 200 and img.headers["content-type"] == "image/jpeg"
    assert client.get(d["annotated_url"].replace("sig=", "sig=x")).status_code == 403


def test_trap_density_and_alerts(client, auth, jpeg):
    r = client.post("/api/detections/analyze", headers=auth, files={"image": ("trap.jpg", jpeg, "image/jpeg")},
                    data={"sample_type": "sticky_trap", "trap_area_cm2": "100", "observation_hours": "24"})
    d = r.json()
    bph = next(x for x in d["densities"] if x["pest_class"] == "brown plant hopper")
    assert bph["unit"] == "pests/100cm²/day" and bph["value"] == 3.0
    alerts = client.get("/api/alerts", headers=auth).json()
    assert any(a["type"] == "new_detection" for a in alerts)
    unread = client.get("/api/alerts/unread-count", headers=auth).json()["count"]
    aid = alerts[0]["id"]
    assert client.patch(f"/api/alerts/{aid}/read", headers=auth).json()["is_read"] is True
    assert client.get("/api/alerts/unread-count", headers=auth).json()["count"] == unread - 1


def test_custom_threshold_drives_critical_alert(client, auth, jpeg):
    r = client.put("/api/alerts/thresholds", headers=auth,
                   json={"pest_class": "brown plant hopper", "low": 1, "moderate": 1, "high": 2, "critical": 3})
    assert r.status_code == 200
    assert client.put("/api/alerts/thresholds", headers=auth, json={"pest_class": "x", "low": 5, "moderate": 1,
                                                                     "high": 2, "critical": 3}).status_code == 422
    d = client.post("/api/detections/analyze", headers=auth, files={"image": ("f.jpg", jpeg, "image/jpeg")}).json()
    assert next(x for x in d["densities"] if x["pest_class"] == "brown plant hopper")["level"] == "critical"
    alerts = client.get("/api/alerts", headers=auth).json()
    assert any(a["type"] == "critical_infestation" and a["detection_id"] == d["id"] for a in alerts)
    # follow-up reminder is scheduled, hidden until due
    sched = client.get("/api/alerts?include_scheduled=true", headers=auth).json()
    assert any(a["type"] == "follow_up" and a["detection_id"] == d["id"] for a in sched)
    assert not any(a["type"] == "follow_up" and a["detection_id"] == d["id"] for a in alerts)


def test_upload_validation(client, auth):
    assert client.post("/api/detections/analyze", headers=auth,
                       files={"image": ("x.txt", b"hello", "text/plain")}).status_code == 415
    assert client.post("/api/detections/analyze", headers=auth,
                       files={"image": ("x.jpg", b"not really a jpeg", "image/jpeg")}).status_code == 422
    assert client.post("/api/detections/analyze", files={"image": ("x.jpg", b"x", "image/jpeg")}).status_code == 401


def test_batch(client, auth, jpeg):
    r = client.post("/api/detections/batch", headers=auth,
                    files=[("images", ("a.jpg", jpeg, "image/jpeg")), ("images", ("b.jpg", jpeg, "image/jpeg"))])
    assert r.status_code == 201 and len(r.json()) == 2


def test_history_filters_privacy_exports(client, auth, auth2, jpeg):
    h = client.get("/api/detections/history", headers=auth).json()
    assert h["total"] >= 4
    assert client.get("/api/detections/history?pest=aphids", headers=auth).json()["total"] == h["total"]
    assert client.get("/api/detections/history?pest=rice%20leaf%20roller", headers=auth).json()["total"] == 0
    det_id = h["items"][0]["id"]
    # another farmer cannot see it
    assert client.get(f"/api/detections/{det_id}", headers=auth2).status_code == 404
    assert client.get("/api/detections/history", headers=auth2).json()["total"] == 0
    csv = client.get("/api/detections/export.csv", headers=auth)
    assert csv.status_code == 200 and csv.text.splitlines()[0].startswith("id,date_utc")
    assert len(csv.text.strip().splitlines()) == h["total"] + 1
    pdf = client.get(f"/api/detections/{det_id}/report.pdf", headers=auth)
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    assert client.get(f"/api/detections/{det_id}/report.pdf", headers=auth2).status_code == 404


def test_analytics(client, auth):
    o = client.get("/api/analytics/overview", headers=auth).json()
    assert o["total_scans"] >= 4 and o["most_frequent_pest"] == "brown plant hopper"
    assert sum(x["count"] for x in o["severity_distribution"]) == o["total_scans"]
    for period in ("daily", "weekly", "monthly"):
        t = client.get(f"/api/analytics/trends?period={period}", headers=auth).json()
        assert t["series"] and sum(s["scans"] for s in t["series"]) == o["total_scans"]
    assert client.get("/api/analytics/trends?period=hourly", headers=auth).status_code == 422


def test_treatments(client):
    t = client.get("/api/treatments/brown plant hopper").json()
    assert t["curated"] and t["safety"] and any("pyrethroid" in c["class"] for c in t["chemical_categories"])
    assert client.get("/api/treatments/Brown planthopper (BPH)").status_code == 200
    assert client.get("/api/treatments/unknown-bug").status_code == 404
    assert len(client.get("/api/treatments").json()) >= 25


def test_chat_kb_fallback_languages(client, auth):
    r = client.post("/api/chat/message", headers=auth, json={"message": "Meri fasal mein kaun sa keeda laga hai?"}).json()
    assert r["reply"]["source"] == "knowledge_base" and r["reply"]["language"] == "hinglish"
    assert "brown plant hopper" in r["reply"]["content"].lower()
    cid = r["conversation_id"]
    r2 = client.post("/api/chat/message", headers=auth, json={"message": "Neem oil ka use kaise hota hai?",
                                                              "conversation_id": cid}).json()
    assert "Neem oil" in r2["reply"]["content"]
    r3 = client.post("/api/chat/message", headers=auth, json={"message": "माहू का इलाज क्या है?"}).json()
    assert r3["reply"]["language"] == "hi"
    r4 = client.post("/api/chat/message", headers=auth,
                     json={"message": "How do I control aphids organically?"}).json()
    assert r4["reply"]["language"] == "en" and "Aphids" in r4["reply"]["content"]
    hist = client.get(f"/api/chat/history?conversation_id={cid}", headers=auth).json()
    assert [m["role"] for m in hist] == ["user", "assistant", "user", "assistant"]
    assert client.get("/api/chat/status").json()["llm_enabled"] is False


def test_admin_rbac(client, auth):
    assert client.get("/api/admin/stats", headers=auth).status_code == 403
    tok = client.post("/api/auth/login", json={"email": "admin@test.in", "password": "AdminPass123"}).json()["access_token"]
    adm = {"Authorization": f"Bearer {tok}"}
    s = client.get("/api/admin/stats", headers=adm).json()
    assert s["detections"] >= 4 and s["users"] >= 2
    assert any(u["email"] == "farmer1@test.in" for u in client.get("/api/admin/users", headers=adm).json())


def test_model_info(client):
    m = client.get("/api/model/info").json()
    assert m["available"] and m["num_classes"] == 3


def test_weather_no_location(client, auth2):
    assert client.get("/api/weather", headers=auth2).json()["status"] == "no_location"
