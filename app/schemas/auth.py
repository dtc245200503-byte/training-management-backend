import re
from pydantic import BaseModel, Field, validator


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, description="Mật khẩu hiện tại")
    new_password: str = Field(..., min_length=8, description="Mật khẩu mới (tối thiểu 8 ký tự)")
    confirm_password: str = Field(..., description="Xác nhận mật khẩu mới")
    refresh_token: str = Field(..., description="Refresh token của phiên hiện tại")

    @validator('new_password')
    def validate_new_password(cls, value):
        # Kiểm tra chứa ít nhất 1 chữ cái và 1 chữ số
        if not re.search(r"[a-zA-Z]", value) or not re.search(r"[0-9]", value):
            raise ValueError('Mật khẩu mới phải bao gồm cả chữ cái và chữ số')
        return value

    @validator('confirm_password')
    def validate_passwords_match(cls, value, values):
        # Kiểm tra confirm_password có khớp với new_password không
        if 'new_password' in values and value != values['new_password']:
            raise ValueError('Mật khẩu xác nhận không trùng khớp với mật khẩu mới')
        return value

    @validator('new_password')
    def validate_new_password(cls, value):
        # Kiểm tra chứa chữ hoa, chữ thường, chữ số và ký tự đặc biệt
        if (
            not re.search(r"[A-Z]", value)
            or not re.search(r"[a-z]", value)
            or not re.search(r"[0-9]", value)
            or not re.search(r"[@$!%*?&]", value)
        ):
            raise ValueError('Mật khẩu mới phải bao gồm chữ hoa, chữ thường, chữ số và ký tự đặc biệt (@, $, !,...)')
        return value