import json
from typing import Dict, Any, List, Tuple


class ResponseDiffer:
    """
    Performs real-time structural and semantic response diffing between
    production and sandbox responses to detect regression risks.
    """

    @staticmethod
    def diff_responses(
        prod_response: Dict[str, Any],
        sandbox_response: Dict[str, Any],
        ignore_headers: List[str] = None
    ) -> Dict[str, Any]:
        """
        Compares production and sandbox response metadata and payloads.
        Returns a detailed diff report.
        """
        ignore_headers = [h.lower() for h in (ignore_headers or ["date", "server", "content-length", "x-request-id"])]
        
        prod_status = prod_response.get("status_code", 200)
        sandbox_status = sandbox_response.get("status_code", 200)
        status_matched = prod_status == sandbox_status

        prod_headers = {k.lower(): v for k, v in prod_response.get("headers", {}).items() if k.lower() not in ignore_headers}
        sandbox_headers = {k.lower(): v for k, v in sandbox_response.get("headers", {}).items() if k.lower() not in ignore_headers}
        
        header_diffs = ResponseDiffer._dict_diff(prod_headers, sandbox_headers)

        prod_body = ResponseDiffer._parse_body(prod_response.get("body", ""))
        sandbox_body = ResponseDiffer._parse_body(sandbox_response.get("body", ""))

        body_diffs = ResponseDiffer._compare_structures(prod_body, sandbox_body)

        has_regression = not status_matched or len(body_diffs) > 0

        return {
            "status_matched": status_matched,
            "production_status": prod_status,
            "sandbox_status": sandbox_status,
            "header_diffs": header_diffs,
            "body_diffs": body_diffs,
            "has_regression": has_regression
        }

    @staticmethod
    def _parse_body(raw_body: Any) -> Any:
        if isinstance(raw_body, (dict, list)):
            return raw_body
        if isinstance(raw_body, str) and raw_body.strip():
            try:
                return json.loads(raw_body)
            except json.JSONDecodeError:
                return raw_body
        return raw_body

    @staticmethod
    def _dict_diff(d1: Dict[str, Any], d2: Dict[str, Any]) -> List[Dict[str, Any]]:
        diffs = []
        all_keys = set(d1.keys()).union(set(d2.keys()))
        for k in all_keys:
            v1 = d1.get(k)
            v2 = d2.get(k)
            if v1 != v2:
                diffs.append({"key": k, "production": v1, "sandbox": v2})
        return diffs

    @staticmethod
    def _compare_structures(v1: Any, v2: Any, path: str = "$") -> List[Dict[str, Any]]:
        diffs = []
        if type(v1) != type(v2):
            # If both are numeric or string representations that could match, handle leniently, else flag diff
            if not (isinstance(v1, (int, float)) and isinstance(v2, (int, float))):
                return [{"path": path, "type_production": type(v1).__name__, "type_sandbox": type(v2).__name__, "production": v1, "sandbox": v2}]

        if isinstance(v1, dict):
            keys1 = set(v1.keys())
            keys2 = set(v2.keys())
            for k in keys1 - keys2:
                diffs.append({"path": f"{path}.{k}", "issue": "missing_in_sandbox", "production_value": v1[k]})
            for k in keys2 - keys1:
                diffs.append({"path": f"{path}.{k}", "issue": "extra_in_sandbox", "sandbox_value": v2[k]})
            for k in keys1.intersection(keys2):
                diffs.extend(ResponseDiffer._compare_structures(v1[k], v2[k], f"{path}.{k}"))

        elif isinstance(v1, list):
            if len(v1) != len(v2):
                diffs.append({"path": path, "issue": "list_length_mismatch", "production_length": len(v1), "sandbox_length": len(v2)})
            for i in range(min(len(v1), len(v2))):
                diffs.extend(ResponseDiffer._compare_structures(v1[i], v2[i], f"{path}[{i}]"))

        elif v1 != v2:
            diffs.append({"path": path, "issue": "value_mismatch", "production": v1, "sandbox": v2})

        return diffs
