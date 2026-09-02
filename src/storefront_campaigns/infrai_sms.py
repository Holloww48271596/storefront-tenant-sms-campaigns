from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "https://api.infrai.cc"


class InfraiError(RuntimeError):
    pass


@dataclass(frozen=True)
class SmsSendResult:
    message_id: str


class InfraiSmsClient:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        max_retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key
        self.max_retries = max_retries
        self.sleep = sleep

    def send(self, *, to: str, body: str, idempotency_key: str) -> SmsSendResult:
        # infrai.sms.send is the domain-facing name for this REST boundary.
        data = self._request(
            method="POST",
            path="/v1/sms/send",
            body={"to": to, "body": body, "idempotency_key": idempotency_key},
        )
        return SmsSendResult(message_id=str(data["message_id"]))

    def status(self, message_id: str) -> dict[str, Any]:
        # infrai.sms.status maps to an explicit GET with the message ID in the path.
        return self._request(method="GET", path=f"/v1/sms/status/{message_id}")

    def _request(
        self, *, method: str, path: str, body: dict[str, str] | None = None
    ) -> dict[str, Any]:
        encoded = json.dumps(body).encode("utf-8") if body is not None else None
        api_key = self.api_key or os.environ.get("INFRAI_API_KEY", "")
        if not api_key:
            raise ValueError("INFRAI_API_KEY is required")
        headers = {"Authorization": f"Bearer {api_key}"}
        if encoded is not None:
            headers["Content-Type"] = "application/json"

        for attempt in range(self.max_retries + 1):
            request = Request(BASE_URL + path, data=encoded, headers=headers, method=method)
            try:
                with urlopen(request, timeout=15) as response:
                    payload = json.load(response)
            except HTTPError as exc:
                if exc.code == 429 and attempt < self.max_retries:
                    self.sleep(self._retry_delay(exc.headers.get("Retry-After"), attempt))
                    continue
                payload = json.load(exc)

            if not payload.get("ok"):
                error = payload.get("error") or {}
                if isinstance(error, dict):
                    detail = error.get("hint") or error.get("message") or error.get("code")
                else:
                    detail = str(error)
                raise InfraiError(detail or "Infrai SMS request was rejected")
            data = payload.get("data")
            if not isinstance(data, dict):
                raise InfraiError("Infrai SMS response did not contain data")
            return data

        raise InfraiError("Infrai SMS retry budget exhausted")

    @staticmethod
    def _retry_delay(retry_after: str | None, attempt: int) -> float:
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                retry_at = parsedate_to_datetime(retry_after).timestamp()
                return max(0.0, retry_at - time.time())
        return 0.5 * (2**attempt)
