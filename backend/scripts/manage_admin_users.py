#!/usr/bin/env python3
"""Management CLI for creating and deactivating admin users.

Run from the repository root or the ``backend/`` directory, for example:

    python scripts/manage_admin_users.py \\
        --add elmanov21@yandex.ru dadeko.aleksandr@yandex.ru \\
        --remove seed-admin@example.com

The ``--remove`` flag deactivates the admin (sets role=user, is_active=False)
instead of hard-deleting, following the project soft-delete convention.

Use ``--dry-run`` to preview changes without committing them.
Use ``--ci`` (or set ``CI=true``) for non-interactive CI/CD execution. In CI
mode passwords are read from environment variables and never printed.
"""

import argparse
import asyncio
import os
import secrets
import sys
from collections.abc import Callable

# Ensure project root is on path when the script is invoked directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.app.core.config import settings
from src.app.services.admin_user_cli_service import (
    AdminPasswordRequiredError,
    AdminUserCliService,
)


def _email_to_env_var(email: str) -> str:
    """Map an email local-part to the admin password env var name.

    Example:
        elmanov21@yandex.ru        -> ADMIN_PASSWORD_ELMANOV21
        dadeko.aleksandr@yandex.ru -> ADMIN_PASSWORD_DADEKO_ALEKSANDR
    """
    local_part = email.split("@", 1)[0]
    normalized = local_part.upper().replace(".", "_").replace("@", "_")
    return f"ADMIN_PASSWORD_{normalized}"


def _build_password_resolver(ci_mode: bool) -> Callable[[str], str | None]:
    """Return a resolver that reads env vars in CI or generates interactively.

    In CI mode a missing env var yields ``None`` so the service can raise an
    error. In interactive mode a missing env var triggers a generated password
    that is returned to the caller for printing.
    """

    def resolver(email: str) -> str | None:
        env_var = _email_to_env_var(email)
        password = os.environ.get(env_var)
        if password:
            return password
        if ci_mode:
            return None
        return secrets.token_urlsafe(16)

    return resolver


def _format_results(ensure_results, deactivate_result, *, ci_mode: bool = False):
    lines = []
    lines.append("=" * 60)
    lines.append("Admin user management results")
    lines.append("=" * 60)

    if ensure_results:
        lines.append("\nEnsured admins:")
        for res in ensure_results:
            if res.created:
                status = "CREATED"
            elif res.password is None:
                status = "UNCHANGED"
            else:
                status = "UPDATED"
            lines.append(f"  {res.email:<40} {status:<20} {res.message}")
            if res.password and not ci_mode:
                lines.append(f"    Generated password: {res.password}")

    if deactivate_result is not None:
        lines.append("\nDeactivated admin:")
        status = "DEACTIVATED" if deactivate_result.deactivated else "FAILED"
        lines.append(
            f"  {deactivate_result.email:<40} {status:<20} {deactivate_result.message}"
        )

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Create or deactivate admin users directly in the database."
    )
    parser.add_argument(
        "--add",
        dest="add_emails",
        nargs="+",
        help="One or more emails to ensure have the admin role.",
    )
    parser.add_argument(
        "--remove",
        dest="remove_email",
        help="Email of the admin user to deactivate (role=user, is_active=False).",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Show planned changes without writing to the database.",
    )
    parser.add_argument(
        "--ci",
        dest="ci",
        action="store_true",
        help=(
            "Non-interactive CI mode: read passwords from env vars, "
            "do not print passwords, exit non-zero on any error."
        ),
    )
    return parser.parse_args(argv)


def _is_ci_mode(args) -> bool:
    """Return True when CI mode is requested via flag or the CI env var."""
    if args.ci:
        return True
    return os.environ.get("CI", "").lower() in ("true", "1", "yes")


async def main(argv=None):
    args = _parse_args(argv)
    ci_mode = _is_ci_mode(args)

    if not args.add_emails and not args.remove_email:
        print("Nothing to do. Use --add and/or --remove.", file=sys.stderr)
        return 0

    password_resolver = _build_password_resolver(ci_mode)

    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    ensure_results = []
    deactivate_result = None
    error_message = None

    try:
        async with session_factory() as db:
            # Deactivate the seed admin first so an FK error during deactivation
            # does not roll back the newly ensured admins (F001).
            if args.remove_email:
                deactivate_result = await AdminUserCliService.deactivate_admin(
                    email=args.remove_email,
                    db=db,
                    dry_run=args.dry_run,
                )
            if args.add_emails:
                ensure_results = await AdminUserCliService.ensure_admins(
                    emails=args.add_emails,
                    db=db,
                    password_resolver=password_resolver,
                    dry_run=args.dry_run,
                )

            if args.dry_run:
                await db.rollback()
            else:
                await db.commit()
    except AdminPasswordRequiredError as exc:
        env_var = _email_to_env_var(exc.email)
        error_message = (
            f"Error: password for {exc.email} is required in CI mode, "
            f"but environment variable {env_var} is not set."
        )
    except Exception as exc:  # noqa: BLE001 - CLI entry point catches all errors
        error_message = f"Error: {exc}"
    finally:
        await engine.dispose()

    if error_message:
        print(error_message, file=sys.stderr)
        return 1

    print(_format_results(ensure_results, deactivate_result, ci_mode=ci_mode))

    has_error = (
        deactivate_result is not None
        and not deactivate_result.deactivated
        and deactivate_result.message != "User not found"
    )
    return 1 if has_error else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
