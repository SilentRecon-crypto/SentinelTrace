def test_list_accounts_default_pagination(client):
    resp = client.get("/api/v1/accounts")
    assert resp.status_code == 200
    body = resp.json()
    assert body["limit"] == 50
    assert body["offset"] == 0
    assert len(body["items"]) == 50
    assert body["total"] == 4025  # canonical Stage 1 account count


def test_list_accounts_pagination_offset(client):
    page1 = client.get("/api/v1/accounts?limit=10&offset=0").json()
    page2 = client.get("/api/v1/accounts?limit=10&offset=10").json()
    ids1 = {a["account_id"] for a in page1["items"]}
    ids2 = {a["account_id"] for a in page2["items"]}
    assert ids1.isdisjoint(ids2)


def test_get_existing_account(client):
    resp = client.get("/api/v1/accounts/0")
    assert resp.status_code == 200
    body = resp.json()
    assert body["account_id"] == 0
    assert "acc_type" in body
    assert "created_day" in body


def test_get_nonexistent_account_returns_404(client):
    resp = client.get("/api/v1/accounts/99999999")
    assert resp.status_code == 404
