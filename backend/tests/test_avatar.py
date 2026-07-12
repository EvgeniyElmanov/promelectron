import io
import os

import pytest


class TestAvatarUpload:
    """Tests for POST /api/v1/me/avatar/."""

    @pytest.mark.asyncio
    async def test_upload_avatar_success(self, client, test_user, user_token):
        """Valid PNG upload returns AvatarUploadOut and updates DB."""
        response = await client.post(
            "/api/v1/me/avatar/",
            headers={"Authorization": f"Bearer {user_token}"},
            files={"file": ("avatar.png", io.BytesIO(b"fake-image-content"), "image/png")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["avatar_url"] == data["original"]
        assert data["original"].endswith(".png")
        assert data["small"].endswith("_small.webp")
        assert data["medium"].endswith("_medium.webp")
        assert data["large"].endswith("_large.webp")
        assert f"/avatars/{test_user.id}/" in data["original"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("filename,content_type", [
        ("avatar.jpg", "image/jpeg"),
        ("avatar.jpeg", "image/jpeg"),
        ("avatar.webp", "image/webp"),
        ("avatar.gif", "image/gif"),
    ])
    async def test_upload_avatar_allowed_extensions(
        self, client, test_user, user_token, filename, content_type
    ):
        """All allowed image extensions are accepted."""
        response = await client.post(
            "/api/v1/me/avatar/",
            headers={"Authorization": f"Bearer {user_token}"},
            files={"file": (filename, io.BytesIO(b"fake-image-content"), content_type)},
        )
        assert response.status_code == 200
        assert response.json()["avatar_url"]

    @pytest.mark.asyncio
    async def test_upload_avatar_saves_to_db(self, client, test_user, user_token, test_session):
        """Uploaded avatar_url is persisted in the database."""
        response = await client.post(
            "/api/v1/me/avatar/",
            headers={"Authorization": f"Bearer {user_token}"},
            files={"file": ("avatar.png", io.BytesIO(b"fake-image-content"), "image/png")},
        )
        assert response.status_code == 200
        data = response.json()

        await test_session.refresh(test_user)
        assert test_user.avatar_url == data["avatar_url"]

    @pytest.mark.asyncio
    async def test_upload_avatar_invalid_extension(self, client, test_user, user_token):
        """Non-image extension returns 400."""
        response = await client.post(
            "/api/v1/me/avatar/",
            headers={"Authorization": f"Bearer {user_token}"},
            files={"file": ("avatar.txt", io.BytesIO(b"not an image"), "text/plain")},
        )
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_avatar_too_large(self, client, test_user, user_token):
        """File exceeding 5 MB returns 413."""
        oversized = b"x" * (5 * 1024 * 1024 + 1)
        response = await client.post(
            "/api/v1/me/avatar/",
            headers={"Authorization": f"Bearer {user_token}"},
            files={"file": ("avatar.png", io.BytesIO(oversized), "image/png")},
        )
        assert response.status_code == 413
        assert "File too large" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_avatar_unauthorized(self, client):
        """Request without token returns 403."""
        response = await client.post(
            "/api/v1/me/avatar/",
            files={"file": ("avatar.png", io.BytesIO(b"fake-image-content"), "image/png")},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_upload_avatar_deletes_old_avatar(
        self, client, test_user, user_token, test_session, monkeypatch
    ):
        """Old avatar deletion is triggered when user already has one."""
        old_avatar_url = "/uploads/avatars/old.png"
        test_user.avatar_url = old_avatar_url
        await test_session.commit()

        deleted_keys = []

        class TrackedStorage:
            async def upload_image(self, key, file, content=None):
                base, _ = os.path.splitext(key)
                return {
                    "original": f"/uploads/{key}",
                    "small": f"/uploads/{base}_small.webp",
                    "medium": f"/uploads/{base}_medium.webp",
                    "large": f"/uploads/{base}_large.webp",
                }

            async def delete_image(self, key):
                deleted_keys.append(key)

        monkeypatch.setattr("src.app.api.users.storage", TrackedStorage())

        response = await client.post(
            "/api/v1/me/avatar/",
            headers={"Authorization": f"Bearer {user_token}"},
            files={"file": ("avatar.png", io.BytesIO(b"fake-image-content"), "image/png")},
        )
        assert response.status_code == 200
        assert old_avatar_url in deleted_keys

    @pytest.mark.asyncio
    async def test_upload_avatar_deletion_failure_does_not_block_upload(
        self, client, test_user, user_token, test_session, monkeypatch
    ):
        """If deleting the old avatar fails, the new upload still succeeds."""
        test_user.avatar_url = "/uploads/avatars/old.png"
        await test_session.commit()

        deleted_keys = []

        class FailingDeleteStorage:
            async def upload_image(self, key, file, content=None):
                base, _ = os.path.splitext(key)
                return {
                    "original": f"/uploads/{key}",
                    "small": f"/uploads/{base}_small.webp",
                    "medium": f"/uploads/{base}_medium.webp",
                    "large": f"/uploads/{base}_large.webp",
                }

            async def delete_image(self, key):
                deleted_keys.append(key)
                raise RuntimeError("storage unavailable")

        monkeypatch.setattr("src.app.api.users.storage", FailingDeleteStorage())

        response = await client.post(
            "/api/v1/me/avatar/",
            headers={"Authorization": f"Bearer {user_token}"},
            files={"file": ("avatar.png", io.BytesIO(b"fake-image-content"), "image/png")},
        )
        assert response.status_code == 200
        assert deleted_keys
        assert response.json()["avatar_url"]

    @pytest.mark.asyncio
    async def test_upload_avatar_invalid_content_type(self, client, test_user, user_token):
        """Valid extension but non-image content_type returns 400."""
        response = await client.post(
            "/api/v1/me/avatar/",
            headers={"Authorization": f"Bearer {user_token}"},
            files={"file": ("avatar.png", io.BytesIO(b"not an image"), "application/octet-stream")},
        )
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_avatar_requires_trailing_slash(self, client, test_user, user_token):
        """FastAPI redirects missing trailing slash, but multipart POST loses body."""
        response = await client.post(
            "/api/v1/me/avatar",
            headers={"Authorization": f"Bearer {user_token}"},
            files={"file": ("avatar.png", io.BytesIO(b"fake-image-content"), "image/png")},
        )
        # FastAPI returns a 307/308 redirect for missing trailing slash; the
        # Location header points to the slash-terminated path.
        assert response.status_code in (307, 308)
        assert response.headers.get("location").endswith("/api/v1/me/avatar/")

    @pytest.mark.asyncio
    async def test_upload_avatar_storage_error_returns_500(
        self, client, test_user, user_token, monkeypatch
    ):
        """If storage.upload_image raises, endpoint returns 500 with generic message."""

        class FailingUploadStorage:
            async def upload_image(self, key, file, content=None):
                raise RuntimeError("storage down")

            async def delete_image(self, key):
                pass

        monkeypatch.setattr("src.app.api.users.storage", FailingUploadStorage())
        response = await client.post(
            "/api/v1/me/avatar/",
            headers={"Authorization": f"Bearer {user_token}"},
            files={"file": ("avatar.png", io.BytesIO(b"fake-image-content"), "image/png")},
        )
        assert response.status_code == 500
        detail = response.json()["detail"]
        assert "Avatar upload failed" in detail
        assert "storage down" not in detail

    @pytest.mark.asyncio
    async def test_upload_avatar_update_profile_error_returns_500(
        self, client, test_user, user_token, monkeypatch
    ):
        """If UserService.update_profile raises, endpoint returns 500 with generic message."""

        class OkStorage:
            async def upload_image(self, key, file, content=None):
                return {
                    "original": "/uploads/avatars/1/test.png",
                    "small": "/uploads/avatars/1/test_small.webp",
                    "medium": "/uploads/avatars/1/test_medium.webp",
                    "large": "/uploads/avatars/1/test_large.webp",
                }

            async def delete_image(self, key):
                pass

        monkeypatch.setattr("src.app.api.users.storage", OkStorage())

        async def failing_update_profile(*, user_id, user_data, db):
            raise RuntimeError("db locked")

        monkeypatch.setattr(
            "src.app.services.user_service.UserService.update_profile",
            failing_update_profile,
        )

        response = await client.post(
            "/api/v1/me/avatar/",
            headers={"Authorization": f"Bearer {user_token}"},
            files={"file": ("avatar.png", io.BytesIO(b"fake-image-content"), "image/png")},
        )
        assert response.status_code == 500
        detail = response.json()["detail"]
        assert "Failed to save avatar" in detail
        assert "db locked" not in detail
