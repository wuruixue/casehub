"""
CaseHub 用例管理服务（FastAPI）
一个自包含的"被测系统"：CRUD + 筛选分页 + 幂等导入 + Token 鉴权
约定：HTTP 恒为 200，业务结果看 code（0=成功），这是国内后端常见风格，也是测试要点
"""
import threading
import time
import uuid as uuidlib

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

API_TOKEN = "demo-token"

app = FastAPI(title="CaseHub", version="1.0")

# 简单内存存储（demo 用，进程内一致性好；生产应换 SQLite/MySQL，简历里可以讲这个取舍）
CASES: dict = {}          # uuid -> case dict，dict 保序，分页天然稳定
IMPORT_BATCHES: set = set()   # 已处理批次号，导入幂等的依据
_lock = threading.Lock()


# ---------- 统一响应 ----------
def ok(data=None):
    return JSONResponse({"code": 0, "message": "ok", "data": data})


def biz_err(code: int, message: str):
    return JSONResponse({"code": code, "message": message, "data": None})


@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    """参数校验失败也返回 HTTP 200 + 业务码 40001，统一错误模型"""
    msg = exc.errors()[0].get("msg", "invalid") if exc.errors() else "invalid"
    return biz_err(40001, f"参数校验失败: {msg}")


# ---------- 鉴权 ----------
def check_token(x_api_token: str = Header(default="")):
    if x_api_token != API_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")


# ---------- 模型 ----------
class Step(BaseModel):
    index: int
    action: str
    expectStatus: int = 200


class CaseIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    creator: str = "anonymous"
    execResult: int = 0          # 0-未执行 1-通过 2-失败
    steps: list[Step] = []


class BatchDelete(BaseModel):
    uuids: list[str]


class ImportIn(BaseModel):
    batchNo: str = Field(min_length=1)
    cases: list[CaseIn]


# ---------- 接口 ----------
@app.get("/health")
def health():
    return ok({"status": "up"})


@app.post("/api/cases", dependencies=[Depends(check_token)])
def create_case(case: CaseIn):
    with _lock:
        u = str(uuidlib.uuid4())
        now = int(time.time())
        CASES[u] = {**case.model_dump(), "uuid": u, "createdTime": now, "updatedTime": now}
    return ok({"uuid": u})


@app.get("/api/cases", dependencies=[Depends(check_token)])
def list_cases(page: int = 1, pageSize: int = 10, name: str = "",
               creator: str = "", execResult: int = None):
    if page < 1 or pageSize < 1:
        return biz_err(40002, "page/pageSize 必须 >= 1")
    items = list(CASES.values())
    if name:
        items = [c for c in items if name in c["name"]]
    if creator:
        items = [c for c in items if c["creator"] == creator]
    if execResult is not None:
        items = [c for c in items if c["execResult"] == execResult]
    start = (page - 1) * pageSize
    return ok({"records": items[start:start + pageSize], "total": len(items),
               "page": page, "pageSize": pageSize})


@app.get("/api/cases/{case_uuid}", dependencies=[Depends(check_token)])
def get_case(case_uuid: str):
    return ok(CASES.get(case_uuid))     # 不存在时 data 为 null


@app.put("/api/cases/{case_uuid}", dependencies=[Depends(check_token)])
def update_case(case_uuid: str, case: CaseIn):
    if case_uuid not in CASES:
        return biz_err(40400, "用例不存在")
    with _lock:
        CASES[case_uuid].update({**case.model_dump(), "updatedTime": int(time.time())})
    return ok({"uuid": case_uuid})


@app.delete("/api/cases/batch", dependencies=[Depends(check_token)])
def delete_cases(payload: BatchDelete):
    with _lock:
        deleted = [u for u in payload.uuids if CASES.pop(u, None) is not None]
    return ok({"deleted": deleted})


@app.post("/api/cases/import", dependencies=[Depends(check_token)])
def import_cases(payload: ImportIn):
    """幂等导入：同一 batchNo 只处理一次，重复提交 successCount=0"""
    with _lock:
        if payload.batchNo in IMPORT_BATCHES:
            return ok({"successCount": 0, "duplicate": True})
        for c in payload.cases:
            u = str(uuidlib.uuid4())
            CASES[u] = {**c.model_dump(), "uuid": u,
                        "createdTime": int(time.time()), "updatedTime": int(time.time())}
        IMPORT_BATCHES.add(payload.batchNo)
    return ok({"successCount": len(payload.cases), "duplicate": False})
