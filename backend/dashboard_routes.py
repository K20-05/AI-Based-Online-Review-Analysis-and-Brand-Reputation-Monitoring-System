from __future__ import annotations

from flask import Blueprint


def create_dashboard_blueprint(deps: dict) -> Blueprint:
    bp = Blueprint("dashboard_routes", __name__)

    jsonify = deps["jsonify"]
    request = deps["request"]
    pd = deps["pd"]

    json_error = deps["json_error"]
    require_auth = deps["require_auth"]
    require_roles = deps["require_roles"]
    prediction_frame = deps["prediction_frame"]
    calculate_brand_score = deps["calculate_brand_score"]
    generate_visualizations = deps["generate_visualizations"]
    dashboard_brand_payload = deps["dashboard_brand_payload"]
    trend_brand_availability = deps["trend_brand_availability"]
    normalize_brand_key = deps["normalize_brand_key"]
    build_brand_insights = deps["build_brand_insights"]
    find_brand_row = deps["find_brand_row"]
    similar_brand_rows = deps["similar_brand_rows"]
    risk_profile = deps["risk_profile"]
    trend_counts_frame = deps["trend_counts_frame"]
    dashboard_keywords_payload = deps["dashboard_keywords_payload"]
    review_samples = deps["review_samples"]
    dashboard_data = deps["dashboard_data"]
    BRAND_REPUTATION_BY_BRAND_PATH = deps["BRAND_REPUTATION_BY_BRAND_PATH"]

    @bp.get("/api/dashboard/summary")
    @require_auth
    def dashboard_summary():
        return jsonify(dashboard_brand_payload())

    @bp.get("/api/dashboard/brands")
    @require_auth
    def dashboard_brands():
        if BRAND_REPUTATION_BY_BRAND_PATH.exists():
            df = pd.read_csv(BRAND_REPUTATION_BY_BRAND_PATH, low_memory=False)
            rows = df.to_dict(orient="records")
        else:
            payload = calculate_brand_score()
            rows = payload.get("brand_scores", [])

        availability = trend_brand_availability()
        normalized_rows = []
        for row in rows:
            next_row = dict(row)
            next_row["has_trend_data"] = bool(availability.get(normalize_brand_key(next_row.get("brand", "")), False))
            normalized_rows.append(next_row)
        return jsonify({"brands": normalized_rows})

    @bp.get("/api/dashboard/insights")
    @require_auth
    @require_roles("marketing_staff")
    def dashboard_insights():
        brand = str(request.args.get("brand", "")).strip()
        if not brand:
            return json_error("brand query parameter is required")
        return jsonify(build_brand_insights(find_brand_row(brand)))

    @bp.get("/api/dashboard/similar")
    @require_auth
    @require_roles("marketing_staff")
    def dashboard_similar():
        brand = str(request.args.get("brand", "")).strip()
        if not brand:
            return json_error("brand query parameter is required")
        limit = max(1, min(int(request.args.get("limit", 3) or 3), 10))
        row = find_brand_row(brand)
        return jsonify({"brand": row["brand"], "similar": similar_brand_rows(row, limit)})

    @bp.get("/api/dashboard/compare")
    @require_auth
    @require_roles("marketing_staff")
    def dashboard_compare():
        brand_a = str(request.args.get("brand_a", "")).strip()
        brand_b = str(request.args.get("brand_b", "")).strip()
        if not brand_a or not brand_b:
            return json_error("brand_a and brand_b query parameters are required")

        row_a = find_brand_row(brand_a)
        row_b = find_brand_row(brand_b)
        leader = row_a if row_a["brand_reputation_score"] >= row_b["brand_reputation_score"] else row_b
        lagger = row_b if leader is row_a else row_a
        summary = (
            f"{leader['brand']} leads on reputation score, while {lagger['brand']} needs more work on negative sentiment control and trust recovery."
        )
        return jsonify(
            {
                "brand_a": row_a,
                "brand_b": row_b,
                "risk_a": risk_profile(row_a["brand_reputation_score"], row_a["negative_pct"]),
                "risk_b": risk_profile(row_b["brand_reputation_score"], row_b["negative_pct"]),
                "summary": summary,
            }
        )

    @bp.get("/api/dashboard/trends")
    @require_auth
    @require_roles("analyst", "marketing_staff")
    def dashboard_trends():
        grouped = trend_counts_frame()
        brand_filter = str(request.args.get("brand", "")).strip()
        months = str(request.args.get("months", "all")).strip().lower() or "all"
        if grouped.empty:
            return jsonify({"trends": [], "brand": brand_filter or None})
        if brand_filter:
            normalized_brand = normalize_brand_key(brand_filter)
            grouped = grouped[grouped["brand_key"] == normalized_brand]
            if grouped.empty:
                return jsonify({"trends": [], "brand": brand_filter or None})

        period_grouped = (
            grouped.groupby(["period", "sentiment"])["count"]
            .sum()
            .unstack(fill_value=0)
            .sort_index()
        )
        if months != "all" and months.isdigit() and not period_grouped.empty:
            month_count = max(1, int(months))
            period_grouped = period_grouped.tail(month_count)
        trends = []
        for period, row in period_grouped.iterrows():
            trends.append(
                {
                    "period": period,
                    "Positive": int(row.get("Positive", 0)),
                    "Neutral": int(row.get("Neutral", 0)),
                    "Negative": int(row.get("Negative", 0)),
                }
            )
        return jsonify({"trends": trends, "brand": brand_filter or None})

    @bp.get("/api/dashboard/keywords")
    @require_auth
    def dashboard_keywords():
        brand = str(request.args.get("brand", "")).strip()
        months = str(request.args.get("months", "all")).strip() or "all"
        sentiment = str(request.args.get("sentiment", "")).strip()
        keywords = dashboard_keywords_payload(brand=brand, months=months, sentiment=sentiment)
        return jsonify({"keywords": keywords, "brand": brand or None, "months": months, "sentiment": sentiment or None})

    @bp.get("/api/dashboard/reviews")
    @require_auth
    @require_roles("analyst")
    def dashboard_review_samples():
        sentiment = str(request.args.get("sentiment", "")).strip()
        if not sentiment:
            return json_error("sentiment query parameter is required")
        brand = str(request.args.get("brand", "")).strip()
        months = str(request.args.get("months", "all")).strip() or "all"
        limit = max(1, min(int(request.args.get("limit", 5) or 5), 10))
        samples = review_samples(sentiment=sentiment, brand=brand, months=months, limit=limit)
        return jsonify({"sentiment": sentiment, "brand": brand or None, "months": months, "samples": samples})

    @bp.get("/api/dashboard/platforms")
    @require_auth
    @require_roles("analyst", "marketing_staff")
    def dashboard_platforms():
        return jsonify({"platforms": dashboard_data.platform_breakdown()})

    @bp.post("/api/dashboard/refresh")
    @require_auth
    @require_roles("admin", "analyst")
    def dashboard_refresh():
        df = prediction_frame()
        generate_visualizations(df)
        score = calculate_brand_score()
        return jsonify({"message": "Dashboard refreshed", "brand_score": score})

    return bp
