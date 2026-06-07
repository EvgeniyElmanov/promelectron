#!/usr/bin/env python3
"""
Диагностика YooKassa: сравниваем прямой SDK-вызов с backend-логикой.

Запуск:
    cd backend && python scripts/diagnose_yookassa.py

Требует YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY из окружения.
"""

import asyncio
import json
import os
import sys
from decimal import Decimal

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app.core.config import settings
from src.app.services.yookassa_service import YooKassaService


async def main():
    print("=" * 60)
    print("YooKassa Diagnosis Script")
    print("=" * 60)

    # Config check
    print("\n[1] Configuration")
    print(f"  YOOKASSA_SHOP_ID: {settings.yookassa_shop_id or 'NOT SET'}")
    print(f"  YOOKASSA_SECRET_KEY: {'SET' if settings.yookassa_secret_key else 'NOT SET'}")
    print(f"  YOOKASSA_TEST_MODE: {settings.yookassa_test_mode}")
    print(f"  YOOKASSA_CAPTURE_AUTO: {settings.yookassa_capture_auto}")
    print(f"  FRONTEND_URL: {settings.frontend_url}")

    if not settings.yookassa_shop_id or not settings.yookassa_secret_key:
        print("\n[ERROR] YooKassa credentials not configured. Set env vars and retry.")
        sys.exit(1)

    # Direct SDK call
    print("\n[2] Direct SDK call: YooKassaService.create_payment")
    try:
        result = await YooKassaService.create_payment(
            order_id=999999,
            amount=Decimal("10.00"),
            description="Diagnosis payment",
            user_id=1,
        )
        print(f"  status: {result['status']}")
        print(f"  yookassa_payment_id: {result['yookassa_payment_id']}")
        print(f"  confirmation_url: {result['confirmation_url']}")
        print(f"  test: {result.get('test')}")

        # Check if confirmation_url looks valid
        if result.get("confirmation_url"):
            if "yoomoney.ru" in result["confirmation_url"] or "yookassa.ru" in result["confirmation_url"]:
                print("  [OK] confirmation_url looks like YooKassa domain")
            else:
                print("  [WARN] confirmation_url does not look like YooKassa domain")
        else:
            print("  [WARN] No confirmation_url returned!")

        # Fetch payment status
        print("\n[3] Direct SDK call: YooKassaService.get_payment")
        get_result = await YooKassaService.get_payment(result["yookassa_payment_id"])
        print(f"  status: {get_result['status']}")
        print(f"  paid: {get_result['paid']}")

    except Exception as exc:
        print(f"  [ERROR] {type(exc).__name__}: {exc}")
        sys.exit(1)

    print("\n[4] Recommendations")
    print("  - If direct SDK works but frontend shows 'Не сработало', check:")
    print("    a) Is the server IP whitelisted by YooKassa? (non-RU IPs may be blocked)")
    print("    b) Is capture=True correct for this merchant type? (try YOOKASSA_CAPTURE_AUTO=false)")
    print("    c) Is return_url reachable from YooKassa servers? (localhost is usually OK for test)")
    print("    d) Are you using the test card 5555 5555 5555 4444? Real cards fail in test shop.")
    print("  - Check backend logs for full request/response (DEBUG level)")

    print("\n" + "=" * 60)
    print("Diagnosis complete.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
