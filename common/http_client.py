"""
统一 HTTP 客户端：统一鉴权 header、请求日志、失败重试
被测服务是本地的 CaseHub（FastAPI），client 结构和真实项目一致
"""
import logging
import time

import requests

logger = logging.getLogger("api")


class HttpClient:
    def __init__(self, base_url: str, token: str = "", timeout: int = 10,
                 use_env_proxy: bool = False):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        # 机器上配置了 HTTP_PROXY 时，requests 会把 127.0.0.1 的请求也转发给代理，
        # 导致拿到的 404 根本不是被测服务返回的。默认绕过环境代理直连。
        # 测试外部环境（需要走公司代理）时再显式传 use_env_proxy=True
        self.session.trust_env = use_env_proxy
        self.timeout = timeout
        if token:
            self.session.headers.update({"X-API-Token": token})
        self.session.headers.update({"Content-Type": "application/json"})

    def request(self, method: str, path: str, retries: int = 0, **kwargs):
        url = f"{self.base_url}{path}"
        last_exc = None
        for attempt in range(retries + 1):
            try:
                logger.info("[%s] %s payload=%s", method, url, kwargs.get("json"))
                resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
                logger.info("-> %s %s", resp.status_code, resp.text[:300])
                return resp
            except requests.RequestException as e:
                last_exc = e
                if attempt < retries:
                    time.sleep(1 * (attempt + 1))
        raise last_exc

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, **kw):
        return self.request("POST", path, **kw)

    def put(self, path, **kw):
        return self.request("PUT", path, **kw)

    def delete(self, path, **kw):
        return self.request("DELETE", path, **kw)
