from datetime import date, timedelta
import base64
import io

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from PIL import Image

from app.core.security import ALGORITHM, SECRET_KEY, create_access_token, create_refresh_token
from app.database import SessionLocal
from app.main import app
from app.migrations import ensure_profile_columns
from app.models.user import User
from app.models.user_role import UserRole


@pytest.fixture
def profile_context():
    with SessionLocal() as db:
        first = User(username="profile_first", full_name="Nguyễn Văn A", email="first@example.com",
                     password="unused", phone="0912345678", role_id=3,
                     date_of_birth=date(2000, 1, 2), address="Hà Nội")
        second = User(username="profile_second", full_name="Trần Thị B", email="second@example.com",
                      password="unused", phone="0987654321", role_id=3)
        db.add_all([first, second])
        db.flush()
        db.add_all([UserRole(user_id=first.user_id, role_id=3), UserRole(user_id=second.user_id, role_id=3)])
        db.commit()
        first_id, second_id = first.user_id, second.user_id
    token = create_access_token(first_id, "STUDENT")
    with TestClient(app) as client:
        yield client, {"Authorization": f"Bearer {token}"}, first_id, second_id
    with SessionLocal() as db:
        db.query(UserRole).filter(UserRole.user_id.in_([first_id, second_id])).delete()
        db.query(User).filter(User.user_id.in_([first_id, second_id])).delete()
        db.commit()


def test_get_own_profile(profile_context):
    client, headers, first_id, _ = profile_context
    response = client.get("/api/me", headers=headers)
    assert response.status_code == 200
    assert response.json() == {
        "user_id": first_id, "full_name": "Nguyễn Văn A", "email": "first@example.com",
        "phone": "0912345678", "date_of_birth": "2000-01-02", "address": "Hà Nội",
        "avatar_url": None,
        "avatar_thumbnail_url": None,
        "roles": ["STUDENT"], "permissions": [],
    }


def test_update_all_fields_and_persist_only_own_profile(profile_context):
    client, headers, first_id, second_id = profile_context
    response = client.put("/api/me", headers=headers, json={
        "full_name": "  Nguyễn Văn Mới  ", "phone": "+84987654321",
        "date_of_birth": "1999-12-31", "address": "  Thành phố Hồ Chí Minh  ",
    })
    assert response.status_code == 200
    assert response.json()["phone"] == "0987654321"
    with SessionLocal() as db:
        first, second = db.get(User, first_id), db.get(User, second_id)
        assert first.full_name == "Nguyễn Văn Mới"
        assert first.date_of_birth == date(1999, 12, 31)
        assert first.address == "Thành phố Hồ Chí Minh"
        assert first.email == "first@example.com" and first.role_id == 3
        assert second.full_name == "Trần Thị B" and second.address is None
        assert db.query(UserRole).filter_by(user_id=first_id).one().role_id == 3
    assert client.get("/api/me", headers=headers).json() == response.json()


@pytest.mark.parametrize("field,value", [
    ("email", "changed@example.com"), ("email", None), ("role", "ADMIN"),
    ("roles", ["ADMIN"]), ("role_id", 1), ("permissions", ["USER_MANAGE"]),
    ("user_id", 999), ("id", 999), ("username", "changed"), ("is_locked", False),
])
def test_forbidden_fields_reject_entire_request(profile_context, field, value):
    client, headers, first_id, _ = profile_context
    response = client.put("/api/me", headers=headers, json={"full_name": "Không được lưu", field: value})
    assert response.status_code == 422
    with SessionLocal() as db:
        user = db.get(User, first_id)
        assert user.full_name == "Nguyễn Văn A"
        assert user.email == "first@example.com" and user.role_id == 3


@pytest.mark.parametrize("phone", ["0312345678", "0512345678", "0712345678", "0812345678",
                                   "0912345678", "02812345678", "+842812345678", "+84912345678"])
def test_valid_vietnamese_phones(profile_context, phone):
    client, headers, _, _ = profile_context
    response = client.put("/api/me", headers=headers, json={"phone": phone})
    assert response.status_code == 200
    assert response.json()["phone"] == ("0" + phone[3:] if phone.startswith("+84") else phone)


