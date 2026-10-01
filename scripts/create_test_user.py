from app.database import SessionLocal
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.core.security import hash_password


db = SessionLocal()

try:
    existing_user = db.query(User).filter(
        User.username == "instructor_test"
    ).first()

    if existing_user:
        print("Tài khoản instructor_test đã tồn tại.")

    else:
        instructor_role = db.query(Role).filter(
            Role.role_name == "INSTRUCTOR"
        ).first()

        if instructor_role is None:
            print("Không tìm thấy vai trò INSTRUCTOR.")

        else:
            user = User(
                username="instructor_test",
                password=hash_password("Instructor123"),
                full_name="Giảng viên Test",
                email="instructor@test.com",
                phone="0123456789",
                role_id=instructor_role.role_id,
                failed_login_attempts=0,
                locked_until=None,
                is_locked=False,
                lock_reason=None
            )

            db.add(user)
            db.flush()

            user_role = UserRole(
                user_id=user.user_id,
                role_id=instructor_role.role_id
            )

            db.add(user_role)
            db.commit()

            print("Tạo tài khoản INSTRUCTOR thành công.")
            print(f"User ID: {user.user_id}")
            print("Email: instructor@test.com")
            print("Password: Instructor123")

except Exception as error:
    db.rollback()
    print("Có lỗi:", error)

finally:
    db.close()