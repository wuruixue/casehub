"""用例 CRUD + 鉴权：正向 / 边界 / 异常"""
import pytest

from common.assertions import assert_status, assert_business_code, assert_json_contains
from common.http_client import HttpClient
from data.case_factory import make_case


@pytest.mark.smoke
def test_create_and_get(case_api, created_cases):
    """正向：创建后能查回来，字段一致"""
    payload = make_case()
    uuid = created_cases(payload)

    resp = case_api.get_case(uuid)
    assert_status(resp)
    assert_business_code(resp)
    assert_json_contains(resp.json().get("data", {}), {"name": payload["name"]})


def test_create_missing_name_should_fail(case_api):
    """异常：必填字段缺失 → HTTP 200 + 业务码 40001（统一错误模型）"""
    bad = make_case()
    bad.pop("name")
    resp = case_api.create_case(bad)
    assert_status(resp, 200)
    assert resp.json().get("code") != 0, f"缺少必填字段竟然创建成功"


def test_create_name_length_boundary(case_api, created_cases):
    """边界：名称 1/128 可创建，129 报错"""
    for length, expect_ok in [(1, True), (128, True), (129, False)]:
        payload = make_case(name="N" * length)
        resp = case_api.create_case(payload)
        if expect_ok:
            created_cases(payload)
            assert_business_code(resp)
        else:
            assert resp.json().get("code") != 0, f"超长名称 {length} 竟然创建成功"


def test_update_then_verify(case_api, created_cases):
    """编辑后立即回查，防止只改了列表缓存"""
    uuid = created_cases(make_case())
    new_name = make_case()["name"]
    resp = case_api.update_case(uuid, {"name": new_name})
    assert_status(resp)

    detail = case_api.get_case(uuid).json().get("data", {})
    assert detail.get("name") == new_name, f"编辑未生效: {detail.get('name')}"


def test_delete_then_get_empty(case_api, created_cases):
    """删除后查询：data 应为空，不能还能查出完整记录"""
    uuid = created_cases(make_case())
    case_api.delete_cases([uuid])
    # 不从 created_cases 移除：teardown 重复删除不存在的 uuid 应无害（幂等删除）

    resp = case_api.get_case(uuid)
    data = resp.json().get("data") if resp.status_code == 200 else None
    assert not data, f"删除后仍能查到: {data}"


def test_request_without_token_rejected(base_url):
    """安全：不带 Token 访问受保护接口必须 401"""
    no_auth = HttpClient(base_url)          # 不带 token
    resp = no_auth.get("/api/cases", params={"page": 1, "pageSize": 1})
    assert resp.status_code == 401, f"无鉴权请求未被拦截: {resp.status_code}"
