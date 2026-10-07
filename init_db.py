from app.database import engine, Base, SessionLocal
from app.models.user import User
from app.models.role import Role
from app.models.user_role import UserRole
from app.core.security import hash_password

import app.models  # noqa


def init_database():
    print("⏳ Đang khởi tạo các bảng trong cơ sở dữ liệu...")
    Base.metadata.create_all(bind=engine)
    print("✅ Đã tạo các bảng thành công!")

    db = SessionLocal()

    # 1. Khởi tạo danh sách Roles (Chỉ truyền các trường có trong Model Role)
    roles_data = [
        {"role_id": 1, "role_name": "ADMIN"},
        {"role_id": 2, "role_name": "MANAGER"},
        {"role_id": 3, "role_name": "INSTRUCTOR"},
        {"role_id": 4, "role_name": "STUDENT"},
    ]

    for r in roles_data:
        role = db.query(Role).filter(Role.role_id == r["role_id"]).first()
        if not role:
            db.add(Role(role_id=r["role_id"], role_name=r["role_name"]))
    db.commit()

    # 2. Khởi tạo danh sách Users mẫu cho Sprint 1 & 2
    users_data = [
        {
            "username": "admin",
            "full_name": "Quản Trị Viên",
            "email": "admin@gmail.com",
            "phone": "0912345678",
            "password": hash_password("123456"),
            "role_id": 1,
        },
        {
            "username": "manager",
            "full_name": "Quản Lý Đào Tạo",
            "email": "manager@gmail.com",
            "phone": "0912345679",
            "password": hash_password("123456"),
            "role_id": 2,
        },
        {
            "username": "instructor1",
            "full_name": "Giảng Viên A",
            "email": "instructor1@gmail.com",
            "phone": "0912345680",
            "password": hash_password("123456"),
            "role_id": 3,
        },
        {
            "username": "student1",
            "full_name": "Học Viên B",
            "email": "student1@gmail.com",
            "phone": "0912345681",
            "password": hash_password("123456"),
            "role_id": 4,
        },
    ]

    print("\n⏳ Đang khởi tạo tài khoản mẫu...")
    for u_data in users_data:
        role_id = u_data.pop("role_id")
        user = db.query(User).filter(User.email == u_data["email"]).first()
        if not user:
            new_user = User(
                **u_data,
                role_id=role_id,
                is_locked=False,
                failed_login_attempts=0
            )
            db.add(new_user)
            db.flush()
            db.add(UserRole(user_id=new_user.user_id, role_id=role_id))
            print(f"  + Đã tạo: {u_data['email']}")
        else:
            print(f"  * Đã tồn tại: {u_data['email']}")

    db.commit()
    db.close()
    print("\n🎉 Hoàn thành khởi tạo dữ liệu Sprint 1 & 2!")


if __name__ == "__main__":
    init_database()