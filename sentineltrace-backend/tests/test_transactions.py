def test_list_transactions_default_pagination(client):
    resp = client.get("/api/v1/transactions")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 50
    assert body["total"] == 38830  # canonical Stage 1 transaction count


def test_list_transactions_filtered_by_account(client):
    resp = client.get("/api/v1/transactions?account_id=0&limit=500")
    assert resp.status_code == 200
    body = resp.json()
    for tx in body["items"]:
        assert tx["src_account_id"] == 0 or tx["dst_account_id"] == 0
