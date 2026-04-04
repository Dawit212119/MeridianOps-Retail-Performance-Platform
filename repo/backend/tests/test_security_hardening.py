"""Tests for security hardening: bcrypt-only, at-rest encryption, audit store isolation."""

from decimal import Decimal

from app.core.encryption import FieldEncryptor
from app.core.security import hash_password, verify_password
from app.services.auth_service import create_user


def _login(client, username: str, password: str = "ChangeMeNow123"):
    client.post("/api/v1/auth/logout")
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200


# --- bcrypt-only tests ---


def test_bcrypt_only_hash_produces_bcrypt_prefix():
    """Ensure hash_password always produces bcrypt hashes (prefix $2b$)."""
    hashed = hash_password("TestPassword123")
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")


def test_bcrypt_verify_correct_password():
    hashed = hash_password("SecurePass12345")
    assert verify_password("SecurePass12345", hashed) is True


def test_bcrypt_verify_wrong_password():
    hashed = hash_password("SecurePass12345")
    assert verify_password("WrongPassword99", hashed) is False


def test_bcrypt_module_is_available():
    """bcrypt is now a hard import — this test verifies it doesn't silently fall back."""
    import app.core.security as sec
    assert hasattr(sec, '_bcrypt')
    assert sec._bcrypt is not None


# --- Audit endpoint auth/role tests ---


def test_audit_events_endpoint_requires_auth(client) -> None:
    resp = client.get("/api/v1/audit/events")
    assert resp.status_code == 401


def test_audit_events_endpoint_requires_manager_role(client) -> None:
    _login(client, "employee")
    resp = client.get("/api/v1/audit/events")
    assert resp.status_code == 403


def test_audit_events_accessible_by_admin(client) -> None:
    _login(client, "admin")
    resp = client.get("/api/v1/audit/events")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_audit_member_events_endpoint(client) -> None:
    _login(client, "admin")
    resp = client.get("/api/v1/audit/events/member")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_audit_campaign_events_endpoint(client) -> None:
    _login(client, "admin")
    resp = client.get("/api/v1/audit/events/campaign")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_audit_order_events_endpoint(client) -> None:
    _login(client, "admin")
    resp = client.get("/api/v1/audit/events/order")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_audit_events_filter_by_resource_type(client) -> None:
    _login(client, "admin")
    resp = client.get("/api/v1/audit/events?resource_type=member")
    assert resp.status_code == 200


def test_audit_events_filter_by_action(client) -> None:
    _login(client, "admin")
    resp = client.get("/api/v1/audit/events?action=member")
    assert resp.status_code == 200


# --- F1: Cross-store audit isolation for store_manager ---


def test_manager_audit_events_scoped_to_own_store(client, db_session) -> None:
    """Store manager must only see audit events for their own store, not other stores."""
    create_user(
        db=db_session,
        username="manager102",
        password="ChangeMeNow123",
        display_name="Store Manager 102",
        roles=["store_manager"],
        store_id=102,
    )
    db_session.commit()

    # Manager (store 101) creates a member — generates audit event scoped to store 101
    _login(client, "manager")
    client.post(
        "/api/v1/members",
        json={
            "member_code": "AUDIT-MEM-101",
            "full_name": "Store 101 Member",
            "tier": "base",
            "stored_value_enabled": False,
        },
    )

    # Manager102 (store 102) should NOT see store 101 audit events
    _login(client, "manager102")
    resp = client.get("/api/v1/audit/events")
    assert resp.status_code == 200
    events = resp.json()
    for event in events:
        # Should only see events with store_id=102 or store_id=None (unscoped)
        assert event.get("store_id") in (102, None), (
            f"Manager102 saw cross-store audit event: store_id={event.get('store_id')}, action={event.get('action')}"
        )


def test_admin_sees_all_audit_events(client, db_session) -> None:
    """Administrator should see audit events from all stores."""
    # Create some audit events via member creation
    _login(client, "manager")
    client.post(
        "/api/v1/members",
        json={
            "member_code": "AUDIT-ALL-1",
            "full_name": "Admin Test Member",
            "tier": "base",
            "stored_value_enabled": False,
        },
    )

    _login(client, "admin")
    resp = client.get("/api/v1/audit/events")
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) >= 1


# --- F2: Wallet encryption at-rest validation ---


def test_wallet_encryption_roundtrip_with_encryptor():
    """Verify that the FieldEncryptor produces ciphertext that differs from plaintext for amounts."""
    encryptor = FieldEncryptor("test-wallet-encryption-key")
    plaintext_amount = "50.00"
    encrypted = encryptor.encrypt(plaintext_amount)

    assert encrypted is not None
    assert encrypted != plaintext_amount  # Must be different (encrypted)
    assert encryptor.decrypt(encrypted) == plaintext_amount  # Must round-trip


def test_wallet_credit_debit_flow_stores_correctly(client) -> None:
    """Verify wallet operations work end-to-end through the String column storage."""
    _login(client, "manager")

    # Create member with wallet
    created = client.post(
        "/api/v1/members",
        json={
            "member_code": "WALLET-ENC-1",
            "full_name": "Wallet Enc Test",
            "tier": "silver",
            "stored_value_enabled": True,
        },
    )
    assert created.status_code == 200
    assert Decimal(created.json()["wallet_balance"]) == Decimal("0.00")

    # Credit
    credit = client.post(
        "/api/v1/members/WALLET-ENC-1/wallet/credit",
        json={"amount": "75.50", "reason": "enc test credit"},
    )
    assert credit.status_code == 200
    assert Decimal(credit.json()["wallet_balance"]) == Decimal("75.50")

    # Debit
    debit = client.post(
        "/api/v1/members/WALLET-ENC-1/wallet/debit",
        json={"amount": "25.25", "reason": "enc test debit"},
    )
    assert debit.status_code == 200
    assert Decimal(debit.json()["wallet_balance"]) == Decimal("50.25")

    # Verify ledger entries are readable
    ledger = client.get("/api/v1/members/WALLET-ENC-1/wallet-ledger")
    assert ledger.status_code == 200
    entries = ledger.json()
    assert len(entries) >= 2
    # Most recent entry (debit) should show correct balance
    latest = entries[0]
    assert Decimal(latest["balance_after"]) == Decimal("50.25")


def test_wallet_insufficient_debit_rejected(client) -> None:
    """Verify insufficient debit is still properly rejected with String column storage."""
    _login(client, "manager")
    client.post(
        "/api/v1/members",
        json={
            "member_code": "WALLET-INSUF",
            "full_name": "Insufficient Test",
            "tier": "base",
            "stored_value_enabled": True,
        },
    )
    client.post(
        "/api/v1/members/WALLET-INSUF/wallet/credit",
        json={"amount": "10.00", "reason": "seed"},
    )
    resp = client.post(
        "/api/v1/members/WALLET-INSUF/wallet/debit",
        json={"amount": "20.00", "reason": "over debit"},
    )
    assert resp.status_code == 409
    assert "insufficient" in resp.json()["detail"].lower()