@pytest.mark.parametrize("phone", ["0123456789", "0612345678", "091234567", "09123456789",
                                   "+840912345678", "+15551234567", "09123abc78", "091 234 5678",
                                   "０９１２３４５６７８", 912345678])
def test_invalid_phone_does_not_change_profile(profile_context, phone):
    client, headers, _, _ = profile_context
    response = client.put("/api/me", headers=headers, json={"phone": phone, "address": "Không lưu"})
    assert response.status_code == 422
    profile = client.get("/api/me", headers=headers).json()
    assert profile["phone"] == "0912345678" and profile["address"] == "Hà Nội"


def test_partial_update_preserves_omitted_fields(profile_context):
    client, headers, _, _ = profile_context
    response = client.put("/api/me", headers=headers, json={"full_name": "Tên mới"})
    assert response.status_code == 200
    assert response.json()["phone"] == "0912345678"
    assert response.json()["date_of_birth"] == "2000-01-02"
    assert response.json()["address"] == "Hà Nội"


@pytest.mark.parametrize("value", [None, "", "   "])
def test_clear_optional_contact_fields(profile_context, value):
    client, headers, _, _ = profile_context
    response = client.put("/api/me", headers=headers, json={"phone": value, "address": value, "date_of_birth": None})
    assert response.status_code == 200
    assert all(response.json()[key] is None for key in ("phone", "address", "date_of_birth"))


@pytest.mark.parametrize("payload", [{}, {"full_name": " "}, {"full_name": None}, {"full_name": "A" * 101},
                                    {"address": "A" * 256}, {"date_of_birth": "2025-02-30"},
                                    {"date_of_birth": "01/02/2000"}, {"date_of_birth": 123},
                                    {"date_of_birth": (date.today() + timedelta(days=1)).isoformat()}])
def test_invalid_profile_data(profile_context, payload):
    client, headers, _, _ = profile_context
    assert client.put("/api/me", headers=headers, json=payload).status_code == 422


@pytest.mark.parametrize("method", ["get", "put"])
@pytest.mark.parametrize("token", [None, "invalid-token"])
def test_authentication_required(profile_context, method, token):
    client, _, _, _ = profile_context
    kwargs = {"headers": {"Authorization": f"Bearer {token}"}} if token else {}
    if method == "put": kwargs["json"] = {"full_name": "Tên mới"}
    assert getattr(client, method)("/api/me", **kwargs).status_code in (401, 403)


def test_expired_and_refresh_tokens_cannot_update(profile_context):
    client, _, first_id, _ = profile_context
    expired = jwt.encode({"sub": str(first_id), "type": "access", "exp": 0}, SECRET_KEY, algorithm=ALGORITHM)
    for token in (expired, create_refresh_token(first_id)):
        assert client.put("/api/me", headers={"Authorization": f"Bearer {token}"},
                          json={"full_name": "Tên mới"}).status_code == 401


def test_locked_user_cannot_read_or_update(profile_context):
    client, headers, first_id, _ = profile_context
    with SessionLocal() as db:
        db.get(User, first_id).is_locked = True
        db.commit()
    assert client.get("/api/me", headers=headers).status_code == 423
    assert client.put("/api/me", headers=headers, json={"phone": "0987654321"}).status_code == 423


def test_other_user_id_cannot_be_targeted(profile_context):
    client, headers, first_id, second_id = profile_context
    assert client.put("/api/me", headers=headers, json={"user_id": second_id, "full_name": "Bị sửa"}).status_code == 422
    assert client.put(f"/api/me/{second_id}", headers=headers, json={"full_name": "Bị sửa"}).status_code == 404
    assert client.put(f"/api/users/{second_id}", headers=headers, json={"full_name": "Bị sửa"}).status_code == 403
    # Query parameters cannot change the authenticated identity.
    response = client.put(f"/api/me?user_id={second_id}", headers=headers, json={"full_name": "Tên mới"})
    assert response.status_code == 200 and response.json()["user_id"] == first_id
    with SessionLocal() as db:
        assert db.get(User, second_id).full_name == "Trần Thị B"


