from __future__ import annotations

from app.main import app


def test_expected_routes_are_registered() -> None:
    routes = {route.path for route in app.router.routes}
    assert '/calculate' in routes
    assert '/verify' in routes
    assert '/prove' in routes
    assert '/proof/{task_id}' in routes
    assert '/status' in routes
    assert '/dashboard' in routes
    assert '/run' in routes
    assert '/start' in routes
    assert '/stop' in routes
    assert '/healthz' in routes
    assert '/metrics' in routes
    assert '/training/dataset' in routes
    assert '/training/moat' in routes
