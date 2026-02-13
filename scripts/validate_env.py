#!/usr/bin/env python3
"""
Validate backend environment variables for Railway (or production) deployment.

Checks:
  - Required: REDIS_URL, ALLOWED_ORIGINS, ENVIRONMENT (optional but recommended)
  - REDIS_URL format: redis:// or rediss://
  - ALLOWED_ORIGINS format: https:// or http://, no trailing slash, no spaces
  - Optional: ALPHA_VANTAGE_API_KEY

Usage:
  cd /path/to/project
  export REDIS_URL=redis://localhost:6379 ALLOWED_ORIGINS=http://localhost:8080
  python scripts/validate_env.py

  # From backend directory with .env:
  cd backend && python -c "import dotenv; dotenv.load_dotenv()" && python ../scripts/validate_env.py

Exit: 0 if all required checks pass, 1 otherwise.
"""

import os
import re
import sys

try:
    from colorama import init as colorama_init, Fore, Style
    colorama_init(autoreset=True)
except ImportError:
    Fore = type("Fore", (), {"GREEN": "", "RED": "", "YELLOW": "", "CYAN": ""})()
    Style = type("Style", (), {"RESET_ALL": ""})()


def _red(s: str) -> str:
    return f"{Fore.RED}{s}{Style.RESET_ALL}"


def _green(s: str) -> str:
    return f"{Fore.GREEN}{s}{Style.RESET_ALL}"


def _yellow(s: str) -> str:
    return f"{Fore.YELLOW}{s}{Style.RESET_ALL}"


def _cyan(s: str) -> str:
    return f"{Fore.CYAN}{s}{Style.RESET_ALL}"


def check_redis_url(value: str) -> tuple[bool, str]:
    if not value or not value.strip():
        return False, "REDIS_URL is empty"
    v = value.strip()
    if not (v.startswith("redis://") or v.startswith("rediss://")):
        return False, "REDIS_URL must start with redis:// or rediss://"
    if " " in v:
        return False, "REDIS_URL must not contain spaces"
    return True, "OK"


def check_allowed_origins(value: str) -> tuple[bool, str]:
    if not value or not value.strip():
        return False, "ALLOWED_ORIGINS is empty"
    parts = [p.strip() for p in value.split(",") if p.strip()]
    if not parts:
        return False, "ALLOWED_ORIGINS has no valid origins"
    for origin in parts:
        if " " in origin:
            return False, f"Origin contains space: {origin!r}"
        if origin.endswith("/"):
            return False, f"Origin must not end with slash: {origin!r}"
        if not (origin.startswith("http://") or origin.startswith("https://")):
            return False, f"Origin must start with http:// or https://: {origin!r}"
    return True, "OK"


def main() -> int:
    print(_cyan("Portfolio Navigator Wizard – Environment validation"))
    print(_cyan("=" * 60))

    required = {
        "REDIS_URL": ("Redis connection URL (redis:// or rediss://)", check_redis_url),
        "ALLOWED_ORIGINS": ("Comma-separated CORS origins (no trailing slash)", check_allowed_origins),
    }
    optional = {
        "ENVIRONMENT": "development | staging | production",
        "ALPHA_VANTAGE_API_KEY": "Alpha Vantage API key",
        "PORT": "Set by Railway; do not override",
    }

    failed = []
    for name, (desc, validator) in required.items():
        value = os.getenv(name)
        if value is None:
            value = ""
        ok, msg = validator(value)
        if ok:
            print(_green(f"  [OK]   {name}: set"))
        else:
            print(_red(f"  [FAIL] {name}: {msg}"))
            failed.append(name)

    # ENVIRONMENT: optional but recommend production on Railway
    env_val = os.getenv("ENVIRONMENT", "").strip()
    if not env_val:
        print(_yellow("  [WARN] ENVIRONMENT not set (recommend production on Railway)"))
    else:
        print(_green(f"  [OK]   ENVIRONMENT: {env_val}"))

    print(_cyan("Optional variables:"))
    for name, desc in optional.items():
        val = os.getenv(name)
        if val:
            print(_green(f"  [SET]  {name}"))
        else:
            print(_yellow(f"  [---]  {name}: {desc}"))

    print(_cyan("=" * 60))
    if failed:
        print(_red("Result: FAILED – fix required variables and re-run."))
        return 1
    print(_green("Result: All required variables valid."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
