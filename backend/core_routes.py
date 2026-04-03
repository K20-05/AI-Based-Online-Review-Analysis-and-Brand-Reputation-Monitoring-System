from __future__ import annotations

from flask import Blueprint, make_response


def create_core_blueprint(deps: dict) -> Blueprint:
    bp = Blueprint("core_routes", __name__)

    jsonify = deps["jsonify"]
    render_template = deps["render_template"]
    request = deps["request"]
    send_file = deps["send_file"]
    pd = deps["pd"]

    API_DOCS = deps["API_DOCS"]
    MODEL_PATH = deps["MODEL_PATH"]
    VECTORIZER_PATH = deps["VECTORIZER_PATH"]
    PREDICTIONS_PATH = deps["PREDICTIONS_PATH"]
    MODEL_REPORT_PATH = deps["MODEL_REPORT_PATH"]
    REALTIME_REVIEWS_PATH = deps["REALTIME_REVIEWS_PATH"]
    USER_STORE_PATH = deps["USER_STORE_PATH"]
    LOGIN_ILLUSTRATION_PATH = deps["LOGIN_ILLUSTRATION_PATH"]

    mongo_enabled = deps["mongo_enabled"]
    json_success = deps["json_success"]
    json_error = deps["json_error"]
    require_auth = deps["require_auth"]
    require_roles = deps["require_roles"]
    preprocess_reviews = deps["preprocess_reviews"]
    build_feature_dataset = deps["build_feature_dataset"]
    train_models = deps["train_models"]
    parse_predict_payload = deps["parse_predict_payload"]
    predict_single_review = deps["predict_single_review"]
    predict_batch_reviews = deps["predict_batch_reviews"]
    load_model_artifacts = deps["load_model_artifacts"]
    predict_dataset = deps["predict_dataset"]
    calculate_brand_score = deps["calculate_brand_score"]
    ingest_realtime_reviews = deps["ingest_realtime_reviews"]
    realtime_review_summary = deps["realtime_review_summary"]
    list_connectors = deps["list_connectors"]
    poll_connector = deps["poll_connector"]
    scheduler_status = deps["scheduler_status"]
    update_scheduler_config = deps["update_scheduler_config"]
    start_background_services = deps["start_background_services"]

    def index_response():
        response = make_response(render_template("index.html"))
        response.cache_control.no_store = True
        response.cache_control.max_age = 0
        return response

    @bp.route("/")
    @bp.route("/index.html")
    def index():
        return index_response()

    @bp.get("/api/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "model_exists": MODEL_PATH.exists(),
                "vectorizer_exists": VECTORIZER_PATH.exists(),
                "predictions_exist": PREDICTIONS_PATH.exists(),
                "report_exists": MODEL_REPORT_PATH.exists(),
                "realtime_reviews_exist": REALTIME_REVIEWS_PATH.exists(),
                "user_store_exists": USER_STORE_PATH.exists(),
                "login_illustration_exists": LOGIN_ILLUSTRATION_PATH.exists(),
                "mongo_configured": mongo_enabled(),
            }
        )

    @bp.get("/api/assets/login-illustration")
    def login_illustration():
        if not LOGIN_ILLUSTRATION_PATH.exists():
            raise FileNotFoundError("Login illustration not found.")
        return send_file(LOGIN_ILLUSTRATION_PATH)

    @bp.get("/api/docs")
    def api_docs():
        return jsonify(API_DOCS)

    @bp.get("/api/openapi.json")
    def api_openapi():
        return jsonify(API_DOCS)

    @bp.post("/api/preprocess")
    @require_auth
    @require_roles("admin", "analyst")
    def preprocess_endpoint():
        df = preprocess_reviews()
        return json_success("Preprocessing completed", rows=int(len(df)))

    @bp.post("/api/features")
    @require_auth
    @require_roles("admin", "analyst")
    def feature_extraction_endpoint():
        df = build_feature_dataset()
        return json_success("Feature extraction completed", rows=int(len(df)))

    @bp.post("/api/train")
    @require_auth
    @require_roles("admin", "analyst")
    def train_endpoint():
        metrics = train_models()
        return json_success("Training completed", models=metrics.to_dict(orient="records"))

    @bp.post("/api/predict")
    @require_auth
    @require_roles("admin", "analyst")
    def predict_single():
        payload = request.get_json(force=True, silent=False) or {}
        request_data = parse_predict_payload(payload)
        response_payload = predict_single_review(request_data, load_model_artifacts)
        return jsonify({"success": True, **response_payload})

    @bp.post("/api/predict/batch")
    @require_auth
    @require_roles("admin", "analyst")
    def predict_batch():
        payload = request.get_json(force=True, silent=False) or {}
        reviews = payload.get("reviews") or []
        save_to_dataset = bool(payload.get("save_to_dataset"))

        if isinstance(reviews, list) and reviews and not save_to_dataset:
            response_payload = predict_batch_reviews(reviews, load_model_artifacts)
            return jsonify({"success": True, **response_payload})

        df = predict_dataset()
        score = calculate_brand_score()
        return json_success("Batch prediction completed", rows=int(len(df)), brand_score=score)

    @bp.post("/api/brand-score")
    @require_auth
    @require_roles("admin", "analyst")
    def brand_score_endpoint():
        payload = calculate_brand_score()
        return json_success("Brand scoring completed", brand_score=payload)

    @bp.post("/api/reviews/realtime")
    @require_auth
    @require_roles("admin", "analyst")
    def realtime_reviews_ingest():
        payload = request.get_json(force=True, silent=False) or {}
        reviews = payload.get("reviews")
        if not isinstance(reviews, list) or not reviews:
            single = payload if payload.get("review_text") else None
            reviews = [single] if single else []
        if not reviews:
            return json_error("Provide reviews as a non-empty list or a single review_text payload")

        df = ingest_realtime_reviews(reviews)
        return jsonify(
            {
                "success": True,
                "message": "Realtime reviews ingested",
                "rows": int(len(df)),
                "results": df.where(pd.notnull(df), None).to_dict(orient="records"),
                "summary": realtime_review_summary(),
            }
        )

    @bp.get("/api/connectors")
    @require_auth
    @require_roles("admin", "analyst")
    def connectors_list_endpoint():
        return jsonify({"connectors": list_connectors()})

    @bp.post("/api/connectors/poll")
    @require_auth
    @require_roles("admin", "analyst")
    def connectors_poll_endpoint():
        payload = request.get_json(force=True, silent=False) or {}
        connector_name = str(payload.get("connector", "")).strip()
        if not connector_name:
            return json_error("connector is required")

        limit = max(1, min(int(payload.get("limit", 20) or 20), 100))
        options = payload.get("options") if isinstance(payload.get("options"), dict) else {}
        reset_cursor = bool(payload.get("reset_cursor"))

        fetched = poll_connector(connector_name, limit=limit, options=options, reset_cursor=reset_cursor)
        reviews = fetched.get("reviews", [])
        if not reviews:
            return jsonify({"success": True, "message": "Connector poll completed with no new reviews", **fetched})

        ingested_df = ingest_realtime_reviews(reviews)
        return jsonify(
            {
                "success": True,
                "message": "Connector poll completed",
                **fetched,
                "ingested_rows": int(len(ingested_df)),
                "summary": realtime_review_summary(),
            }
        )

    @bp.get("/api/connectors/scheduler")
    @require_auth
    @require_roles("admin", "analyst")
    def connector_scheduler_status_endpoint():
        start_background_services(current_app.debug)
        return jsonify(scheduler_status())

    @bp.post("/api/connectors/scheduler")
    @require_auth
    @require_roles("admin", "analyst")
    def connector_scheduler_update_endpoint():
        start_background_services(current_app.debug)
        payload = request.get_json(force=True, silent=False) or {}
        return jsonify(
            {
                "success": True,
                "message": "Connector scheduler updated",
                **update_scheduler_config(payload),
            }
        )

    return bp
