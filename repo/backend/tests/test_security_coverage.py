"""Comprehensive security coverage tests for audit Section 8.3.

Covers: object-level authorization, tenant/data isolation,
admin/internal endpoint hardening, share-link URL architecture,
training topic uniqueness, KPI run scoping, seed/demo gating.
"""

from datetime import date, timedelta
from decimal import Decimal

from app.core.config import settings
from app.db.models import KPIDailyMetric, KPIJobRun
from app.services.auth_service import create_user


def _login(client, username: str, password: str = "ChangeMeNow123"):
    client.post("/api/v1/auth/logout")
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    return resp


def _create_manager102(db_session):
    create_user(
        db=db_session,
        username="manager102",
        password="ChangeMeNow123",
        display_name="Store Manager 102",
        roles=["store_manager"],
        store_id=102,
    )
    db_session.commit()


# ---------------------------------------------------------------------------
# A) Share-link URL architecture: no hardcoded localhost
# ---------------------------------------------------------------------------


def test_share_link_uses_config_frontend_base_url(client, monkeypatch) -> None:
    """When FRONTEND_BASE_URL is set, share links use it (not localhost)."""
    monkeypatch.setattr(settings, "frontend_base_url", "https://app.meridianops.io")
    _login(client, "manager")

    today = date.today()
    dashboard = client.post(
        "/api/v1/analytics/dashboards",
        json={
            "name": "URL Test Dashboard",
            "widgets": [{"id": "w1", "kind": "kpi", "title": "Rev", "metric": "revenue", "dimension": None, "x": 0, "y": 0, "w": 4, "h": 2}],
            "allowed_store_ids": [101],
            "default_start_date": (today - timedelta(days=7)).isoformat(),
            "default_end_date": today.isoformat(),
        },
    )
    assert dashboard.status_code == 200
    dashboard_id = dashboard.json()["id"]

    link_resp = client.post(f"/api/v1/analytics/dashboards/{dashboard_id}/share-links", json={})
    assert link_resp.status_code == 200
    share_url = link_resp.json()["share_url"]
    assert share_url.startswith("https://app.meridianops.io/")
    assert "localhost" not in share_url


def test_share_link_dev_fallback_works_when_config_absent(client, monkeypatch) -> None:
    """In dev env with FRONTEND_BASE_URL unset, fallback derives URL from request host."""
    monkeypatch.setattr(settings, "frontend_base_url", None)
    monkeypatch.setattr(settings, "app_env", "local")
    _login(client, "manager")

    today = date.today()
    dashboard = client.post(
        "/api/v1/analytics/dashboards",
        json={
            "name": "Fallback URL Dashboard",
            "widgets": [{"id": "w1", "kind": "kpi", "title": "Rev", "metric": "revenue", "dimension": None, "x": 0, "y": 0, "w": 4, "h": 2}],
            "allowed_store_ids": [101],
            "default_start_date": (today - timedelta(days=7)).isoformat(),
            "default_end_date": today.isoformat(),
        },
    )
    assert dashboard.status_code == 200
    dashboard_id = dashboard.json()["id"]

    link_resp = client.post(f"/api/v1/analytics/dashboards/{dashboard_id}/share-links", json={})
    assert link_resp.status_code == 200
    share_url = link_resp.json()["share_url"]
    assert "/shared/" in share_url


def test_share_link_prod_missing_frontend_url_returns_400(client, monkeypatch) -> None:
    """In production env with FRONTEND_BASE_URL unset, share-link creation returns 400."""
    monkeypatch.setattr(settings, "frontend_base_url", None)
    _login(client, "manager")
    monkeypatch.setattr(settings, "app_env", "production")

    today = date.today()
    dashboard = client.post(
        "/api/v1/analytics/dashboards",
        json={
            "name": "Prod Missing URL Dashboard",
            "widgets": [{"id": "w1", "kind": "kpi", "title": "Rev", "metric": "revenue", "dimension": None, "x": 0, "y": 0, "w": 4, "h": 2}],
            "allowed_store_ids": [101],
            "default_start_date": (today - timedelta(days=7)).isoformat(),
            "default_end_date": today.isoformat(),
        },
    )
    assert dashboard.status_code == 200
    dashboard_id = dashboard.json()["id"]

    link_resp = client.post(f"/api/v1/analytics/dashboards/{dashboard_id}/share-links", json={})
    assert link_resp.status_code == 400
    assert "FRONTEND_BASE_URL" in link_resp.json()["detail"]


