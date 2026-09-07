"""Strict Core role→permission matrix tests (no FastAPI/Qdrant import)."""
from app.models.auth import User, UserRole, Permission, user_has_permission


def _user(role: UserRole) -> User:
    return User(
        id="u1",
        user_id="u1",
        email=f"{role.value}@airc.edu.vn",
        full_name="Test",
        role=role,
        is_active=True,
    )


def test_student_can_chat():
    assert user_has_permission(_user(UserRole.STUDENT), Permission.CHAT_USE)


def test_student_cannot_view_analytics():
    assert not user_has_permission(_user(UserRole.STUDENT), Permission.ANALYTICS_VIEW)


def test_teacher_can_view_analytics():
    assert user_has_permission(_user(UserRole.TEACHER), Permission.ANALYTICS_VIEW)


def test_teacher_cannot_manage_any_chatbot():
    assert not user_has_permission(_user(UserRole.TEACHER), Permission.CHATBOTS_MANAGE_ANY)


def test_admin_has_all_permissions():
    assert user_has_permission(_user(UserRole.ADMIN), Permission.SYSTEM_MANAGE)
    assert user_has_permission(_user(UserRole.ADMIN), Permission.CHAT_USE)