def test_admin_self_role_exception_preserves_email_and_admin_protection(profile_context):
    client, headers, first_id, second_id = profile_context
    with SessionLocal() as db:
        db.add(UserRole(user_id=first_id, role_id=1))
        db.commit()
    assert client.put(f"/api/users/{first_id}", headers=headers,
                      json={"email": "changed@example.com", "full_name": "Không lưu"}).status_code == 403
    assert client.put(f"/api/users/{first_id}", headers=headers,
                      json={"phone": "invalid"}).status_code == 403
    assert client.post(f"/api/users/{first_id}/roles", headers=headers,
                       json={"role_id": 2}).status_code == 200
    # DELETE accepts a JSON body in the existing API.
    assert client.request("DELETE", f"/api/users/{first_id}/roles", headers=headers,
                          json={"role_id": 3}).status_code == 200
    assert client.request("DELETE", f"/api/users/{first_id}/roles", headers=headers,
                          json={"role_id": 1}).status_code == 403
    assert client.put("/api/me", headers=headers, json={"email": "changed@example.com"}).status_code == 422
    with SessionLocal() as db:
        assert db.get(User, first_id).full_name == "Nguyễn Văn A"
        assert db.get(User, first_id).email == "first@example.com"
        assert {r.role_id for r in db.query(UserRole).filter_by(user_id=first_id)} == {1, 2}
    # An administrator retains the existing ability to manage OTHER accounts.
    assert client.put(f"/api/users/{second_id}", headers=headers,
                      json={"email": "managed@example.com"}).status_code == 200


def test_profile_migration_preserves_existing_data_and_is_idempotent():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (user_id INTEGER PRIMARY KEY, full_name VARCHAR(100))"))
        connection.execute(text("INSERT INTO users VALUES (1, 'Tên hiện có')"))
    ensure_profile_columns(engine)
    ensure_profile_columns(engine)
    assert {c["name"] for c in inspect(engine).get_columns("users")} == {
        "user_id", "full_name", "date_of_birth", "address", "avatar_url", "avatar_thumbnail_url",
    }
    with engine.connect() as connection:
        assert connection.execute(text("SELECT * FROM users")).one() == (1, "Tên hiện có", None, None, None, None)
    engine.dispose()


def avatar_bytes(format="PNG", color="red", size=(400, 200)):
    output = io.BytesIO()
    image = Image.new("RGB", size, color)
    image.save(output, format=format)
    return output.getvalue()


@pytest.mark.parametrize("format,mime", [("PNG", "image/png"), ("JPEG", "image/jpeg")])
def test_upload_avatar_normalizes_image_and_only_updates_own_account(profile_context, format, mime):
    client, headers, first_id, second_id = profile_context
    before = client.get("/api/me", headers=headers).json()
    response = client.put(f"/api/me/avatar?user_id={second_id}", headers=headers,
                          data={"user_id": str(second_id)},
                          files={"file": ("../../avatar." + format.lower(), avatar_bytes(format), mime)})
    assert response.status_code == 200
    profile = response.json()
    assert profile["user_id"] == first_id
    assert profile["avatar_url"].startswith("data:image/jpeg;base64,")
    assert len(profile["avatar_url"]) < 65_535
    with Image.open(io.BytesIO(base64.b64decode(profile["avatar_url"].split(",")[1]))) as image:
        assert image.size == (256, 256) and image.format == "JPEG"
        assert not image.getexif()
    with Image.open(io.BytesIO(base64.b64decode(profile["avatar_thumbnail_url"].split(",")[1]))) as thumbnail:
        assert thumbnail.size == (64, 64) and thumbnail.format == "JPEG"
        assert not thumbnail.getexif()
    assert len(profile["avatar_thumbnail_url"]) < len(profile["avatar_url"])
    assert {k: v for k, v in profile.items() if k not in ("avatar_url", "avatar_thumbnail_url")} == {
        k: v for k, v in before.items() if k not in ("avatar_url", "avatar_thumbnail_url")
    }
    assert client.get("/api/me", headers=headers).json() == profile
    with SessionLocal() as db:
        assert db.get(User, first_id).avatar_url == profile["avatar_url"]
        assert db.get(User, first_id).avatar_thumbnail_url == profile["avatar_thumbnail_url"]
        assert db.get(User, second_id).avatar_url is None
        assert db.get(User, second_id).avatar_thumbnail_url is None


