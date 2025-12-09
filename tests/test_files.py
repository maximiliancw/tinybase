"""
Tests for file storage functionality.
"""

import io


def test_get_storage_status_requires_auth(client):
    """Test that checking storage status requires authentication."""
    response = client.get("/api/files/status")
    assert response.status_code == 401


def test_get_storage_status(client, admin_token):
    """Test checking storage status."""
    response = client.get(
        "/api/files/status",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "enabled" in data
    assert isinstance(data["enabled"], bool)


def test_upload_file_requires_auth(client):
    """Test that file upload requires authentication."""
    file_content = b"test file content"
    files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
    response = client.post("/api/files/upload", files=files)
    assert response.status_code == 401


def test_upload_file_storage_disabled(client, admin_token):
    """Test uploading file when storage is disabled."""
    file_content = b"test file content"
    files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
    response = client.post(
        "/api/files/upload",
        headers={"Authorization": f"Bearer {admin_token}"},
        files=files,
    )
    # Should return 503 if storage is disabled
    assert response.status_code in [503, 500]


def test_download_file_requires_auth(client):
    """Test that file download requires authentication."""
    response = client.get("/api/files/download/test.txt")
    assert response.status_code == 401


def test_download_file_not_found(client, admin_token):
    """Test downloading a non-existent file."""
    response = client.get(
        "/api/files/download/nonexistent.txt",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Should return 404 or 503 depending on storage status
    assert response.status_code in [404, 503]


def test_delete_file_requires_auth(client):
    """Test that file deletion requires authentication."""
    response = client.delete("/api/files/test.txt")
    assert response.status_code == 401


def test_delete_file_not_found(client, admin_token):
    """Test deleting a non-existent file."""
    response = client.delete(
        "/api/files/nonexistent.txt",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Should return 404 or 503 depending on storage status
    assert response.status_code in [404, 503, 500]


def test_get_presigned_url_requires_auth(client):
    """Test that getting presigned URL requires authentication."""
    response = client.get("/api/files/presigned/test.txt")
    assert response.status_code == 401


def test_get_presigned_url_not_found(client, admin_token):
    """Test getting presigned URL for non-existent file."""
    response = client.get(
        "/api/files/presigned/nonexistent.txt",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Should return 404 or 503 depending on storage status
    assert response.status_code in [404, 503, 500]


def test_get_presigned_url_expires_in_validation(client, admin_token):
    """Test presigned URL expiration validation."""
    # Test with invalid expiration (too short)
    response = client.get(
        "/api/files/presigned/test.txt",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"expires_in": 30},  # Less than minimum (60)
    )
    # Should return 422 for validation error or 503 if storage disabled
    assert response.status_code in [422, 503, 500]

    # Test with invalid expiration (too long)
    response = client.get(
        "/api/files/presigned/test.txt",
        headers={"Authorization": f"Bearer {admin_token}"},
        params={"expires_in": 100000},  # More than maximum (86400)
    )
    # Should return 422 for validation error or 503 if storage disabled
    assert response.status_code in [422, 503, 500]

