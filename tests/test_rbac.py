from app.core.permissions import user_has_permission


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
    def __init__(self, allowed):
        self.allowed = allowed

    def query(self, *args, **kwargs):
        return FakeQuery(self.allowed)


def test_admin_has_role_manage_permission():
    db = FakeDB(True)

    result = user_has_permission(
        user_id=1,
        permission_name="ROLE_MANAGE",
        db=db
    )

    assert result is True


def test_instructor_has_grade_edit_permission():
    db = FakeDB(True)

    result = user_has_permission(
        user_id=2,
        permission_name="GRADE_EDIT",
        db=db
    )

    assert result is True


def test_accountant_has_tuition_edit_permission():
    db = FakeDB(True)

    result = user_has_permission(
        user_id=4,
        permission_name="TUITION_EDIT",
        db=db
    )

    assert result is True


def test_instructor_cannot_edit_tuition():
    db = FakeDB(False)

    result = user_has_permission(
        user_id=2,
        permission_name="TUITION_EDIT",
        db=db
    )

    assert result is False


def test_accountant_cannot_edit_grade():
    db = FakeDB(False)

    result = user_has_permission(
        user_id=4,
        permission_name="GRADE_EDIT",
        db=db
    )

    assert result is False