"""
全局 fixture：在独立线程里拉起真实 FastAPI 服务（随机端口），整场测试共用
→ 测的是真 HTTP 链路，不是 mock
"""
import os
import socket
import sys
import threading
import time

import pytest
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.http_client import HttpClient   # noqa: E402
from api.case_api import CaseApi            # noqa: E402
from app.main import API_TOKEN              # noqa: E402


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def base_url():
    from app.main import app
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    for _ in range(50):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    t.join(timeout=5)


@pytest.fixture(scope="session")
def http(base_url):
    return HttpClient(base_url, token=API_TOKEN)


@pytest.fixture(scope="session")
def case_api(http):
    return CaseApi(http)


@pytest.fixture
def created_cases(case_api):
    """每条用例测试后自动清理，不污染环境"""
    created = []

    def _create(payload):
        resp = case_api.create_case(payload)
        assert resp.status_code == 200
        created.append(resp.json()["data"]["uuid"])
        return created[-1]

    yield _create

    valid = [u for u in created if u]
    if valid:
        case_api.delete_cases(valid)
