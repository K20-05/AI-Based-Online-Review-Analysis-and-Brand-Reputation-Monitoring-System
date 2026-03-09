from __future__ import annotations

from flask import Blueprint


def create_auth_blueprint(deps: dict) -> Blueprint:
    bp = Blueprint("auth_routes", __name__)

    jsonify = deps["jsonify"]
    request = deps["request"]
    session = deps["session"]
    UTC = deps["UTC"]
    datetime = deps["datetime"]
    check_password_hash = deps["check_password_hash"]
    generate_password_hash = deps["generate_password_hash"]

    json_success = deps["json_success"]
    json_error = deps["json_error"]
    load_user_store = deps["load_user_store"]
    save_user_store = deps["save_user_store"]
    find_user = deps["find_user"]
    current_user = deps["current_user"]
    serialize_user = deps["serialize_user"]
    normalize_public_role = deps["normalize_public_role"]
    validate_password_strength = deps["validate_password_strength"]

    @bp.get("/api/auth/session")
    def auth_session():
        user_email = current_user()
        user = find_user(user_email) if user_email else None
        return jsonify({"authenticated": bool(user_email), "user": serialize_user(user)})

    @bp.post("/api/auth/register")
    def auth_register():
        payload = request.get_json(force=True, silent=False) or {}
        name = str(payload.get("name", "")).strip()
        email = str(payload.get("email", "")).strip().lower()
        password = str(payload.get("password", ""))
        role = normalize_public_role(payload.get("role"))

        if not name or not email or not password:
            return json_error("name, email and password are required")
        if "@" not in email:
            return json_error("Enter a valid email address")
        password_error = validate_password_strength(password)
        if password_error:
            return json_error(password_error)
        if find_user(email):
            return json_error("An account with this email already exists", 409)

        users = load_user_store()
        users.append(
            {
                "name": name,
                "email": email,
                "password_hash": generate_password_hash(password),
                "role": role,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        save_user_store(users)
        return json_success("Account created", user=serialize_user(find_user(email)))

    @bp.post("/api/auth/login")
    def auth_login():
        payload = request.get_json(force=True, silent=False) or {}
        email = str(payload.get("email", "")).strip().lower()
        password = str(payload.get("password", ""))

        if not email or not password:
            return json_error("email and password are required")

        user = find_user(email)
        if not user or not check_password_hash(str(user.get("password_hash", "")), password):
            return json_error("Invalid email or password", 401)

        session["user_email"] = str(user.get("email", email))
        return json_success("Login successful", user=serialize_user(user))

    @bp.post("/api/auth/reset-password")
    def auth_reset_password():
        payload = request.get_json(force=True, silent=False) or {}
        email = str(payload.get("email", "")).strip().lower()
        new_password = str(payload.get("new_password", ""))

        if not email or not new_password:
            return json_error("email and new_password are required")
        password_error = validate_password_strength(new_password)
        if password_error:
            return json_error(password_error)

        users = load_user_store()
        updated = False
        for user in users:
            if str(user.get("email", "")).strip().lower() == email:
                user["password_hash"] = generate_password_hash(new_password)
                user["updated_at"] = datetime.now(UTC).isoformat()
                updated = True
                break

        if not updated:
            return json_error("No account found for this email", 404)

        save_user_store(users)
        return json_success("Password updated", user=serialize_user(find_user(email)))

    @bp.post("/api/auth/logout")
    def auth_logout():
        session.clear()
        return json_success("Logout successful")

    return bp
