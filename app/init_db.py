from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from app.database import Base, engine, SessionLocal
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.security.password import hash_password


def ensure_db_schema():
    Base.metadata.create_all(bind=engine)
    try:
        inspector = inspect(engine)
        if "users" in inspector.get_table_names():
            columns = [col["name"] for col in inspector.get_columns("users")]
            with engine.connect() as conn:
                if "is_locked" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN is_locked BOOLEAN DEFAULT 0 NOT NULL"))
                if "locked_at" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN locked_at DATETIME"))
                if "lock_reason" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN lock_reason VARCHAR(500)"))
                if "phone_number" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN phone_number VARCHAR(20)"))
                if "avatar_url" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500)"))
                if "bio" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN bio VARCHAR(1000)"))
                if "address" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN address VARCHAR(255)"))
                if "date_of_birth" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN date_of_birth VARCHAR(50)"))
                if "gender" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN gender VARCHAR(20)"))
                conn.commit()
    except Exception:
        pass


def seed_roles_and_permissions(db: Session):
    # 1. Khởi tạo danh sách quyền hạn (Permissions)
    permissions_data = [
        # Quản lý người dùng
        {"name": "Xem người dùng", "code": "user:read", "module": "users", "description": "Xem danh sách và chi tiết người dùng"},
        {"name": "Tạo người dùng", "code": "user:create", "module": "users", "description": "Tạo tài khoản người dùng mới"},
        {"name": "Cập nhật người dùng", "code": "user:update", "module": "users", "description": "Cập nhật thông tin tài khoản người dùng"},
        {"name": "Xóa người dùng", "code": "user:delete", "module": "users", "description": "Xóa tài khoản người dùng"},
        {"name": "Khóa/Mở khóa tài khoản", "code": "user:lock", "module": "users", "description": "Khóa hoặc mở khóa tài khoản người dùng"},
        # Quản lý vai trò
        {"name": "Phân quyền vai trò", "code": "role:assign", "module": "roles", "description": "Gán hoặc thu hồi vai trò cho người dùng"},
        # Quản lý đào tạo (Sprint 1 & Sprint 2)
        {"name": "Xem khóa học", "code": "course:read", "module": "courses", "description": "Xem danh sách và nội dung khóa học"},
        {"name": "Quản lý khóa học", "code": "course:manage", "module": "courses", "description": "Tạo, sửa, xóa khóa học và lớp đào tạo"},
        {"name": "Quản lý chương trình đào tạo", "code": "program:manage", "module": "programs", "description": "Tạo, sửa, xóa chương trình đào tạo"},
        {"name": "Quản lý môn học", "code": "subject:manage", "module": "subjects", "description": "Tạo, sửa, xóa môn học"},
        {"name": "Quản lý lớp/phiên đào tạo", "code": "session:manage", "module": "sessions", "description": "Tạo, sửa, xóa phiên đào tạo"},
        # Quản lý khách hàng tư vấn (Leads - S2-08 -> S2-11)
        {"name": "Xem danh sách tư vấn", "code": "lead:read", "module": "leads", "description": "Xem danh sách và chi tiết yêu cầu tư vấn"},
        {"name": "Quản lý tư vấn", "code": "lead:manage", "module": "leads", "description": "Cập nhật trạng thái và ghi chú tư vấn"},
        {"name": "Phân công tư vấn", "code": "lead:assign", "module": "leads", "description": "Phân công chuyên viên phụ trách tư vấn"},
        # Báo cáo
        {"name": "Xem báo cáo", "code": "report:view", "module": "reports", "description": "Xem thống kê và báo cáo đào tạo"},
        # Menu điều hướng
        {"name": "Menu Quản trị", "code": "menu:admin", "module": "menu", "description": "Truy cập menu chức năng Quản trị"},
        {"name": "Menu Giảng viên", "code": "menu:trainer", "module": "menu", "description": "Truy cập menu chức năng Giảng viên"},
        {"name": "Menu Học viên", "code": "menu:trainee", "module": "menu", "description": "Truy cập menu chức năng Học viên"},
    ]

    existing_perms = {p.code: p for p in db.query(Permission).all()}
    for p_data in permissions_data:
        if p_data["code"] not in existing_perms:
            perm = Permission(**p_data)
            db.add(perm)
            existing_perms[p_data["code"]] = perm
    db.commit()

    # 2. Khởi tạo danh sách vai trò (Roles)
    role_admin = db.query(Role).filter(Role.name == "ADMIN").first()
    if not role_admin:
        role_admin = Role(name="ADMIN", description="Quản trị viên toàn quyền hệ thống")
        db.add(role_admin)
        db.commit()

    role_trainer = db.query(Role).filter(Role.name == "TRAINER").first()
    if not role_trainer:
        role_trainer = Role(name="TRAINER", description="Giảng viên / Chuyên viên đào tạo")
        db.add(role_trainer)
        db.commit()

    role_trainee = db.query(Role).filter(Role.name == "TRAINEE").first()
    if not role_trainee:
        role_trainee = Role(name="TRAINEE", description="Học viên tham gia đào tạo")
        db.add(role_trainee)
        db.commit()

    # 3. Gán quyền cho vai trò
    all_perms = db.query(Permission).all()
    # ADMIN nhận tất cả quyền
    role_admin.permissions = all_perms

    # TRAINER nhận quyền giảng dạy, đào tạo, báo cáo và menu trainer
    trainer_perm_codes = {
        "course:read", "course:manage", "program:manage", "subject:manage",
        "session:manage", "lead:read", "report:view", "menu:trainer"
    }
    role_trainer.permissions = [p for p in all_perms if p.code in trainer_perm_codes]

    # TRAINEE nhận quyền học tập và menu trainee
    trainee_perm_codes = {"course:read", "menu:trainee"}
    role_trainee.permissions = [p for p in all_perms if p.code in trainee_perm_codes]
    db.commit()


def seed_demo_users(db: Session):
    role_admin = db.query(Role).filter(Role.name == "ADMIN").first()
    role_trainee = db.query(Role).filter(Role.name == "TRAINEE").first()

    user_trainee = db.query(User).filter(User.email == "user@example.com").first()
    if not user_trainee:
        user_trainee = User(
            email="user@example.com",
            password_hash=hash_password("password123"),
            full_name="Nguyễn Văn A",
            is_active=True,
            is_locked=False,
            roles=[role_trainee] if role_trainee else [],
        )
        db.add(user_trainee)
    else:
        if role_trainee and role_trainee not in user_trainee.roles:
            user_trainee.roles.append(role_trainee)

    user_admin = db.query(User).filter(User.email == "admin@example.com").first()
    if not user_admin:
        user_admin = User(
            email="admin@example.com",
            password_hash=hash_password("password123"),
            full_name="Quản trị viên",
            is_active=True,
            is_locked=False,
            roles=[role_admin] if role_admin else [],
        )
        db.add(user_admin)
    else:
        if role_admin and role_admin not in user_admin.roles:
            user_admin.roles.append(role_admin)

    db.commit()


def seed_data(db: Session):
    seed_roles_and_permissions(db)
    seed_demo_users(db)
