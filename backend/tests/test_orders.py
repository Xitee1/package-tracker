import pytest
from datetime import date, datetime, timezone
from decimal import Decimal

from app.models.order import Order
from app.models.order_state import OrderState


@pytest.fixture
async def admin_token(client):
    resp = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    return resp.json()["access_token"]


@pytest.fixture
async def user_token(client, admin_token):
    await client.post(
        "/api/v1/users",
        json={"username": "user1", "password": "pass"},
        headers=auth(admin_token),
    )
    login = await client.post("/api/v1/auth/login", json={"username": "user1", "password": "pass"})
    return login.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


async def _get_user_id(client, token):
    resp = await client.get("/api/v1/auth/me", headers=auth(token))
    return resp.json()["id"]


async def _create_order(db, user_id, **kwargs):
    defaults = {
        "user_id": user_id,
        "order_number": "ORD-001",
        "vendor_name": "Amazon",
        "status": "ordered",
    }
    defaults.update(kwargs)
    order = Order(**defaults)
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


# --- Create Order ---


@pytest.mark.asyncio
async def test_create_order_all_fields(client, admin_token):
    resp = await client.post(
        "/api/v1/orders",
        json={
            "vendor_name": "Amazon",
            "order_number": "ORD-NEW-001",
            "tracking_number": "1Z999AA1",
            "carrier": "UPS",
            "vendor_domain": "amazon.com",
            "status": "shipped",
            "order_date": "2026-02-15",
            "total_amount": 49.99,
            "currency": "EUR",
            "estimated_delivery": "2026-02-20",
            "items": [
                {"name": "Widget", "quantity": 2, "price": 24.99},
                {"name": "Gadget", "quantity": 1},
            ],
        },
        headers=auth(admin_token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["vendor_name"] == "Amazon"
    assert data["order_number"] == "ORD-NEW-001"
    assert data["tracking_number"] == "1Z999AA1"
    assert data["carrier"] == "UPS"
    assert data["status"] == "shipped"
    assert data["total_amount"] == "49.99"
    assert data["currency"] == "EUR"
    assert len(data["items"]) == 2
    assert data["items"][0]["name"] == "Widget"

    # Verify OrderState was created
    detail_resp = await client.get(f"/api/v1/orders/{data['id']}", headers=auth(admin_token))
    detail = detail_resp.json()
    assert len(detail["states"]) == 1
    assert detail["states"][0]["status"] == "shipped"
    assert detail["states"][0]["source_type"] == "manual"


@pytest.mark.asyncio
async def test_create_order_minimal(client, admin_token):
    resp = await client.post(
        "/api/v1/orders",
        json={"vendor_name": "eBay"},
        headers=auth(admin_token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["vendor_name"] == "eBay"
    assert data["status"] == "ordered"
    assert data["order_number"] is None
    assert data["items"] is None


@pytest.mark.asyncio
async def test_create_order_missing_vendor_name(client, admin_token):
    resp = await client.post(
        "/api/v1/orders",
        json={"order_number": "ORD-123"},
        headers=auth(admin_token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_order_invalid_status(client, admin_token):
    resp = await client.post(
        "/api/v1/orders",
        json={"vendor_name": "Amazon", "status": "bogus"},
        headers=auth(admin_token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_order_unauthenticated(client):
    resp = await client.post(
        "/api/v1/orders",
        json={"vendor_name": "Amazon"},
    )
    assert resp.status_code in (401, 403)


# --- List Orders ---


@pytest.mark.asyncio
async def test_list_orders_empty(client, admin_token):
    resp = await client.get("/api/v1/orders", headers=auth(admin_token))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_orders(client, db_session, admin_token):
    user_id = await _get_user_id(client, admin_token)
    await _create_order(db_session, user_id, order_number="ORD-001")
    await _create_order(db_session, user_id, order_number="ORD-002", vendor_name="eBay")

    resp = await client.get("/api/v1/orders", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    order_numbers = {o["order_number"] for o in data}
    assert order_numbers == {"ORD-001", "ORD-002"}


# --- Get Order Detail ---


@pytest.mark.asyncio
async def test_get_order_detail(client, db_session, admin_token):
    user_id = await _get_user_id(client, admin_token)
    order = await _create_order(db_session, user_id, order_number="ORD-100", vendor_name="BestBuy")

    # Add an OrderState
    state = OrderState(
        order_id=order.id,
        status="shipped",
        source_type="manual",
    )
    db_session.add(state)
    await db_session.commit()

    resp = await client.get(f"/api/v1/orders/{order.id}", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["order_number"] == "ORD-100"
    assert data["vendor_name"] == "BestBuy"
    assert len(data["states"]) == 1
    assert data["states"][0]["status"] == "shipped"
    assert data["states"][0]["source_type"] == "manual"


@pytest.mark.asyncio
async def test_get_order_not_found(client, admin_token):
    resp = await client.get("/api/v1/orders/9999", headers=auth(admin_token))
    assert resp.status_code == 404


# --- Update Order ---


@pytest.mark.asyncio
async def test_update_order(client, db_session, admin_token):
    user_id = await _get_user_id(client, admin_token)
    order = await _create_order(db_session, user_id, order_number="ORD-200")

    resp = await client.patch(
        f"/api/v1/orders/{order.id}",
        json={"tracking_number": "1Z999AA10123456784", "carrier": "UPS", "status": "shipped"},
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tracking_number"] == "1Z999AA10123456784"
    assert data["carrier"] == "UPS"
    assert data["status"] == "shipped"
    assert data["order_number"] == "ORD-200"  # unchanged


@pytest.mark.asyncio
async def test_update_order_creates_order_state(client, db_session, admin_token):
    """Updating status via API should create an OrderState entry."""
    user_id = await _get_user_id(client, admin_token)
    order = await _create_order(db_session, user_id, order_number="ORD-210")

    resp = await client.patch(
        f"/api/v1/orders/{order.id}",
        json={"status": "shipped"},
        headers=auth(admin_token),
    )
    assert resp.status_code == 200

    # Verify OrderState created
    resp = await client.get(f"/api/v1/orders/{order.id}", headers=auth(admin_token))
    data = resp.json()
    assert len(data["states"]) == 1
    assert data["states"][0]["status"] == "shipped"
    assert data["states"][0]["source_type"] == "manual"


@pytest.mark.asyncio
async def test_update_order_partial(client, db_session, admin_token):
    user_id = await _get_user_id(client, admin_token)
    order = await _create_order(db_session, user_id, order_number="ORD-201", vendor_name="Amazon")

    resp = await client.patch(
        f"/api/v1/orders/{order.id}",
        json={"vendor_name": "Amazon.de"},
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["vendor_name"] == "Amazon.de"
    assert data["order_number"] == "ORD-201"


@pytest.mark.asyncio
async def test_update_order_not_found(client, admin_token):
    resp = await client.patch(
        "/api/v1/orders/9999",
        json={"status": "shipped"},
        headers=auth(admin_token),
    )
    assert resp.status_code == 404


# --- Delete Order ---


@pytest.mark.asyncio
async def test_delete_order(client, db_session, admin_token):
    user_id = await _get_user_id(client, admin_token)
    order = await _create_order(db_session, user_id, order_number="ORD-300")

    resp = await client.delete(f"/api/v1/orders/{order.id}", headers=auth(admin_token))
    assert resp.status_code == 204

    # Verify it's gone
    resp = await client.get(f"/api/v1/orders/{order.id}", headers=auth(admin_token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_order_not_found(client, admin_token):
    resp = await client.delete("/api/v1/orders/9999", headers=auth(admin_token))
    assert resp.status_code == 404


# --- Filter by Status ---


@pytest.mark.asyncio
async def test_filter_by_status(client, db_session, admin_token):
    user_id = await _get_user_id(client, admin_token)
    await _create_order(db_session, user_id, order_number="ORD-400", status="ordered")
    await _create_order(db_session, user_id, order_number="ORD-401", status="shipped")
    await _create_order(db_session, user_id, order_number="ORD-402", status="delivered")
    await _create_order(db_session, user_id, order_number="ORD-403", status="shipped")

    resp = await client.get("/api/v1/orders?status=shipped", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all(o["status"] == "shipped" for o in data)


# --- Search ---


@pytest.mark.asyncio
async def test_search_by_order_number(client, db_session, admin_token):
    user_id = await _get_user_id(client, admin_token)
    await _create_order(db_session, user_id, order_number="ABC-123", vendor_name="Amazon")
    await _create_order(db_session, user_id, order_number="XYZ-789", vendor_name="eBay")

    resp = await client.get("/api/v1/orders?search=ABC", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["order_number"] == "ABC-123"


@pytest.mark.asyncio
async def test_search_by_vendor_name(client, db_session, admin_token):
    user_id = await _get_user_id(client, admin_token)
    await _create_order(db_session, user_id, order_number="ORD-500", vendor_name="Amazon")
    await _create_order(db_session, user_id, order_number="ORD-501", vendor_name="eBay")

    resp = await client.get("/api/v1/orders?search=eBay", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["vendor_name"] == "eBay"


@pytest.mark.asyncio
async def test_search_by_tracking_number(client, db_session, admin_token):
    user_id = await _get_user_id(client, admin_token)
    await _create_order(db_session, user_id, order_number="ORD-600", tracking_number="1Z999AA1")
    await _create_order(db_session, user_id, order_number="ORD-601", tracking_number="9400111899")

    resp = await client.get("/api/v1/orders?search=1Z999", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["tracking_number"] == "1Z999AA1"


# --- Link Orders ---


@pytest.mark.asyncio
async def test_link_orders(client, db_session, admin_token):
    user_id = await _get_user_id(client, admin_token)
    source = await _create_order(db_session, user_id, order_number="ORD-700", status="ordered")
    target = await _create_order(
        db_session, user_id, order_number="ORD-701",
        tracking_number="TRACK123", carrier="FedEx", status="shipped",
    )

    # Add an OrderState to the target
    state = OrderState(
        order_id=target.id,
        status="shipped",
        source_type="email",
    )
    db_session.add(state)
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/orders/{source.id}/link",
        json={"target_order_id": target.id},
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["merged_into"] == source.id

    # Verify source got the tracking info and status
    resp = await client.get(f"/api/v1/orders/{source.id}", headers=auth(admin_token))
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["tracking_number"] == "TRACK123"
    assert detail["carrier"] == "FedEx"
    assert detail["status"] == "shipped"
    # OrderState should have been migrated from target to source
    assert len(detail["states"]) == 1
    assert detail["states"][0]["status"] == "shipped"

    # Verify target is deleted
    resp = await client.get(f"/api/v1/orders/{target.id}", headers=auth(admin_token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_link_orders_not_found(client, admin_token):
    resp = await client.post(
        "/api/v1/orders/9999/link",
        json={"target_order_id": 8888},
        headers=auth(admin_token),
    )
    assert resp.status_code == 404


# --- User Isolation ---


@pytest.mark.asyncio
async def test_user_isolation(client, db_session, admin_token, user_token):
    admin_id = await _get_user_id(client, admin_token)
    user_id = await _get_user_id(client, user_token)

    admin_order = await _create_order(db_session, admin_id, order_number="ADMIN-001")
    user_order = await _create_order(db_session, user_id, order_number="USER-001")

    # Admin sees only admin's orders
    resp = await client.get("/api/v1/orders", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["order_number"] == "ADMIN-001"

    # User sees only user's orders
    resp = await client.get("/api/v1/orders", headers=auth(user_token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["order_number"] == "USER-001"

    # Admin can't access user's order by ID
    resp = await client.get(f"/api/v1/orders/{user_order.id}", headers=auth(admin_token))
    assert resp.status_code == 404

    # User can't access admin's order by ID
    resp = await client.get(f"/api/v1/orders/{admin_order.id}", headers=auth(user_token))
    assert resp.status_code == 404

    # User can't update admin's order
    resp = await client.patch(
        f"/api/v1/orders/{admin_order.id}",
        json={"status": "shipped"},
        headers=auth(user_token),
    )
    assert resp.status_code == 404

    # User can't delete admin's order
    resp = await client.delete(f"/api/v1/orders/{admin_order.id}", headers=auth(user_token))
    assert resp.status_code == 404


# --- Unauthenticated ---


@pytest.mark.asyncio
async def test_unauthenticated_access_denied(client):
    resp = await client.get("/api/v1/orders")
    assert resp.status_code in (401, 403)
