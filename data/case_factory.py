"""测试数据工厂：随机生成 + 唯一前缀标记"""
import random
import string
import time


def _suffix():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=6))


def make_case(name=None, creator="pytest_bot", exec_result=0, steps=None):
    ts = time.strftime("%Y%m%d%H%M%S")
    return {
        "name": name or f"AUTO_{ts}_{_suffix()}",
        "creator": creator,
        "execResult": exec_result,
        "steps": steps or [{"index": 1, "action": "request", "expectStatus": 200}],
    }


def make_batch(n, **overrides):
    return [make_case(**overrides) for _ in range(n)]
