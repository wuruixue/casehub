"""列表筛选 + 分页 + 幂等导入。parametrize 数据驱动"""
import pytest

from common.assertions import assert_status, assert_business_code, assert_page_result
from data.case_factory import make_case, make_batch


@pytest.fixture(scope="module")
def seeded(case_api):
    """准备一批已知数据，模块内共用，跑完统一清理"""
    uuids = []
    plans = [
        {"name": f"{make_case()['name']}_PASS_A", "creator": "alice", "execResult": 1},
        {"name": f"{make_case()['name']}_PASS_B", "creator": "alice", "execResult": 1},
        {"name": f"{make_case()['name']}_FAIL_A", "creator": "bob", "execResult": 2},
        {"name": f"{make_case()['name']}_NONE_A", "creator": "bob", "execResult": 0},
    ]
    for p in plans:
        resp = case_api.create_case(p)
        uuids.append(resp.json()["data"]["uuid"])
    yield
    case_api.delete_cases(uuids)


@pytest.mark.parametrize(
    "filters, expect_min",
    [
        ({"name": "_PASS_"}, 2),         # 按名称模糊筛
        ({"creator": "alice"}, 2),       # 按创建人筛
        ({"exec_result": 2}, 1),         # 按执行结果筛
        ({"creator": "nobody_xyz"}, 0),  # 无结果
    ],
    ids=["by-name", "by-creator", "by-result", "empty-result"],
)
def test_list_filters(case_api, seeded, filters, expect_min):
    resp = case_api.list_cases(size=50, **filters)
    assert_status(resp)
    assert_business_code(resp)
    assert_page_result(resp.json(), expect_total_ge=expect_min)


def test_list_pagination(case_api, seeded):
    """分页大小生效，且页间数据不重复"""
    p1 = case_api.list_cases(page=1, size=2).json()["data"]
    p2 = case_api.list_cases(page=2, size=2).json()["data"]
    ids1 = {r["uuid"] for r in p1["records"]}
    ids2 = {r["uuid"] for r in p2["records"]}
    assert len(ids1) == 2 and len(ids2) == 2, "分页大小未生效"
    assert not (ids1 & ids2), "分页出现重复数据"


def test_import_idempotent(case_api):
    """幂等：同一 batchNo 重复提交导入，第二次必须 successCount=0。
    这条是从支付回调测试迁移来的习惯——面试重点讲"""
    batch_no = make_case()["name"]
    payload = {"batchNo": batch_no, "cases": make_batch(3)}

    r1 = case_api.import_cases(payload)
    r2 = case_api.import_cases(payload)

    assert_status(r1)
    assert_business_code(r1)
    assert r1.json()["data"]["successCount"] == 3
    assert r2.json()["data"]["successCount"] == 0, "重复导入幂等失效"
    assert r2.json()["data"]["duplicate"] is True


def test_import_invalid_case_fails_whole_batch(case_api):
    """导入里混入非法数据（超长名称），整批应失败，不能部分成功后状态不明"""
    cases = make_batch(2)
    cases.append(make_case(name="X" * 200))
    resp = case_api.import_cases({"batchNo": make_case()["name"], "cases": cases})
    assert resp.json().get("code") != 0, "非法数据混入竟然导入成功"
