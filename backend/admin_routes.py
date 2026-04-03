from __future__ import annotations

from flask import Blueprint


def create_admin_blueprint(deps: dict) -> Blueprint:
    bp = Blueprint("admin_routes", __name__)

    jsonify = deps["jsonify"]
    request = deps["request"]
    pd = deps["pd"]
    UTC = deps["UTC"]
    datetime = deps["datetime"]

    json_success = deps["json_success"]
    json_error = deps["json_error"]
    load_user_store = deps["load_user_store"]
    save_user_store = deps["save_user_store"]
    current_user = deps["current_user"]
    serialize_user = deps["serialize_user"]
    normalize_public_role = deps["normalize_public_role"]
    require_auth = deps["require_auth"]
    require_roles = deps["require_roles"]
    MODEL_METRICS_PATH = deps["MODEL_METRICS_PATH"]
    DASHBOARD_ADMIN_EMAIL = deps["DASHBOARD_ADMIN_EMAIL"]

    @bp.get("/api/admin/users")
    @require_auth
    @require_roles("admin")
    def admin_users():
        def display_role(role_value: str) -> str:
            normalized_role = str(role_value or "").strip().lower()
            if normalized_role == "admin":
                return "admin"
            return normalize_public_role(normalized_role)

        current_email = str(current_user() or "").strip().lower()
        protected_admin = DASHBOARD_ADMIN_EMAIL.strip().lower()
        users = []
        for record in load_user_store():
            serialized = serialize_user(record)
            if not serialized:
                continue
            email = str(serialized.get("email", "")).strip().lower()
            role = str(serialized.get("role", "analyst")).strip().lower()
            users.append(
                {
                    **serialized,
                    "role": display_role(role),
                    "is_self": email == current_email,
                    "is_protected": email == protected_admin or role == "admin",
                }
            )
        users.sort(key=lambda row: (not row["is_protected"], row["email"]))
        return jsonify({"users": users})

    @bp.post("/api/admin/users/role")
    @require_auth
    @require_roles("admin")
    def admin_update_user_role():
        payload = request.get_json(force=True, silent=False) or {}
        email = str(payload.get("email", "")).strip().lower()
        role = normalize_public_role(payload.get("role"))
        if not email:
            return json_error("email is required")
        if role not in {"analyst", "marketing_staff"}:
            return json_error("role must be analyst or marketing_staff")

        protected_admin = DASHBOARD_ADMIN_EMAIL.strip().lower()
        current_email = str(current_user() or "").strip().lower()
        if email == protected_admin:
            return json_error("Protected admin account cannot be modified", 403)
        if email == current_email:
            return json_error("You cannot modify your own role", 403)

        users = load_user_store()
        target = None
        for user in users:
            if str(user.get("email", "")).strip().lower() == email:
                user["role"] = role
                target = user
                break
        if not target:
            return json_error("User not found", 404)

        save_user_store(users)
        return json_success("User role updated", user=serialize_user(target))

    @bp.post("/api/admin/users/delete")
    @require_auth
    @require_roles("admin")
    def admin_delete_user():
        payload = request.get_json(force=True, silent=False) or {}
        email = str(payload.get("email", "")).strip().lower()
        if not email:
            return json_error("email is required")
        if email == str(DASHBOARD_ADMIN_EMAIL).strip().lower():
            return json_error("Primary admin account cannot be deleted", 403)
        if email == str(current_user() or "").strip().lower():
            return json_error("You cannot delete your own account", 403)

        users = load_user_store()
        filtered = [user for user in users if str(user.get("email", "")).strip().lower() != email]
        if len(filtered) == len(users):
            return json_error("User not found", 404)

        save_user_store(filtered)
        return json_success("User deleted", email=email)

    @bp.get("/api/admin/model-performance")
    @require_auth
    @require_roles("admin")
    def admin_model_performance():
        metrics = {}
        if MODEL_METRICS_PATH.exists():
            df = pd.read_csv(MODEL_METRICS_PATH)
            if not df.empty:
                row = df.iloc[0].to_dict()
                metrics = {
                    "model": str(row.get("model", "Unavailable")),
                    "validation_accuracy": float(row.get("validation_accuracy", 0.0) or 0.0),
                    "validation_f1_macro": float(row.get("validation_f1_macro", 0.0) or 0.0),
                    "train_accuracy": float(row.get("train_accuracy", 0.0) or 0.0),
                    "test_accuracy": float(row.get("accuracy", 0.0) or 0.0),
                    "train_f1_macro": float(row.get("train_f1_macro", 0.0) or 0.0),
                    "test_f1_macro": float(row.get("f1_macro", 0.0) or 0.0),
                    "train_log_loss": float(row.get("train_log_loss", 0.0) or 0.0),
                    "test_log_loss": float(row.get("log_loss", 0.0) or 0.0),
                }
        last_training_at = None
        if MODEL_METRICS_PATH.exists():
            last_training_at = datetime.fromtimestamp(MODEL_METRICS_PATH.stat().st_mtime, UTC).isoformat()
        return jsonify({"metrics": metrics, "last_training_at": last_training_at})

    return bp
