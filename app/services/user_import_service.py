from io import BytesIO
import os
import re
from typing import List, Optional
from fastapi import HTTPException, UploadFile, status
import openpyxl
from sqlalchemy.orm import Session
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.excel_import import UserImportErrorDetail, UserImportResult
from app.security.password import hash_password

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


class UserImportService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)

    def import_users_from_excel(self, file: UploadFile) -> UserImportResult:
        # 1. Kiểm tra phần mở rộng file Excel
        filename = file.filename or ""
        ext = os.path.splitext(filename)[1].lower()
        if ext not in {".xlsx", ".xls"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Định dạng file không được hỗ trợ ({ext}). Vui lòng tải lên file Excel (.xlsx hoặc .xls).",
            )

        content = file.file.read()
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File Excel tải lên không có dữ liệu.",
            )

        try:
            workbook = openpyxl.load_workbook(BytesIO(content), data_only=True)
            sheet = workbook.active
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Không thể đọc nội dung file Excel. Vui lòng kiểm tra lại tính hợp lệ của file: {str(e)}",
            )

        if not sheet:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sheet làm việc trong file Excel không tồn tại.",
            )

        # 2. Đọc dòng tiêu đề (Header row)
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File Excel không có bất kỳ dòng dữ liệu nào.",
            )

        header_row = rows[0]
        col_mapping = {}
        for idx, col_val in enumerate(header_row):
            if col_val is not None:
                norm_key = str(col_val).strip().lower()
                if norm_key in {"email", "e-mail"}:
                    col_mapping["email"] = idx
                elif norm_key in {"full_name", "fullname", "họ và tên", "ho và ten", "tên", "name"}:
                    col_mapping["full_name"] = idx
                elif norm_key in {"password", "mật khẩu", "mat khau"}:
                    col_mapping["password"] = idx
                elif norm_key in {"role", "roles", "vai trò", "vai tro"}:
                    col_mapping["roles"] = idx
                elif norm_key in {"phone", "phone_number", "số điện thoại", "so dien thoai"}:
                    col_mapping["phone_number"] = idx

        if "email" not in col_mapping:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File Excel thiếu cột bắt buộc: 'email'.",
            )

        # 3. Lấy cache danh sách vai trò có trong hệ thống
        available_roles = {r.name.upper(): r for r in self.role_repo.get_all()}
        default_trainee_role = available_roles.get("TRAINEE")

        imported_users: List[str] = []
        errors: List[UserImportErrorDetail] = []
        seen_emails_in_batch = set()

        data_rows = rows[1:]
        total_data_rows = len(data_rows)

        for row_idx, row_values in enumerate(data_rows, start=2):
            # Bỏ qua nếu cả dòng rỗng
            if not any(v is not None and str(v).strip() != "" for v in row_values):
                continue

            raw_email = row_values[col_mapping["email"]] if col_mapping.get("email") < len(row_values) else None
            email_str = str(raw_email).strip().lower() if raw_email else ""

            # Validate email
            if not email_str or not EMAIL_REGEX.match(email_str):
                errors.append(
                    UserImportErrorDetail(
                        row=row_idx,
                        email=email_str or None,
                        reason="Email không hợp lệ hoặc để trống.",
                    )
                )
                continue

            # Kiểm tra trùng lặp ngay trong file import
            if email_str in seen_emails_in_batch:
                errors.append(
                    UserImportErrorDetail(
                        row=row_idx,
                        email=email_str,
                        reason="Email bị trùng lặp trong chính file import.",
                    )
                )
                continue
            seen_emails_in_batch.add(email_str)

            # Kiểm tra email đã tồn tại trong database
            if self.user_repo.get_by_email(email_str):
                errors.append(
                    UserImportErrorDetail(
                        row=row_idx,
                        email=email_str,
                        reason="Email đã tồn tại trên hệ thống.",
                    )
                )
                continue

            # Full name
            raw_name = None
            if "full_name" in col_mapping and col_mapping["full_name"] < len(row_values):
                raw_name = row_values[col_mapping["full_name"]]
            full_name = str(raw_name).strip() if raw_name else None

            # Password (mặc định 'password123' nếu không chỉ định cột mật khẩu)
            raw_pw = None
            if "password" in col_mapping and col_mapping["password"] < len(row_values):
                raw_pw = row_values[col_mapping["password"]]
            password_str = str(raw_pw).strip() if raw_pw else "password123"

            if len(password_str) < 6:
                errors.append(
                    UserImportErrorDetail(
                        row=row_idx,
                        email=email_str,
                        reason="Mật khẩu phải có tối thiểu 6 ký tự.",
                    )
                )
                continue

            # Phone number
            raw_phone = None
            if "phone_number" in col_mapping and col_mapping["phone_number"] < len(row_values):
                raw_phone = row_values[col_mapping["phone_number"]]
            phone_str = str(raw_phone).strip() if raw_phone else None

            # Roles
            raw_role = None
            if "roles" in col_mapping and col_mapping["roles"] < len(row_values):
                raw_role = row_values[col_mapping["roles"]]

            user_roles_to_assign = []
            if raw_role:
                role_tokens = [t.strip().upper() for t in str(raw_role).replace(";", ",").split(",") if t.strip()]
                invalid_role_found = False
                for r_token in role_tokens:
                    if r_token in available_roles:
                        user_roles_to_assign.append(available_roles[r_token])
                    else:
                        errors.append(
                            UserImportErrorDetail(
                                row=row_idx,
                                email=email_str,
                                reason=f"Vai trò '{r_token}' không tồn tại trong hệ thống.",
                            )
                        )
                        invalid_role_found = True
                        break
                if invalid_role_found:
                    continue
            else:
                if default_trainee_role:
                    user_roles_to_assign.append(default_trainee_role)

            # Tạo người dùng mới an toàn
            new_user = User(
                email=email_str,
                password_hash=hash_password(password_str),
                full_name=full_name,
                phone_number=phone_str,
                is_active=True,
                is_locked=False,
                roles=user_roles_to_assign,
            )
            self.user_repo.create(new_user)
            imported_users.append(email_str)

        return UserImportResult(
            total_rows=total_data_rows,
            imported_count=len(imported_users),
            skipped_count=len(errors),
            success_count=len(imported_users),
            failed_count=len(errors),
            errors=errors,
            imported_users=imported_users,
            imported_emails=imported_users,
        )