def test_share_link_prod_with_frontend_url_works(client, monkeypatch) -> None:
    """In production env with FRONTEND_BASE_URL set, share-link creation succeeds."""
    monkeypatch.setattr(settings, "frontend_base_url", "https://prod.meridianops.io")
    _login(client, "manager")
    monkeypatch.setattr(settings, "app_env", "production")

    today = date.today()
    dashboard = client.post(
        "/api/v1/analytics/dashboards",
        json={
            "name": "Prod URL Dashboard",
            "widgets": [{"id": "w1", "kind": "kpi", "title": "Rev", "metric": "revenue", "dimension": None, "x": 0, "y": 0, "w": 4, "h": 2}],
            "allowed_store_ids": [101],
            "default_start_date": (today - timedelta(days=7)).isoformat(),
            "default_end_date": today.isoformat(),
        },
    )
    assert dashboard.status_code == 200
    dashboard_id = dashboard.json()["id"]

    link_resp = client.post(f"/api/v1/analytics/dashboards/{dashboard_id}/share-links", json={})
    assert link_resp.status_code == 200
    assert link_resp.json()["share_url"].startswith("https://prod.meridianops.io/")


def test_share_link_list_uses_config_url(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "frontend_base_url", "https://network.local:5173")
    _login(client, "manager")

    today = date.today()
    dashboard = client.post(
        "/api/v1/analytics/dashboards",
        json={
            "name": "List URL Dashboard",
            "widgets": [{"id": "w1", "kind": "kpi", "title": "Rev", "metric": "revenue", "dimension": None, "x": 0, "y": 0, "w": 4, "h": 2}],
            "allowed_store_ids": [101],
            "default_start_date": (today - timedelta(days=7)).isoformat(),
            "default_end_date": today.isoformat(),
        },
    )
    dashboard_id = dashboard.json()["id"]
    client.post(f"/api/v1/analytics/dashboards/{dashboard_id}/share-links", json={})

    list_resp = client.get(f"/api/v1/analytics/dashboards/{dashboard_id}/share-links")
    assert list_resp.status_code == 200
    for link in list_resp.json():
        assert link["share_url"].startswith("https://network.local:5173/")


# ---------------------------------------------------------------------------
# B) Training topic uniqueness: store-scoped, 409 on duplicate
# ---------------------------------------------------------------------------


def test_training_topic_duplicate_within_same_store_returns_409(client) -> None:
    _login(client, "manager")
    first = client.post(
        "/api/v1/training/topics",
        json={"code": "DUP-TEST", "name": "Dup Test", "difficulty": "easy"},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/v1/training/topics",
        json={"code": "DUP-TEST", "name": "Dup Test 2", "difficulty": "easy"},
    )
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"].lower()


def test_training_topic_same_code_allowed_across_stores(client, db_session) -> None:
    _create_manager102(db_session)

    _login(client, "manager")
    first = client.post(
        "/api/v1/training/topics",
        json={"code": "CROSS-STORE", "name": "Cross Store 101", "difficulty": "easy"},
    )
    assert first.status_code == 200

    _login(client, "manager102")
    second = client.post(
        "/api/v1/training/topics",
        json={"code": "CROSS-STORE", "name": "Cross Store 102", "difficulty": "easy"},
    )
    assert second.status_code == 200


