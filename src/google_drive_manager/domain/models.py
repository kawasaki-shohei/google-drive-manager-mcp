from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class PermissionRole(str, Enum):
    READER = "reader"
    COMMENTER = "commenter"
    WRITER = "writer"
    OWNER = "owner"


class PermissionType(str, Enum):
    USER = "user"
    GROUP = "group"
    DOMAIN = "domain"
    ANYONE = "anyone"


@dataclass(frozen=True)
class DriveFile:
    id: str
    name: str
    mime_type: str
    size: int | None
    parents: tuple[str, ...]
    created_time: datetime | None
    modified_time: datetime | None
    web_view_link: str | None


@dataclass(frozen=True)
class Permission:
    id: str
    type: PermissionType
    role: PermissionRole
    email_address: str | None
    display_name: str | None
