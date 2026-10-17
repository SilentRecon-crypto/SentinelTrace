def test_list_complaints_default_pagination(client):
    resp = client.get("/api/v1/complaints")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 50
    assert body["total"] == 500  # canonical Stage 1 complaint count


def test_get_existing_complaint_has_chain(client):
    first_page = client.get("/api/v1/complaints?limit=1").json()
    complaint_id = first_page["items"][0]["complaint_id"]
    resp = client.get(f"/api/v1/complaints/{complaint_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["complaint_id"] == complaint_id
    assert isinstance(body["chain"], list)
    assert len(body["chain"]) == body["n_hops"]


def test_get_nonexistent_complaint_returns_404(client):
    resp = client.get("/api/v1/complaints/99999999")
    assert resp.status_code == 404