def test_replace_and_remove_avatar(profile_context):
    client, headers, _, _ = profile_context
    first = client.put("/api/me/avatar", headers=headers,
                       files={"file": ("first.png", avatar_bytes(color="red"), "image/png")})
    second = client.put("/api/me/avatar", headers=headers,
                        files={"file": ("second.png", avatar_bytes(color="blue"), "image/png")})
    assert first.status_code == second.status_code == 200
    assert first.json()["avatar_url"] != second.json()["avatar_url"]
    assert first.json()["avatar_thumbnail_url"] != second.json()["avatar_thumbnail_url"]
    removed = client.delete("/api/me/avatar", headers=headers)
    assert removed.status_code == 200 and removed.json()["avatar_url"] is None
    assert removed.json()["avatar_thumbnail_url"] is None
    assert client.get("/api/me", headers=headers).json()["avatar_url"] is None
    assert client.delete("/api/me/avatar", headers=headers).status_code == 200


@pytest.mark.parametrize("content,mime", [
    (b"", "image/png"), (b"not a JPEG", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\ncorrupted image", "image/png"),
    (b"<svg><script>alert(1)</script></svg>", "image/svg+xml"),
    (b"<svg><script>alert(1)</script></svg>", "image/png"),
    (b"not an image", "text/plain"), (avatar_bytes("GIF"), "image/png"),
    (avatar_bytes("WEBP"), "image/webp"), (avatar_bytes("WEBP"), "image/png"),
    (avatar_bytes("WEBP"), "image/jpeg"),
])
def test_invalid_avatar_keeps_previous_image(profile_context, content, mime):
    client, headers, _, _ = profile_context
    previous = client.put("/api/me/avatar", headers=headers,
                          files={"file": ("valid.png", avatar_bytes(), "image/png")}).json()
    response = client.put("/api/me/avatar", headers=headers, files={"file": ("fake.png", content, mime)})
    assert response.status_code == 400
    assert client.get("/api/me", headers=headers).json() == previous


def test_oversized_avatar_is_rejected(profile_context):
    client, headers, _, _ = profile_context
    response = client.put("/api/me/avatar", headers=headers,
                          files={"file": ("large.png", b"x" * (2 * 1024 * 1024 + 1), "image/png")})
    assert response.status_code == 413
    assert client.get("/api/me", headers=headers).json()["avatar_url"] is None


def test_image_with_too_many_pixels_is_rejected(profile_context):
    client, headers, _, _ = profile_context
    image = Image.new("1", (5000, 4001))
    output = io.BytesIO()
    image.save(output, format="PNG")
    response = client.put("/api/me/avatar", headers=headers,
                          files={"file": ("large.png", output.getvalue(), "image/png")})
    assert response.status_code == 400
    assert "20 triệu" in response.json()["detail"]


def test_avatar_endpoints_require_authentication_and_reject_locked_account(profile_context):
    client, headers, first_id, _ = profile_context
    assert client.put("/api/me/avatar", files={"file": ("image.png", avatar_bytes(), "image/png")}).status_code in (401, 403)
    assert client.delete("/api/me/avatar").status_code in (401, 403)
    with SessionLocal() as db:
        db.get(User, first_id).is_locked = True
        db.commit()
    assert client.put("/api/me/avatar", headers=headers,
                      files={"file": ("image.png", avatar_bytes(), "image/png")}).status_code == 423
    assert client.delete("/api/me/avatar", headers=headers).status_code == 423


@pytest.mark.parametrize("field", ["avatar_url", "avatar_thumbnail_url"])
def test_avatar_url_cannot_be_injected_via_profile_json(profile_context, field):
    client, headers, _, _ = profile_context
    assert client.put("/api/me", headers=headers, json={field: "javascript:alert(1)"}).status_code == 422


@pytest.mark.parametrize("size,expected_status", [
    (2 * 1024 * 1024 - 1, 200), (2 * 1024 * 1024, 200), (2 * 1024 * 1024 + 1, 413),
])
def test_scrum31_upload_size_boundary(profile_context, size, expected_status):
    client, headers, _, _ = profile_context
    original = avatar_bytes()
    content = original + b"\0" * (size - len(original))
    response = client.put("/api/me/avatar", headers=headers,
                          files={"file": ("boundary.png", content, "image/png")})
    assert response.status_code == expected_status
    if expected_status == 413:
        assert "2 MB" in response.json()["detail"]
        profile = client.get("/api/me", headers=headers).json()
        assert profile["avatar_url"] is None and profile["avatar_thumbnail_url"] is None


@pytest.mark.parametrize("size", [(400, 200), (200, 400)])
def test_scrum31_square_crop_uses_center_without_stretching(profile_context, size):
    client, headers, _, _ = profile_context
    image = Image.new("RGB", size, "blue")
    if size[0] > size[1]:
        image.paste("red", (100, 0, 300, 200))
    else:
        image.paste("red", (0, 100, 200, 300))
    output = io.BytesIO()
    image.save(output, format="PNG")
    response = client.put("/api/me/avatar", headers=headers,
                          files={"file": ("rectangular.png", output.getvalue(), "image/png")})
    assert response.status_code == 200
    for field, pixels in (("avatar_url", 256), ("avatar_thumbnail_url", 64)):
        with Image.open(io.BytesIO(base64.b64decode(response.json()[field].split(",")[1]))) as result:
            assert result.size == (pixels, pixels)
            for point in ((pixels // 4, pixels // 4), (3 * pixels // 4, 3 * pixels // 4)):
                red, green, blue = result.getpixel(point)
                assert red > 240 and green < 15 and blue < 15


def test_scrum31_phone_photo_orientation_applied_before_crop(profile_context):
    client, headers, _, _ = profile_context
    image = Image.new("RGB", (400, 200), "red")
    image.paste("blue", (200, 0, 400, 100))
    image.paste((0, 255, 0), (0, 100, 200, 200))
    image.paste("yellow", (200, 100, 400, 200))
    exif = Image.Exif()
    exif[274] = 6  # A phone photo whose display orientation is rotated clockwise.
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=95, exif=exif)
    response = client.put("/api/me/avatar", headers=headers,
                          files={"file": ("phone.jpg", output.getvalue(), "image/jpeg")})
    assert response.status_code == 200
    for field, size in (("avatar_url", 256), ("avatar_thumbnail_url", 64)):
        with Image.open(io.BytesIO(base64.b64decode(response.json()[field].split(",")[1]))) as result:
            expected = [((size // 4, size // 4), (0, 255, 0)),
                        ((3 * size // 4, size // 4), (255, 0, 0)),
                        ((size // 4, 3 * size // 4), (255, 255, 0)),
                        ((3 * size // 4, 3 * size // 4), (0, 0, 255))]
            for point, color in expected:
                assert all(abs(actual - wanted) < 25 for actual, wanted in zip(result.getpixel(point), color))
            assert not result.getexif()


def test_scrum31_transparent_png_has_white_background(profile_context):
    client, headers, _, _ = profile_context
    image = Image.new("RGBA", (200, 400), (0, 0, 0, 0))
    output = io.BytesIO()
    image.save(output, format="PNG")
    response = client.put("/api/me/avatar", headers=headers,
                          files={"file": ("transparent.png", output.getvalue(), "image/png")})
    assert response.status_code == 200
    for field in ("avatar_url", "avatar_thumbnail_url"):
        with Image.open(io.BytesIO(base64.b64decode(response.json()[field].split(",")[1]))) as result:
            assert all(channel > 240 for channel in result.getpixel((10, 10)))
