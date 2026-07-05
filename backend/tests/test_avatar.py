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
    async def test_upload_avatar_requires_trailing_slash(self, client, test_user, user_token):
        """FastAPI redirects missing trailing slash, but multipart POST loses body."""
        response = await client.post(
            "/api/v1/me/avatar",
            headers={"Authorization": f"Bearer {user_token}"},
            files={"file": ("avatar.png", io.BytesIO(b"fake-image-content"), "image/png")},
        )
        # Without trailing slash the response is a redirect, not the successful upload.
        assert response.status_code != 200
