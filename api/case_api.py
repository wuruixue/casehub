"""CaseHub 用例管理接口层：路径集中管理"""


class CaseApi:
    def __init__(self, http):
        self.http = http

    def list_cases(self, page=1, size=10, name=None, creator=None, exec_result=None):
        params = {"page": page, "pageSize": size}
        if name:
            params["name"] = name
        if creator:
            params["creator"] = creator
        if exec_result is not None:
            params["execResult"] = exec_result
        return self.http.get("/api/cases", params=params)

    def get_case(self, case_uuid):
        return self.http.get(f"/api/cases/{case_uuid}")

    def create_case(self, payload: dict):
        return self.http.post("/api/cases", json=payload)

    def update_case(self, case_uuid, payload: dict):
        return self.http.put(f"/api/cases/{case_uuid}", json=payload)

    def delete_cases(self, uuids: list):
        return self.http.delete("/api/cases/batch", json={"uuids": uuids})

    def import_cases(self, payload: dict):
        return self.http.post("/api/cases/import", json=payload)
