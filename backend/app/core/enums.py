from enum import StrEnum


class UserRole(StrEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MEMBER = "member"


class UserStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
