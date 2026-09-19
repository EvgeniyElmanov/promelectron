import os
import subprocess
import sys
from pathlib import Path


def test_users_router_imports_in_production():
    """Регрессия: endpoint'ы users импортируются в production без slowapi-ошибки.

    Декоратор ``@conditional_limit`` в production оборачивает функцию в
    ``slowapi.limiter.limit(...)``, который требует аргумент ``request`` или
    ``websocket``.  В ``register_user`` / ``login_user`` этот аргумент должен
    присутствовать, иначе импорт модуля падает на этапе загрузки приложения.
    """
    backend_dir = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["ENVIRONMENT"] = "production"
    env.pop("CI", None)
    env["SECRET_KEY"] = "a" * 64  # достаточно длинный ключ для production-валидации
    env["ONEC_WEBHOOK_API_KEY"] = "b" * 32  # production fail-fast требует не-placeholder
    env["YOOKASSA_WEBHOOK_SECRET"] = "c" * 32  # production fail-fast (#210)
    env["FRONTEND_URL"] = "https://example.com"

    result = subprocess.run(
        [sys.executable, "-c", "from src.app.api.users import router; print('import ok')"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "import ok" in result.stdout


def test_production_limiter_storage_options_types():
    """Регрессия: ``socket_connect_timeout`` должен быть числом, а не строкой.

    redis-py передаёт значение в ``sock.settimeout()`` — строка вызывает
    ``TypeError`` на каждом hit лимитера, превращая все лимитированные
    endpoint'ы в 500 (падение E2E на test-окружении после PR #68).
    """
    backend_dir = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["ENVIRONMENT"] = "production"
    env.pop("CI", None)
    env["SECRET_KEY"] = "a" * 64
    env["ONEC_WEBHOOK_API_KEY"] = "b" * 32
    env["YOOKASSA_WEBHOOK_SECRET"] = "c" * 32  # production fail-fast (#210)
    env["FRONTEND_URL"] = "https://example.com"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from src.app.utils.rate_limiter import limiter; "
            "timeout = limiter._storage_options['socket_connect_timeout']; "
            "assert isinstance(timeout, (int, float)), type(timeout); "
            "print('timeout ok')",
        ],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "timeout ok" in result.stdout
