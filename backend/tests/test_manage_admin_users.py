"""Tests for the ``AdminUserCliService`` and ``manage_admin_users`` CLI helpers."""

import secrets
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import scripts.manage_admin_users as cli_module
from scripts.manage_admin_users import _email_to_env_var, _parse_args, main
from src.app.models.notification import Notification
from src.app.models.user import RoleEnum, User
from src.app.services.admin_user_cli_service import (
    AdminPasswordRequiredError,
    AdminUserCliService,
)
from src.app.utils.auth import hash_password, verify_password


@pytest.fixture
def generated_password_resolver():
    """Resolver that always returns a freshly generated password."""

    def resolver(email: str) -> str:  # noqa: ARG001
        return secrets.token_urlsafe(16)

    return resolver


@pytest.fixture
async def admin_user(test_session: AsyncSession):
    user = User(
        email="admin-to-remove@example.com",
        hashed_password=hash_password("old-password"),
        role=RoleEnum.admin,
        is_active=True,
        email_verified=True,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest.fixture
async def regular_user(test_session: AsyncSession):
    user = User(
        email="regular@example.com",
        hashed_password=hash_password("user-password"),
        role=RoleEnum.user,
        is_active=True,
        email_verified=False,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


async def test_create_new_admin_with_generated_password(
    test_session: AsyncSession, generated_password_resolver
):
    email = "NEW_ADMIN@example.com"

    results = await AdminUserCliService.ensure_admins(
        [email], db=test_session, password_resolver=generated_password_resolver
    )
    await test_session.commit()

    assert len(results) == 1
    result = results[0]
    assert result.email == email.lower()
    assert result.created is True
    assert result.password is not None
    assert result.message == "Created new admin user"

    user = await _get_user_by_email(test_session, email)
    assert user is not None
    assert user.role == RoleEnum.admin
    assert user.email_verified is True
    assert verify_password(result.password, user.hashed_password)


async def test_update_existing_user_to_admin(
    test_session: AsyncSession, regular_user: User, generated_password_resolver
):
    results = await AdminUserCliService.ensure_admins(
        [regular_user.email],
        db=test_session,
        password_resolver=generated_password_resolver,
    )
    await test_session.commit()

    assert len(results) == 1
    result = results[0]
    assert result.email == regular_user.email.lower()
    assert result.created is False
    assert result.password is not None
    assert result.message == "Updated existing user to admin"

    user = await _get_user_by_email(test_session, regular_user.email)
    assert user.role == RoleEnum.admin
    assert user.email_verified is True
    assert user.is_active is True
    assert verify_password(result.password, user.hashed_password)


async def test_promoted_inactive_user_becomes_active(
    test_session: AsyncSession, generated_password_resolver
):
    email = "inactive-user@example.com"
    user = User(
        email=email,
        hashed_password=hash_password("user-password"),
        role=RoleEnum.user,
        is_active=False,
        email_verified=False,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)

    results = await AdminUserCliService.ensure_admins(
        [email], db=test_session, password_resolver=generated_password_resolver
    )
    await test_session.commit()

    assert len(results) == 1
    assert results[0].created is False
    assert results[0].password is not None

    refreshed = await _get_user_by_email(test_session, email)
    assert refreshed.role == RoleEnum.admin
    assert refreshed.is_active is True
    assert refreshed.email_verified is True


async def test_existing_admin_left_unchanged(
    test_session: AsyncSession, admin_user: User
):
    original_hash = admin_user.hashed_password

    def resolver(email: str) -> str:  # noqa: ARG001
        raise AssertionError("Resolver must not be called for existing admin")

    results = await AdminUserCliService.ensure_admins(
        [admin_user.email], db=test_session, password_resolver=resolver
    )
    await test_session.commit()

    assert len(results) == 1
    result = results[0]
    assert result.email == admin_user.email.lower()
    assert result.created is False
    assert result.password is None
    assert result.message == "User already has admin role"

    user = await _get_user_by_email(test_session, admin_user.email)
    assert user.role == RoleEnum.admin
    assert user.hashed_password == original_hash


async def test_ensure_admins_uses_provided_password(test_session: AsyncSession):
    email = "newadmin@example.com"
    provided_password = "my-secret-password"

    results = await AdminUserCliService.ensure_admins(
        [email],
        db=test_session,
        password_resolver=lambda e: provided_password,
    )
    await test_session.commit()

    assert len(results) == 1
    assert results[0].password == provided_password

    user = await _get_user_by_email(test_session, email)
    assert verify_password(provided_password, user.hashed_password)


async def test_ensure_admins_raises_when_password_resolver_returns_none(
    test_session: AsyncSession,
):
    email = "newadmin@example.com"

    with pytest.raises(AdminPasswordRequiredError) as exc_info:
        await AdminUserCliService.ensure_admins(
            [email], db=test_session, password_resolver=lambda e: None
        )

    assert exc_info.value.email == email.lower()


async def test_deactivate_admin_user(test_session: AsyncSession, admin_user: User):
    result = await AdminUserCliService.deactivate_admin(
        admin_user.email, db=test_session
    )
    await test_session.commit()

    assert result.email == admin_user.email.lower()
    assert result.deactivated is True
    assert result.message == "Admin user deactivated"

    user = await _get_user_by_email(test_session, admin_user.email)
    assert user is not None
    assert user.role == RoleEnum.user
    assert user.is_active is False


async def test_dry_run_does_not_commit_changes(
    test_session: AsyncSession, generated_password_resolver
):
    email = "dry-run-admin@example.com"

    results = await AdminUserCliService.ensure_admins(
        [email],
        db=test_session,
        password_resolver=generated_password_resolver,
        dry_run=True,
    )

    assert len(results) == 1
    assert results[0].password is not None

    user = await _get_user_by_email(test_session, email)
    assert user is None

    deactivate_result = await AdminUserCliService.deactivate_admin(
        "nonexistent@example.com", db=test_session, dry_run=True
    )
    assert deactivate_result.deactivated is False


async def test_deactivate_admin_keeps_related_rows(
    test_session: AsyncSession, admin_user: User
):
    email = admin_user.email
    notification = Notification(
        user_id=admin_user.id,
        type="test",
        title="Test",
        message="Test notification",
    )
    test_session.add(notification)
    await test_session.commit()

    result = await AdminUserCliService.deactivate_admin(email, db=test_session)
    await test_session.commit()

    assert result.email == email.lower()
    assert result.deactivated is True
    assert result.message == "Admin user deactivated"

    user = await _get_user_by_email(test_session, email)
    assert user is not None
    assert user.role == RoleEnum.user
    assert user.is_active is False


async def _get_user_by_email(session: AsyncSession, email: str) -> User | None:
    from sqlalchemy import func

    result = await session.execute(
        select(User).where(func.lower(User.email) == email.lower())
    )
    return result.scalars().first()


def _cli_session_factory(test_session: AsyncSession):
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=test_session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return factory


def _cli_engine():
    engine = MagicMock()
    engine.dispose = AsyncMock()
    return engine


def test_email_to_env_var_mapping():
    assert _email_to_env_var("elmanov21@yandex.ru") == "ADMIN_PASSWORD_ELMANOV21"
    assert (
        _email_to_env_var("dadeko.aleksandr@yandex.ru")
        == "ADMIN_PASSWORD_DADEKO_ALEKSANDR"
    )


def test_parse_args_add_emails_and_remove_email():
    args = _parse_args(
        [
            "--add",
            "a@example.com",
            "b@example.com",
            "--remove",
            "seed@example.com",
        ]
    )
    assert args.add_emails == ["a@example.com", "b@example.com"]
    assert args.remove_email == "seed@example.com"
    assert args.dry_run is False
    assert args.ci is False


def test_parse_args_dry_run_flag():
    args = _parse_args(["--add", "a@example.com", "--dry-run"])
    assert args.add_emails == ["a@example.com"]
    assert args.remove_email is None
    assert args.dry_run is True
    assert args.ci is False


def test_parse_args_ci_flag():
    args = _parse_args(["--add", "a@example.com", "--ci"])
    assert args.add_emails == ["a@example.com"]
    assert args.ci is True
    assert args.dry_run is False


async def test_main_ensure_admins_and_deactivate_seed_admin(
    test_session: AsyncSession, monkeypatch, capsys
):
    seed_email = "seed-admin@example.com"
    new_email = "new-admin@example.com"

    seed = User(
        email=seed_email,
        hashed_password=hash_password("seed-password"),
        role=RoleEnum.admin,
        is_active=True,
        email_verified=True,
    )
    test_session.add(seed)
    await test_session.commit()

    engine = _cli_engine()
    monkeypatch.setattr(
        cli_module,
        "settings",
        type("Settings", (), {"database_url": "postgresql+asyncpg://test"})(),
    )
    monkeypatch.setattr(cli_module, "create_async_engine", lambda url: engine)
    monkeypatch.setattr(
        cli_module,
        "async_sessionmaker",
        lambda *a, **kw: _cli_session_factory(test_session),
    )

    exit_code = await main(["--add", new_email, "--remove", seed_email])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert new_email in captured.out
    assert seed_email in captured.out
    assert "DEACTIVATED" in captured.out

    new_user = await _get_user_by_email(test_session, new_email)
    assert new_user is not None
    assert new_user.role == RoleEnum.admin

    seed_user = await _get_user_by_email(test_session, seed_email)
    assert seed_user.role == RoleEnum.user
    assert seed_user.is_active is False


async def test_main_dry_run_does_not_change_db(
    test_session: AsyncSession, monkeypatch, capsys
):
    seed_email = "seed-admin@example.com"
    existing_email = "existing@example.com"

    existing = User(
        email=existing_email,
        hashed_password=hash_password("password"),
        role=RoleEnum.user,
        is_active=True,
        email_verified=True,
    )
    seed = User(
        email=seed_email,
        hashed_password=hash_password("seed-password"),
        role=RoleEnum.admin,
        is_active=True,
        email_verified=True,
    )
    test_session.add_all([existing, seed])
    await test_session.commit()

    engine = _cli_engine()
    monkeypatch.setattr(
        cli_module,
        "settings",
        type("Settings", (), {"database_url": "postgresql+asyncpg://test"})(),
    )
    monkeypatch.setattr(cli_module, "create_async_engine", lambda url: engine)
    monkeypatch.setattr(
        cli_module,
        "async_sessionmaker",
        lambda *a, **kw: _cli_session_factory(test_session),
    )

    exit_code = await main(
        ["--add", existing_email, "--remove", seed_email, "--dry-run"]
    )

    assert exit_code == 0

    existing_user = await _get_user_by_email(test_session, existing_email)
    assert existing_user.role == RoleEnum.user

    seed_user = await _get_user_by_email(test_session, seed_email)
    assert seed_user.role == RoleEnum.admin
    assert seed_user.is_active is True


async def test_main_returns_non_zero_when_deactivate_not_admin(
    test_session: AsyncSession, monkeypatch, capsys
):
    email = "regular@example.com"
    user = User(
        email=email,
        hashed_password=hash_password("password"),
        role=RoleEnum.user,
        is_active=True,
        email_verified=True,
    )
    test_session.add(user)
    await test_session.commit()

    engine = _cli_engine()
    monkeypatch.setattr(
        cli_module,
        "settings",
        type("Settings", (), {"database_url": "postgresql+asyncpg://test"})(),
    )
    monkeypatch.setattr(cli_module, "create_async_engine", lambda url: engine)
    monkeypatch.setattr(
        cli_module,
        "async_sessionmaker",
        lambda *a, **kw: _cli_session_factory(test_session),
    )

    exit_code = await main(["--remove", email])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "FAILED" in captured.out


async def test_main_ci_mode_uses_env_password(
    test_session: AsyncSession, monkeypatch, capsys
):
    email = "newadmin@example.com"
    env_var = "ADMIN_PASSWORD_NEWADMIN"
    env_password = "env-provided-secret"

    engine = _cli_engine()
    monkeypatch.setattr(
        cli_module,
        "settings",
        type("Settings", (), {"database_url": "postgresql+asyncpg://test"})(),
    )
    monkeypatch.setattr(cli_module, "create_async_engine", lambda url: engine)
    monkeypatch.setattr(
        cli_module,
        "async_sessionmaker",
        lambda *a, **kw: _cli_session_factory(test_session),
    )
    monkeypatch.setenv(env_var, env_password)

    exit_code = await main(["--add", email, "--ci"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert env_password not in captured.out
    assert "CREATED" in captured.out

    user = await _get_user_by_email(test_session, email)
    assert verify_password(env_password, user.hashed_password)


async def test_main_ci_mode_fails_without_env_password(
    test_session: AsyncSession, monkeypatch, capsys
):
    email = "newadmin@example.com"
    env_var = "ADMIN_PASSWORD_NEWADMIN"

    engine = _cli_engine()
    monkeypatch.setattr(
        cli_module,
        "settings",
        type("Settings", (), {"database_url": "postgresql+asyncpg://test"})(),
    )
    monkeypatch.setattr(cli_module, "create_async_engine", lambda url: engine)
    monkeypatch.setattr(
        cli_module,
        "async_sessionmaker",
        lambda *a, **kw: _cli_session_factory(test_session),
    )
    monkeypatch.delenv(env_var, raising=False)

    exit_code = await main(["--add", email, "--ci"])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert env_var in captured.err


async def test_main_ci_mode_existing_admin_password_unchanged(
    test_session: AsyncSession, monkeypatch, capsys
):
    email = "existing-admin@example.com"
    env_var = "ADMIN_PASSWORD_EXISTING_ADMIN"
    original_hash = hash_password("original-password")

    user = User(
        email=email,
        hashed_password=original_hash,
        role=RoleEnum.admin,
        is_active=True,
        email_verified=True,
    )
    test_session.add(user)
    await test_session.commit()

    engine = _cli_engine()
    monkeypatch.setattr(
        cli_module,
        "settings",
        type("Settings", (), {"database_url": "postgresql+asyncpg://test"})(),
    )
    monkeypatch.setattr(cli_module, "create_async_engine", lambda url: engine)
    monkeypatch.setattr(
        cli_module,
        "async_sessionmaker",
        lambda *a, **kw: _cli_session_factory(test_session),
    )
    monkeypatch.setenv(env_var, "must-not-be-applied")

    exit_code = await main(["--add", email, "--ci"])

    assert exit_code == 0
    refreshed = await _get_user_by_email(test_session, email)
    assert refreshed.hashed_password == original_hash


async def test_main_ci_mode_via_environment_variable(
    test_session: AsyncSession, monkeypatch, capsys
):
    email = "newadmin@example.com"
    env_var = "ADMIN_PASSWORD_NEWADMIN"
    env_password = "env-provided-secret"

    engine = _cli_engine()
    monkeypatch.setattr(
        cli_module,
        "settings",
        type("Settings", (), {"database_url": "postgresql+asyncpg://test"})(),
    )
    monkeypatch.setattr(cli_module, "create_async_engine", lambda url: engine)
    monkeypatch.setattr(
        cli_module,
        "async_sessionmaker",
        lambda *a, **kw: _cli_session_factory(test_session),
    )
    monkeypatch.setenv(env_var, env_password)
    monkeypatch.setenv("CI", "true")

    exit_code = await main(["--add", email])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert env_password not in captured.out

    user = await _get_user_by_email(test_session, email)
    assert verify_password(env_password, user.hashed_password)


async def test_main_interactive_mode_prints_generated_password(
    test_session: AsyncSession, monkeypatch, capsys
):
    email = "newadmin@example.com"

    engine = _cli_engine()
    monkeypatch.setattr(
        cli_module,
        "settings",
        type("Settings", (), {"database_url": "postgresql+asyncpg://test"})(),
    )
    monkeypatch.setattr(cli_module, "create_async_engine", lambda url: engine)
    monkeypatch.setattr(
        cli_module,
        "async_sessionmaker",
        lambda *a, **kw: _cli_session_factory(test_session),
    )
    monkeypatch.delenv("ADMIN_PASSWORD_NEWADMIN", raising=False)
    monkeypatch.delenv("CI", raising=False)

    exit_code = await main(["--add", email])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Generated password:" in captured.out

    user = await _get_user_by_email(test_session, email)
    assert user is not None
    assert user.role == RoleEnum.admin
