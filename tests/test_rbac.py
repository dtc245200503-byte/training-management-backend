from app.core.permissions import user_has_permission


ROLE_PERMISSIONS = {
    1: {
        "USER_MANAGE",
        "ROLE_MANAGE",
        "COURSE_MANAGE",
        "CLASS_MANAGE",
        "GRADE_VIEW",
        "GRADE_EDIT",
        "TUITION_VIEW",
        "TUITION_EDIT",
        "ATTENDANCE_VIEW",
        "ATTENDANCE_EDIT",
    },
    2: {
        "COURSE_MANAGE",
        "CLASS_MANAGE",
        "GRADE_VIEW",
        "GRADE_EDIT",
        "ATTENDANCE_VIEW",
        "ATTENDANCE_EDIT",
    },
    3: {
        "GRADE_VIEW",
        "TUITION_VIEW",
        "ATTENDANCE_VIEW",
    },
    4: {
        "TUITION_VIEW",
        "TUITION_EDIT",
    },
}


class FakeQuery:
    def __init__(self, allowed):
        self.allowed = allowed

    def join(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        if self.allowed:
            return object()

        return None


class FakeDB:
    def __init__(self, user_id, permission_name):
        role_permissions = ROLE_PERMISSIONS.get(
            user_id,
            set()
        )

        self.allowed = (
            permission_name in role_permissions
        )

    def query(self, *args, **kwargs):
        return FakeQuery(self.allowed)


def check_permission(
    user_id: int,
    permission_name: str
):
    db = FakeDB(
        user_id,
        permission_name
    )

    return user_has_permission(
        user_id=user_id,
        permission_name=permission_name,
        db=db
    )


def test_admin_has_role_manage_permission():
    assert check_permission(
        1,
        "ROLE_MANAGE"
    ) is True


def test_instructor_can_edit_grade():
    assert check_permission(
        2,
        "GRADE_EDIT"
    ) is True


def test_instructor_cannot_edit_tuition():
    assert check_permission(
        2,
        "TUITION_EDIT"
    ) is False


def test_student_can_view_grade():
    assert check_permission(
        3,
        "GRADE_VIEW"
    ) is True


def test_student_cannot_edit_grade():
    assert check_permission(
        3,
        "GRADE_EDIT"
    ) is False


def test_accountant_can_edit_tuition():
    assert check_permission(
        4,
        "TUITION_EDIT"
    ) is True


def test_accountant_cannot_edit_grade():
    assert check_permission(
        4,
        "GRADE_EDIT"
    ) is False