def test_training_topic_duplicate_does_not_return_500(client) -> None:
    """Ensure duplicate topic does NOT throw 500 (IntegrityError) but a controlled 4xx."""
    _login(client, "manager")
    client.post(
        "/api/v1/training/topics",
        json={"code": "NO-500", "name": "No 500", "difficulty": "easy"},
    )
    resp = client.post(
        "/api/v1/training/topics",
        json={"code": "NO-500", "name": "No 500 Again", "difficulty": "easy"},
    )
    assert resp.status_code in (400, 409)
    assert resp.status_code != 500


# ---------------------------------------------------------------------------
# C) KPI run-history object-level authorization
# ---------------------------------------------------------------------------


def test_kpi_runs_scoped_for_store_manager(client, db_session) -> None:
    """Store manager only sees runs that include their store."""
    import json as json_mod

    run_101 = KPIJobRun(
        job_name="nightly_kpi_materialization",
        trigger_type="manual",
        status="success",
        processed_from_date=date.today(),
        processed_to_date=date.today(),
        records_written=5,
        store_ids_json=json_mod.dumps([101]),
        attempts_made=1,
        max_attempts=3,
    )
    run_102 = KPIJobRun(
        job_name="nightly_kpi_materialization",
        trigger_type="manual",
        status="success",
        processed_from_date=date.today(),
        processed_to_date=date.today(),
        records_written=5,
        store_ids_json=json_mod.dumps([102]),
        attempts_made=1,
        max_attempts=3,
    )
    db_session.add_all([run_101, run_102])
    db_session.commit()

    _login(client, "manager")
    resp = client.get("/api/v1/ops/kpi/runs")
    assert resp.status_code == 200
    runs = resp.json()
    for run in runs:
        assert run["id"] != run_102.id, "Manager (store 101) should not see store 102 run"


def test_kpi_runs_admin_sees_all(client, db_session) -> None:
    """Admin sees all runs regardless of store scope."""
    import json as json_mod

    run = KPIJobRun(
        job_name="nightly_kpi_materialization",
        trigger_type="manual",
        status="success",
        processed_from_date=date.today(),
        processed_to_date=date.today(),
        records_written=5,
        store_ids_json=json_mod.dumps([102, 103]),
        attempts_made=1,
        max_attempts=3,
    )
    db_session.add(run)
    db_session.commit()

    _login(client, "admin")
    resp = client.get("/api/v1/ops/kpi/runs")
    assert resp.status_code == 200
    run_ids = [r["id"] for r in resp.json()]
    assert run.id in run_ids


def test_kpi_runs_manager_gets_full_limit_despite_out_of_scope_rows(client, db_session) -> None:
    """Regression: SQL filter before LIMIT ensures manager gets results even when
    many newer out-of-scope rows exist."""
    import json as json_mod

    for _ in range(10):
        db_session.add(KPIJobRun(
            job_name="nightly_kpi_materialization",
            trigger_type="scheduled",
            status="success",
            processed_from_date=date.today(),
            processed_to_date=date.today(),
            records_written=1,
            store_ids_json=json_mod.dumps([102]),
            attempts_made=1,
            max_attempts=3,
        ))
    older_101 = KPIJobRun(
        job_name="nightly_kpi_materialization",
        trigger_type="manual",
        status="success",
        processed_from_date=date.today() - timedelta(days=5),
        processed_to_date=date.today() - timedelta(days=5),
        records_written=3,
        store_ids_json=json_mod.dumps([101]),
        attempts_made=1,
        max_attempts=3,
    )
    db_session.add(older_101)
    db_session.commit()

    _login(client, "manager")
    resp = client.get("/api/v1/ops/kpi/runs", params={"limit": 5})
    assert resp.status_code == 200
    runs = resp.json()
    assert any(r["id"] == older_101.id for r in runs), (
        "Manager must see older store-101 run even when 10 newer store-102 runs exist"
    )
    for r in runs:
        assert r["id"] != older_101.id or r["records_written"] == 3


