# CaseHub · 用例管理服务 + 接口自动化测试（FastAPI + pytest）

> 一个自包含的全栈测试项目：**自己用 FastAPI 写被测服务，再用 pytest 对它做接口自动化**。
> 灵感来自我在天眼平台做的"用例列表"模块（CRUD/筛选/分页/导入），代码全部重写，不含任何公司内部信息。
> 当前状态：**13/13 用例通过，`pytest` 一条命令本地跑通，无需任何外部环境。**

## 为什么这么设计

面试官经常问"你有 Python 项目吗"。与其只交测试脚本，不如交付一个闭环：

```
app/main.py        被测服务（FastAPI）：CRUD + 筛选分页 + 幂等导入 + Token 鉴权
tests/…            接口自动化（pytest）：真 HTTP 调用，不是 mock
```

**既证明会写 Python，又证明测试设计能力，还省去了"没有可测环境"的尴尬**——服务就在测试的 fixture 里拉起，换台电脑照样跑。

## 结构

```
app/main.py              被测服务：6 个接口，统一响应模型 {code, message, data}
common/http_client.py    请求出口：统一鉴权/日志/重试 + trust_env 绕过代理（见下方踩坑）
common/assertions.py     断言封装：业务码/字段递归比对/分页校验，失败输出可读差异
api/case_api.py          接口层：一个模块一个类，路径集中管理
data/case_factory.py     数据工厂：随机生成 + AUTO_ 前缀，并发不污染
tests/conftest.py        fixture：线程内拉起真实服务（随机端口）+ 测后自动清理
tests/test_case_crud.py  CRUD 正反例 + 鉴权 + 边界
tests/test_case_query.py 筛选/分页/幂等导入（parametrize 数据驱动）
.github/workflows/ci.yml push 触发 + 每天凌晨 2 点定时回归
```

## 本地跑起来

```bash
cd casehub
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest          # 13 passed in ~1s
pytest -m smoke # 冒烟子集
```

看报告：`allure serve allure-results`（需安装 allure 命令行）。

## 用例设计的三个亮点（面试重点讲）

1. **幂等导入** `test_import_idempotent`：同一 batchNo 重复提交，第二次必须 successCount=0。
   这是我在支付回调测试里养成的习惯——重复消息只能入账一次。
2. **统一错误模型测试**：HTTP 恒为 200、业务码区分成败（国内后端常见风格）。
   缺 name 返回 40001 而不是 500——`test_create_missing_name_should_fail` 专门验证这一点。
3. **整批失败语义** `test_import_invalid_case_fails_whole_batch`：批量导入混入非法数据时整批失败，
   不能"部分成功"导致状态不明——资金系统的教训。

另有一条 **`test_request_without_token_rejected`**（安全：无 Token 必须 401）。

## 一个真实的踩坑记录（面试聊定位能力时用）

本地调试时出现诡异现象：**每个会话第一条请求 200，之后全部 404，且响应是 `{"detail":"Not Found"}`**。
逐步定位：直连 curl 正常 → 怀疑不是服务问题 → 查 `env` 发现机器配了全局代理 `HTTP_PROXY`，
requests 默认信任环境变量，把发往 127.0.0.1 的请求也转给了代理。
解决：`session.trust_env = False`（默认绕过环境代理，测外部环境时再显式开启）。
**教训：先确认"这个响应到底是谁返回的"，再怀疑被测系统。**

## 简历措辞（跑通后可用）

> 个人项目 CaseHub：使用 FastAPI 实现用例管理服务（CRUD/筛选分页/幂等导入/Token 鉴权），
> 并使用 Python + pytest 完成接口自动化（13 个场景：正反例、边界、异常、幂等、鉴权），
> 分层设计（HTTP 封装/接口层/数据工厂/fixture 清理），接入 GitHub Actions 实现每日定时回归。

## 迁移对照（Java 天眼 → pytest）

| Java 天眼 | 本项目 |
|---|---|
| base test class + Spring 注入 | conftest.py + fixture（scope 控制） |
| @DataProvider 数据驱动 | @pytest.mark.parametrize（带可读 ids） |
| TestNG 断言 + 自定义 assert | 纯函数断言封装（递归字段比对） |
| Maven + Jenkins | requirements.txt + GitHub Actions |
| 手写 teardown 清数据 | yield fixture 自动清理 |
