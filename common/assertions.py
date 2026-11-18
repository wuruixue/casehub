"""业务断言封装：失败时输出可读差异（与之前设计一致）"""
import json


def assert_status(resp, expected=200):
    assert resp.status_code == expected, (
        f"HTTP 状态不符: 期望 {expected}, 实际 {resp.status_code}\n响应: {resp.text[:800]}"
    )


def assert_business_code(resp, expected_code=0):
    body = resp.json()
    assert body.get("code") == expected_code, (
        f"业务码不符: 期望 {expected_code}, 实际 {body.get('code')}, message={body.get('message')}"
    )


def assert_json_contains(actual: dict, expected: dict):
    """只断言关心的字段，递归比对"""
    for key, value in expected.items():
        assert key in actual, f"响应缺少字段 {key}\n响应: {json.dumps(actual, ensure_ascii=False)[:500]}"
        if isinstance(value, dict) and isinstance(actual[key], dict):
            assert_json_contains(actual[key], value)
        else:
            assert actual[key] == value, f"字段 {key} 不符: 期望 {value!r}, 实际 {actual[key]!r}"


def assert_page_result(body, expect_total_ge=1):
    data = body.get("data", {})
    records = data.get("records") or []
    assert len(records) >= expect_total_ge, f"分页记录数不足: {len(records)}"
    for r in records:
        assert "uuid" in r, f"记录缺少主键: {r}"