def test_kpi_runs_manager_cannot_see_unscoped_legacy_runs(client, db_session) -> None:
    """Runs without store_ids_json (legacy) are hidden from store managers."""
    legacy_run = KPIJobRun(
        job_name="nightly_kpi_materialization",
        trigger_type="scheduled",
        status="success",
        processed_from_date=date.today(),
        processed_to_date=date.today(),
        records_written=10,
        store_ids_json=None,
        attempts_made=1,
        max_attempts=3,
    )
    db_session.add(legacy_run)
    db_session.commit()

    _login(client, "manager")
    resp = client.get("/api/v1/ops/kpi/runs")
    assert resp.status_code == 200
    run_ids = [r["id"] for r in resp.json()]
    assert legacy_run.id not in run_ids


def test_kpi_runs_manager_does_not_500(client, db_session) -> None:
    """Regression guard: manager-scoped /kpi/runs must never 500.

    This path exercises the SQL-level or_() filter in
    kpi_service._store_id_json_contains.  A missing import or runtime
    NameError would surface as HTTP 500 here.
    """
    import json as json_mod

    db_session.add(KPIJobRun(
        job_name="nightly_kpi_materialization",
        trigger_type="manual",
        status="success",
        processed_from_date=date.today(),
        processed_to_date=date.today(),
        records_written=1,
        store_ids_json=json_mod.dumps([101]),
        attempts_made=1,
        max_attempts=3,
    ))
    db_session.commit()

    _login(client, "manager")
    resp = client.get("/api/v1/ops/kpi/runs")
    assert resp.status_code == 200, (
        f"Expected 200 but got {resp.status_code}: {resp.text}"
    )
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# D) Seed/demo endpoint gating
# ---------------------------------------------------------------------------


def test_seed_demo_denied_when_feature_flag_off(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "seed_demo_enabled", False)
    _login(client, "admin")
    resp = client.post("/api/v1/ops/seed/demo")
    assert resp.status_code == 403
    assert "disabled" in resp.json()["detail"].lower()


def test_seed_demo_denied_in_production_env(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "seed_demo_enabled", True)
    _login(client, "admin")
    monkeypatch.setattr(settings, "app_env", "production")
    resp = client.post("/api/v1/ops/seed/demo")
    assert resp.status_code == 403
    assert "production" in resp.json()["detail"].lower()


def test_seed_demo_allowed_when_flag_on_and_non_prod(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "seed_demo_enabled", True)
    monkeypatch.setattr(settings, "app_env", "local")
    _login(client, "admin")
    resp = client.post("/api/v1/ops/seed/demo")
    assert resp.status_code == 200


def test_seed_demo_denied_for_non_admin(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "seed_demo_enabled", True)
    monkeypatch.setattr(settings, "app_env", "local")
    _login(client, "manager")
    resp = client.post("/api/v1/ops/seed/demo")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# E) Object-level authorization: analytics/audit/store scoped access
# ---------------------------------------------------------------------------


def test_manager_cannot_access_other_store_dashboard(client, db_session) -> None:
    _create_manager102(db_session)

    _login(client, "manager")
    today = date.today()
    dashboard = client.post(
        "/api/v1/analytics/dashboards",
        json={
            "name": "Store 101 Only",
            "widgets": [{"id": "w1", "kind": "kpi", "title": "Rev", "metric": "revenue", "dimension": None, "x": 0, "y": 0, "w": 4, "h": 2}],
            "allowed_store_ids": [101],
            "default_start_date": (today - timedelta(days=7)).isoformat(),
            "default_end_date": today.isoformat(),
        },
    )
    assert dashboard.status_code == 200
    dashboard_id = dashboard.json()["id"]

    _login(client, "manager102")
    detail = client.get(f"/api/v1/analytics/dashboards/{dashboard_id}")
    assert detail.status_code == 403


