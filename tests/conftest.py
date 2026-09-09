import json
import socket
import duckdb
import pytest
from ontime import config as c
from ontime.split import assign_splits


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Tests must not use the network")
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket.socket, "connect", blocked)


@pytest.fixture(scope="session")
def con():
    if not c.DB.exists():
        pytest.fail("Run make build before the offline test suite")
    connection = duckdb.connect(str(c.DB), read_only=True, config={"threads": 1})
    yield connection
    connection.close()


@pytest.fixture(scope="session")
def frame(con):
    return assign_splits(con.table("model_fact").df())


@pytest.fixture(scope="session")
def metrics():
    return json.loads((c.OUTPUTS / "metrics.json").read_text())
