import json

import pytest

import skelion_agent.control_plane as control_plane


class _Connection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, statement):
        return None


class _Engine:
    def connect(self):
        return _Connection()


class _Redis:
    async def ping(self):
        return True


@pytest.mark.asyncio
async def test_readiness_requires_database_and_redis(monkeypatch):
    monkeypatch.setattr(control_plane, "get_engine", lambda: _Engine())
    monkeypatch.setattr(control_plane, "redis_client", _Redis())

    response = await control_plane.readiness_check()

    assert response.status_code == 200
    assert json.loads(response.body)["status"] == "ready"


@pytest.mark.asyncio
async def test_readiness_fails_when_redis_is_not_initialized(monkeypatch):
    monkeypatch.setattr(control_plane, "get_engine", lambda: _Engine())
    monkeypatch.setattr(control_plane, "redis_client", None)

    response = await control_plane.readiness_check()

    assert response.status_code == 503
    assert json.loads(response.body)["status"] == "not_ready"
