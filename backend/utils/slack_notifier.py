#!/usr/bin/env python3
"""
Slack notifier utility (single destination via webhook).

Design goal:
- ALL notifications go to the same Slack destination (channel or DM) configured
  on the incoming webhook itself.
- No per-message channel overrides.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

_LAST_SENT: dict[str, float] = {}


@dataclass(frozen=True)
class SlackMessage:
    title: str
    message: str
    severity: str = "INFO"  # INFO, WARNING, CRITICAL, SUCCESS
    fields: dict[str, str] | None = None
    blocks: list[dict[str, Any]] | None = None


def _enabled() -> bool:
    return os.getenv("TTL_SLACK_NOTIFICATIONS", "false").lower() == "true"


def _webhook_url() -> str | None:
    return os.getenv("TTL_SLACK_WEBHOOK_URL")


def _emoji(severity: str) -> str:
    return {
        "INFO": "ℹ️",
        "WARNING": "⚠️",
        "CRITICAL": "🚨",
        "SUCCESS": "✅",
        "EXPIRED": "❌",
    }.get(severity.upper(), "🔔")


def send_slack(msg: SlackMessage, throttle_key: str | None = None, min_interval_seconds: int = 0) -> None:
    """
    Send a Slack notification via incoming webhook.

    throttle_key + min_interval_seconds:
      - prevents spamming the same alert repeatedly
      - in-memory only (resets on process restart)
    """
    try:
        if not _enabled():
            return

        webhook_url = _webhook_url()
        if not webhook_url:
            logger.debug("TTL_SLACK_WEBHOOK_URL not configured")
            return

        if throttle_key and min_interval_seconds > 0:
            now = time.time()
            last = _LAST_SENT.get(throttle_key, 0.0)
            if (now - last) < min_interval_seconds:
                return
            _LAST_SENT[throttle_key] = now

        import requests

        # If caller provides blocks, send them as-is (still single destination).
        if msg.blocks:
            payload: dict[str, Any] = {"blocks": msg.blocks, "text": f"{msg.title}: {msg.message}"}
        else:
            fields = msg.fields or {}
            blocks: list[dict[str, Any]] = [
                {"type": "header", "text": {"type": "plain_text", "text": f"{_emoji(msg.severity)} {msg.title}"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": msg.message}},
            ]
            if fields:
                blocks.append(
                    {
                        "type": "section",
                        "fields": [{"type": "mrkdwn", "text": f"*{k}*\n{v}"} for k, v in fields.items()],
                    }
                )
            payload = {"blocks": blocks, "text": f"{msg.title}: {msg.message}"}

        # IMPORTANT: Do NOT set "channel" here. The webhook defines destination.
        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        logger.debug(f"Slack send failed (non-fatal): {e}")

