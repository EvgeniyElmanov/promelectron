"""CLI-only service for managing admin users outside HTTP handlers."""

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.user import RoleEnum, User
from src.app.utils.auth import hash_password


class AdminPasswordRequiredError(Exception):
    """Raised when a password is required for an admin operation but not provided."""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"Password required for {email} but not provided")


@dataclass(frozen=True)
class AdminEnsureResult:
    email: str
    created: bool
    password: str | None = None
    message: str = ""


@dataclass(frozen=True)
class AdminDeactivateResult:
    email: str
    deactivated: bool
    message: str = ""


class AdminUserCliService:
    """Low-level operations for the ``manage_admin_users.py`` CLI script.

    This service is intentionally separate from ``UserService`` because it
    performs privileged actions (role escalation, deactivation) that must never
    be reachable through self-registration HTTP endpoints.
    """

    @staticmethod
    async def ensure_admins(
        emails: list[str],
        db: AsyncSession,
        password_resolver: Callable[[str], str | None],
        dry_run: bool = False,
    ) -> list[AdminEnsureResult]:
        """Ensure each email has the ``admin`` role, creating users if needed.

        ``password_resolver`` is called for every user that needs a password
        (newly created users and existing non-admin users that are promoted).
        Already existing admins are left untouched and the resolver is not
        invoked for them.

        If the resolver returns ``None`` for a user that needs a password, an
        ``AdminPasswordRequiredError`` is raised. The CLI translates this into
        a CI failure or an interactive password generation.
        """
        results: list[AdminEnsureResult] = []

        for raw_email in emails:
            email = raw_email.lower()
            result = await db.execute(
                select(User).where(func.lower(User.email) == email)
            )
            user = result.scalars().first()

            if user is not None and user.role == RoleEnum.admin:
                results.append(
                    AdminEnsureResult(
                        email=email,
                        created=False,
                        message="User already has admin role",
                    )
                )
                continue

            password = password_resolver(email)
            if password is None:
                raise AdminPasswordRequiredError(email)

            hashed_password = hash_password(password)

            if user is None:
                user = User(
                    email=email,
                    role=RoleEnum.admin,
                    hashed_password=hashed_password,
                    email_verified=True,
                    is_active=True,
                )
                db.add(user)
                message = "Created new admin user"
                created = True
            else:
                user.role = RoleEnum.admin
                user.hashed_password = hashed_password
                user.email_verified = True
                user.is_active = True
                message = "Updated existing user to admin"
                created = False

            results.append(
                AdminEnsureResult(
                    email=email,
                    created=created,
                    password=password,
                    message=message,
                )
            )

        if dry_run:
            await db.rollback()

        return results

    @staticmethod
    async def deactivate_admin(
        email: str,
        db: AsyncSession,
        dry_run: bool = False,
    ) -> AdminDeactivateResult:
        """Deactivate the admin user with the given email.

        The user's role is downgraded to ``user`` and ``is_active`` is set to
        ``False``. This follows the project soft-delete convention and avoids
        foreign-key violations that a hard delete could trigger.

        Returns a result describing the outcome. In the unlikely event that a
        foreign-key constraint is still violated, the transaction is rolled
        back and ``deactivated`` is ``False``.
        """
        normalized_email = email.lower()
        result = await db.execute(
            select(User).where(func.lower(User.email) == normalized_email)
        )
        user = result.scalars().first()

        if user is None:
            return AdminDeactivateResult(
                email=normalized_email,
                deactivated=False,
                message="User not found",
            )

        if user.role != RoleEnum.admin:
            return AdminDeactivateResult(
                email=normalized_email,
                deactivated=False,
                message=f"User found but has role '{user.role.value}', not admin",
            )

        user.role = RoleEnum.user
        user.is_active = False

        try:
            await db.flush()
        except IntegrityError as exc:
            await db.rollback()
            return AdminDeactivateResult(
                email=normalized_email,
                deactivated=False,
                message=(
                    "Cannot deactivate admin: foreign key constraint violation "
                    "(related entities may include orders, carts, favorites, "
                    "notifications, reviews, suppliers). "
                    f"Details: {exc.orig}"
                ),
            )

        if dry_run:
            await db.rollback()

        return AdminDeactivateResult(
            email=normalized_email,
            deactivated=True,
            message="Admin user deactivated",
        )
