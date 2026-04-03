from __future__ import annotations

from datetime import UTC, datetime
from functools import wraps
import json
from pathlib import Path
import re

from flask import g, session


USER_STORE_CACHE = {
    "signature": None,
    "users": [],
    "index": {},
}


def session_user_email() -> str | None:
    email = str(session.get("user_email", "")).strip().lower()
    return email or None


def current_user(current_user_record_func) -> str | None:
    user = current_user_record_func()
    if not user:
        return None
    return str(user.get("email", "")).strip().lower() or None


def current_user_record(find_user_func):
    if getattr(g, "_brandpulse_current_user_loaded", False):
        return getattr(g, "_brandpulse_current_user_record", None)
    user_email = session_user_email()
    if not user_email:
        g._brandpulse_current_user_loaded = True
        g._brandpulse_current_user_record = None
        return None
    user = find_user_func(user_email)
    if user:
        g._brandpulse_current_user_loaded = True
        g._brandpulse_current_user_record = user
        return user
    session.pop("user_email", None)
    g._brandpulse_current_user_loaded = True
    g._brandpulse_current_user_record = None
    return None


def current_user_role(current_user_record_func) -> str:
    user = current_user_record_func()
    if not user:
        return ""
    normalized = str(user.get("role", "")).strip().lower()
    if normalized == "user":
        return "analyst"
    return normalized


def can_seed_dashboard_admin(
    admin_email: str,
    admin_password: str,
    is_insecure_admin_password,
    password_validator,
) -> bool:
    password = admin_password
    return (
        bool(admin_email.strip())
        and bool(password)
        and not is_insecure_admin_password(password)
        and password_validator(password) is None
    )


def user_store_signature(user_store_path: Path) -> tuple[str, int, int]:
    resolved = str(user_store_path.resolve())
    if not user_store_path.exists():
        return (resolved, 0, 0)
    stats = user_store_path.stat()
    return (resolved, int(stats.st_mtime_ns), int(stats.st_size))


def clone_users(users: list[dict]) -> list[dict]:
    return [dict(user) for user in users if isinstance(user, dict)]


def user_index(users: list[dict]) -> dict[str, dict]:
    index = {}
    for user in users:
        email = str(user.get("email", "")).strip().lower()
        if email:
            index[email] = dict(user)
    return index


def update_user_store_cache(
    users: list[dict],
    user_store_path: Path,
    signature: tuple[str, int, int] | None = None,
) -> None:
    normalized_users = clone_users(users)
    USER_STORE_CACHE["signature"] = signature if signature is not None else user_store_signature(user_store_path)
    USER_STORE_CACHE["users"] = normalized_users
    USER_STORE_CACHE["index"] = user_index(normalized_users)


def cached_user_store_snapshot(user_store_path: Path, force_reload: bool = False) -> dict:
    signature = user_store_signature(user_store_path)
    if not force_reload and USER_STORE_CACHE["signature"] == signature:
        return USER_STORE_CACHE

    users = []
    if user_store_path.exists():
        try:
            payload = json.loads(user_store_path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                users = clone_users(payload)
        except (OSError, json.JSONDecodeError):
            users = []
    update_user_store_cache(users, user_store_path, signature)
    return USER_STORE_CACHE


def load_user_store(
    user_store_path: Path,
    admin_email: str,
    admin_password: str,
    password_hasher,
    is_insecure_admin_password,
    password_validator,
) -> list[dict]:
    snapshot = cached_user_store_snapshot(user_store_path)
    users = clone_users(snapshot["users"])

    normalized_admin_email = admin_email.strip().lower()
    if can_seed_dashboard_admin(
        admin_email,
        admin_password,
        is_insecure_admin_password,
        password_validator,
    ) and normalized_admin_email not in snapshot["index"]:
        users.append(
            {
                "name": "Administrator",
                "email": normalized_admin_email,
                "password_hash": password_hasher(admin_password),
                "role": "admin",
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        save_user_store(users, user_store_path)
        return load_user_store(
            user_store_path,
            admin_email,
            admin_password,
            password_hasher,
            is_insecure_admin_password,
            password_validator,
        )
    return users


def save_user_store(users: list[dict], user_store_path: Path) -> None:
    user_store_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_users = clone_users(users)
    user_store_path.write_text(json.dumps(normalized_users, indent=2), encoding="utf-8")
    update_user_store_cache(normalized_users, user_store_path)


def find_user(email: str, load_user_store_func) -> dict | None:
    email = email.strip().lower()
    if not email:
        return None
    load_user_store_func()
    user = USER_STORE_CACHE["index"].get(email)
    return dict(user) if user else None


def serialize_user(user: dict | None) -> dict | None:
    if not user:
        return None
    normalized_role = str(user.get("role", "")).strip().lower() or "analyst"
    if normalized_role == "user":
        normalized_role = "analyst"
    return {
        "name": str(user.get("name", "")).strip() or str(user.get("email", "")).strip(),
        "email": str(user.get("email", "")).strip().lower(),
        "role": normalized_role,
    }


def normalize_public_role(role: str | None) -> str:
    normalized = str(role or "").strip().lower()
    if normalized == "marketing_staff":
        return "marketing_staff"
    if normalized in {"admin", "user"}:
        return "analyst"
    return "analyst"


def validate_password_strength(password: str) -> str | None:
    if len(password) < 8:
        return "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return "Password must include at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return "Password must include at least one lowercase letter"
    if not re.search(r"\d", password):
        return "Password must include at least one number"
    if not re.search(r"[^A-Za-z0-9]", password):
        return "Password must include at least one special character"
    return None


def build_require_auth(current_user_record_func, json_error):
    def require_auth(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user_record_func():
                return json_error("Authentication required", 401)
            return view_func(*args, **kwargs)

        return wrapped

    return require_auth


def build_require_roles(current_user_record_func, current_user_role_func, json_error):
    def require_roles(*roles: str):
        allowed_roles = {str(role).strip().lower() for role in roles if str(role).strip()}

        def decorator(view_func):
            @wraps(view_func)
            def wrapped(*args, **kwargs):
                if not current_user_record_func():
                    return json_error("Authentication required", 401)
                active_role = current_user_role_func()
                if active_role == "admin":
                    return view_func(*args, **kwargs)
                if active_role not in allowed_roles:
                    return json_error("Access denied for this role", 403)
                return view_func(*args, **kwargs)

            return wrapped

        return decorator

    return require_roles
