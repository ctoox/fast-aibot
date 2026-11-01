from __future__ import annotations

import base64
import json
import os
from typing import Any
from urllib.parse import quote, urljoin

import aiohttp

from .models import (
    GetConfigResponse,
    GetUpdatesResponse,
    QrCodeResponse,
    QrStatusResponse,
    SendMessageMessage,
    SendTypingRequest,
)
from .config import get_settings

DEFAULT_BASE_URL = "https://ilinkai.weixin.qq.com"
CHANNEL_VERSION = "1.0.0"


class ApiError(Exception):
    def __init__(self, message: str, *, status: int, code: int | None = None, payload: Any = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.payload = payload

    @property
    def is_session_expired(self) -> bool:
        return self.code == -14


def random_wechat_uin() -> str:
    value = int.from_bytes(os.urandom(4), "big")
    return base64.b64encode(str(value).encode("utf-8")).decode("ascii")


def build_headers(token: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "AuthorizationType": "ilink_bot_token",
        "Authorization": f"Bearer {token}",
        "X-WECHAT-UIN": random_wechat_uin(),
    }


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


async def _parse_json_response(response: aiohttp.ClientResponse, label: str) -> dict[str, Any]:
    text = await response.text()
    payload = json.loads(text) if text else {}

    if response.status < 200 or response.status >= 300:
        message = payload.get("errmsg") or f"{label} failed with HTTP {response.status}"
        raise ApiError(message, status=response.status, code=payload.get("errcode"), payload=payload)

    if isinstance(payload.get("ret"), int) and payload["ret"] != 0:
        raise ApiError(
            payload.get("errmsg") or f"{label} failed",
            status=response.status,
            code=payload.get("errcode", payload["ret"]),
            payload=payload,
        )

    return payload


async def _api_fetch(
    base_url: str,
    endpoint: str,
    body: object,
    token: str,
    timeout_ms: int = 40_000,
) -> dict[str, Any]:
    url = urljoin(f"{_normalize_base_url(base_url)}/", endpoint.lstrip("/"))

    timeout = aiohttp.ClientTimeout(total=timeout_ms / 1000)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, headers=build_headers(token), json=body) as response:
            return await _parse_json_response(response, endpoint)


async def _api_get(base_url: str, path: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    url = urljoin(f"{_normalize_base_url(base_url)}/", path.lstrip("/"))

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers or {}) as response:
            return await _parse_json_response(response, path)


async def get_updates(base_url: str, token: str, buf: str) -> GetUpdatesResponse:
    body = {
        "get_updates_buf": buf,
        "base_info": {"channel_version": CHANNEL_VERSION},
    }
    payload = await _api_fetch(base_url, "/ilink/bot/getupdates", body, token, 40_000)
    return GetUpdatesResponse(**payload)


async def send_message(base_url: str, token: str, msg: SendMessageMessage) -> dict[str, Any]:
    payload = await _api_fetch(
        base_url,
        "/ilink/bot/sendmessage",
        {"msg": msg.model_dump(exclude_none=True), "base_info": {"channel_version": CHANNEL_VERSION}},
        token,
        15_000,
    )
    return payload


async def get_config(base_url: str, token: str, user_id: str, context_token: str) -> GetConfigResponse:
    payload = await _api_fetch(
        base_url,
        "/ilink/bot/getconfig",
        {
            "ilink_user_id": user_id,
            "context_token": context_token,
            "base_info": {"channel_version": CHANNEL_VERSION},
        },
        token,
        15_000,
    )
    return GetConfigResponse(**payload)


async def send_typing(
    base_url: str,
    token: str,
    user_id: str,
    ticket: str,
    status: int,
) -> dict[str, Any]:
    body = {
        "ilink_user_id": user_id,
        "typing_ticket": ticket,
        "status": status,
        "base_info": {"channel_version": CHANNEL_VERSION},
    }
    payload = await _api_fetch(base_url, "/ilink/bot/sendtyping", body, token, 15_000)
    return payload


async def fetch_qr_code(base_url: str = DEFAULT_BASE_URL) -> QrCodeResponse:
    payload = await _api_get(base_url, "/ilink/bot/get_bot_qrcode?bot_type=3")
    return QrCodeResponse(**payload)


async def poll_qr_status(base_url: str, qrcode: str) -> QrStatusResponse:
    payload = await _api_get(
        base_url,
        f"/ilink/bot/get_qrcode_status?qrcode={quote(qrcode, safe='')}",
        {"iLink-App-ClientVersion": "1"},
    )
    return QrStatusResponse(**payload)


def build_text_message(user_id: str, context_token: str, text: str) -> SendMessageMessage:
    from .models import MessageItem, MessageItemType, TextItem

    return SendMessageMessage(
        to_user_id=user_id,
        context_token=context_token,
        item_list=[
            MessageItem(
                type=MessageItemType.TEXT,
                text_item=TextItem(text=text),
            )
        ],
    )


__all__ = [
    "ApiError",
    "build_text_message",
    "fetch_qr_code",
    "get_config",
    "get_updates",
    "poll_qr_status",
    "random_wechat_uin",
    "send_message",
    "send_typing",
]