def test_manager_analytics_list_excludes_other_store_dashboards(client, db_session) -> None:
    _create_manager102(db_session)

    _login(client, "manager")
    today = date.today()
    client.post(
        "/api/v1/analytics/dashboards",
        json={
            "name": "Store 101 Exclusive",
            "widgets": [{"id": "w1", "kind": "kpi", "title": "Rev", "metric": "revenue", "dimension": None, "x": 0, "y": 0, "w": 4, "h": 2}],
            "allowed_store_ids": [101],
            "default_start_date": (today - timedelta(days=7)).isoformat(),
            "default_end_date": today.isoformat(),
        },
    )

    _login(client, "manager102")
    listed = client.get("/api/v1/analytics/dashboards")
    assert listed.status_code == 200
    for d in listed.json():
        assert 101 not in d["allowed_store_ids"] or 102 in d["allowed_store_ids"]


# ---------------------------------------------------------------------------
# E) Tenant/data isolation: inventory cross-store checks
# ---------------------------------------------------------------------------


def test_inventory_positions_store_isolation(client, db_session) -> None:
    """Store manager cannot see inventory positions from another store."""
    _create_manager102(db_session)

    _login(client, "manager")
    positions_101 = client.get("/api/v1/inventory/positions")
    assert positions_101.status_code == 200

    _login(client, "manager102")
    positions_102 = client.get("/api/v1/inventory/positions")
    assert positions_102.status_code == 200
    for pos in positions_102.json():
        assert pos.get("store_id") in (102, None)


# ---------------------------------------------------------------------------
# E) Admin/internal protection: scheduler controls
# ---------------------------------------------------------------------------


def test_scheduler_start_denied_for_manager(client) -> None:
    _login(client, "manager")
    resp = client.post("/api/v1/ops/scheduler/start")
    assert resp.status_code == 403


def test_scheduler_stop_denied_for_manager(client) -> None:
    _login(client, "manager")
    resp = client.post("/api/v1/ops/scheduler/stop")
    assert resp.status_code == 403


def test_scheduler_status_denied_for_employee(client) -> None:
    _login(client, "employee")
    resp = client.get("/api/v1/ops/scheduler/status")
    assert resp.status_code == 403


def test_scheduler_status_denied_for_cashier(client) -> None:
    _login(client, "cashier")
    resp = client.get("/api/v1/ops/scheduler/status")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# E) Authentication: unauthenticated access returns 401
# ---------------------------------------------------------------------------


def test_unauthenticated_kpi_runs_returns_401(client) -> None:
    resp = client.get("/api/v1/ops/kpi/runs")
    assert resp.status_code == 401


def test_unauthenticated_training_topics_returns_401(client) -> None:
    resp = client.get("/api/v1/training/topics")
    assert resp.status_code == 401


def test_unauthenticated_analytics_dashboards_returns_401(client) -> None:
    resp = client.get("/api/v1/analytics/dashboards")
    assert resp.status_code == 401


def test_unauthenticated_seed_demo_returns_401(client) -> None:
    resp = client.post("/api/v1/ops/seed/demo")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# E) Route authorization: role-based access
# ---------------------------------------------------------------------------


def test_employee_cannot_create_training_topic(client) -> None:
    _login(client, "employee")
    resp = client.post(
        "/api/v1/training/topics",
        json={"code": "UNAUTH-TOPIC", "name": "Unauthorized", "difficulty": "easy"},
    )
    assert resp.status_code == 403


def test_cashier_cannot_access_kpi_backfill(client) -> None:
    _login(client, "cashier")
    resp = client.post(
        "/api/v1/ops/kpi/backfill",
        json={"start_date": date.today().isoformat(), "end_date": date.today().isoformat()},
    )
    assert resp.status_code == 403


def test_employee_cannot_access_analytics(client) -> None:
    _login(client, "employee")
    resp = client.get("/api/v1/analytics/dashboards")
    assert resp.status_code == 403
