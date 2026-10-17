def test_health_endpoint_returns_ok(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["api_status"] == "ok"
    assert body["database_connected"] is True
    assert body["model_a_loaded"] is True
    assert body["model_a_version"] == "model_a_v1"
