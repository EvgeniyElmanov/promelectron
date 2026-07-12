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
