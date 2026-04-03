import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_APP_PATH = ROOT_DIR / "frontend" / "app.js"
FRONTEND_RUNTIME_KEYWORDS_PATH = ROOT_DIR / "frontend" / "app-runtime-keywords.js"
FRONTEND_RUNTIME_CUSTOMER_VOICE_PATH = ROOT_DIR / "frontend" / "app-runtime-customer-voice.js"
FRONTEND_RUNTIME_SIGNALS_PATH = ROOT_DIR / "frontend" / "app-runtime-signals.js"
FRONTEND_RUNTIME_ANALYTICS_PATH = ROOT_DIR / "frontend" / "app-runtime-analytics.js"
FRONTEND_DASHBOARD_FRAGMENTS_PATH = ROOT_DIR / "frontend" / "app-dashboard-fragments.js"
FRONTEND_DASHBOARD_PATH = ROOT_DIR / "frontend" / "app-dashboard.js"
FRONTEND_DASHBOARD_OVERVIEW_PATH = ROOT_DIR / "frontend" / "app-dashboard-overview.js"
FRONTEND_DASHBOARD_PANELS_PATH = ROOT_DIR / "frontend" / "app-dashboard-panels.js"
FRONTEND_BRAND_WORKSPACE_PATH = ROOT_DIR / "frontend" / "app-brand-workspace.js"
FRONTEND_INDEX_PATH = ROOT_DIR / "frontend" / "index.html"
FRONTEND_PARTIALS_DIR = ROOT_DIR / "frontend" / "_partials"


def read_frontend_runtime_source():
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            FRONTEND_RUNTIME_KEYWORDS_PATH,
            FRONTEND_RUNTIME_CUSTOMER_VOICE_PATH,
            FRONTEND_RUNTIME_SIGNALS_PATH,
            FRONTEND_RUNTIME_ANALYTICS_PATH,
            FRONTEND_APP_PATH,
        )
    )


def read_frontend_dashboard_source():
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            FRONTEND_DASHBOARD_FRAGMENTS_PATH,
            FRONTEND_DASHBOARD_OVERVIEW_PATH,
            FRONTEND_DASHBOARD_PANELS_PATH,
            FRONTEND_DASHBOARD_PATH,
        )
    )


def read_frontend_markup_source():
    partial_paths = sorted(FRONTEND_PARTIALS_DIR.rglob("*.html"))
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in (FRONTEND_INDEX_PATH, *partial_paths)
    )


class FrontendDashboardContractTests(unittest.TestCase):
    def test_sentiment_distribution_view_refresh_hook_uses_canonical_view_name(self):
        source = read_frontend_runtime_source()

        self.assertIn('resolved === "sentiment-distribution"', source)
        self.assertNotIn('resolved === "sentiment-insights"', source)

    def test_role_dashboard_cards_escape_dynamic_content_and_support_prefilled_compare_pairs(self):
        source = read_frontend_dashboard_source()

        self.assertIn('const safeLabel = escapeHtml(String(item.label || ""));', source)
        self.assertIn('const safeValue = escapeHtml(String(item.value || ""));', source)
        self.assertIn('const safeCopy = escapeHtml(String(item.copy || ""));', source)
        self.assertIn('data-compare-a="', source)
        self.assertIn('data-compare-b="', source)
        self.assertIn('scrollTarget: "compareSummary"', source)

    def test_role_dashboard_navigation_prefills_brand_comparison(self):
        source = read_frontend_runtime_source()

        self.assertIn('const compareA = card.dataset.compareA || "";', source)
        self.assertIn('const compareB = card.dataset.compareB || "";', source)
        self.assertIn('if (view === "brand-insights" && (compareA || compareB)) {', source)
        self.assertIn("renderBrandComparison();", source)
        self.assertIn('const safeBrand = escapeHtml(String(item.brand || "Unknown brand"));', source)

    def test_dashboard_alert_eyebrow_is_role_aware(self):
        app_source = read_frontend_runtime_source()
        index_source = read_frontend_markup_source()

        self.assertIn('id="dashboardAlertEyebrow"', index_source)
        self.assertIn('const alertEyebrow = $("#dashboardAlertEyebrow");', app_source)
        self.assertIn('alertEyebrow.textContent = "Executive Note";', app_source)
        self.assertIn('alertEyebrow.textContent = "Market Note";', app_source)
        self.assertIn('alertEyebrow.textContent = "Analysis Note";', app_source)

    def test_dashboard_markup_includes_role_specific_overview_hooks(self):
        index_source = read_frontend_markup_source()

        self.assertIn('id="dashboardNarrativeLabel"', index_source)
        self.assertIn('id="dashboardQuickRiskLabel"', index_source)
        self.assertIn('id="dashboardQuickTotalReviewsLabel"', index_source)
        self.assertIn('id="dashboardQuickPipelineLabel"', index_source)
        self.assertIn('id="dashboardQuickAlertsLabel"', index_source)
        self.assertIn('id="dashboardDisclosureEyebrow"', index_source)
        self.assertIn('id="dashboardDisclosureTitle"', index_source)
        self.assertIn('id="dashboardDisclosureHint"', index_source)
        self.assertIn('id="dashboardRiskLabel"', index_source)

    def test_dashboard_overview_copy_differs_for_marketing_and_analyst_roles(self):
        source = read_frontend_dashboard_source()

        self.assertIn('narrativeLabel: "Market Position"', source)
        self.assertIn('label: "Portfolio Reach"', source)
        self.assertIn('label: "Brand Leader"', source)
        self.assertIn('label: "Compare Ready"', source)
        self.assertIn('narrativeLabel: "Signal Watch"', source)
        self.assertIn('label: "Negative Share"', source)
        self.assertIn('label: "Trend Window"', source)
        self.assertIn('label: "Live Evidence"', source)
        self.assertIn('label: "Complaint Watch"', source)
        self.assertIn('liveTitle: "Latest brand mentions"', source)
        self.assertIn('liveTitle: "Latest review evidence"', source)
        self.assertIn('label: "System Status"', source)
        self.assertIn('label: "Portfolio Leader"', source)
        self.assertIn('label: "Signal Focus"', source)

    def test_dashboard_disclosure_copy_is_role_aware(self):
        source = read_frontend_runtime_source()

        self.assertIn('const previousRole = dashboardView?.getAttribute("data-role") || "";', source)
        self.assertIn('const disclosureEyebrow = $("#dashboardDisclosureEyebrow");', source)
        self.assertIn('disclosureEyebrow.textContent = "Market Monitor";', source)
        self.assertIn('disclosureTitle.textContent = "Brand leaderboard and early warnings";', source)
        self.assertIn('disclosureEyebrow.textContent = "Investigation Desk";', source)
        self.assertIn('disclosureTitle.textContent = "Diagnostic signals and quick analysis actions";', source)
        self.assertIn('if (previousRole !== resolved) dashboardDisclosure.open = true;', source)

    def test_api_client_prefers_real_http_errors_over_cross_host_401_fallbacks(self):
        source = read_frontend_runtime_source()

        self.assertIn("function pickPreferredHttpError(currentError, nextError) {", source)
        self.assertIn('if (currentStatus && currentStatus !== 401 && nextStatus === 401) return currentError;', source)
        self.assertIn('if (nextStatus && nextStatus !== 401 && currentStatus === 401) return nextError;', source)
        self.assertIn("let bestHttpError = null;", source)
        self.assertIn("bestHttpError = pickPreferredHttpError(bestHttpError, httpError);", source)
        self.assertIn("if (bestHttpError) {", source)
        self.assertIn("throw bestHttpError;", source)

    def test_toast_renderer_uses_text_nodes_instead_of_inner_html(self):
        source = read_frontend_runtime_source()

        self.assertIn('const titleEl = document.createElement("strong");', source)
        self.assertIn('const bodyEl = document.createElement("p");', source)
        self.assertIn("titleEl.textContent = type;", source)
        self.assertIn("bodyEl.textContent = message;", source)
        self.assertNotIn('toastEl.innerHTML = "<strong>" + type + "</strong><p>" + message + "</p>";', source)

    def test_brand_workspace_requests_are_guarded_by_role_access(self):
        source = FRONTEND_BRAND_WORKSPACE_PATH.read_text(encoding="utf-8")

        self.assertIn("function canAccessBrandWorkspace(role = state.userRole) {", source)
        self.assertIn('return resolved === "admin" || resolved === "marketing_staff";', source)
        self.assertIn('clearBrandInsights("Brand intelligence is available in the marketing workspace.");', source)
        self.assertIn('clearBrandComparison("Brand comparison is available in the marketing workspace.");', source)
        self.assertIn("const canOpenBrandWorkspace = canAccessBrandWorkspace();", source)
        self.assertIn("if (canOpenBrandWorkspace) {", source)

    def test_auth_errors_trigger_session_recheck_before_forcing_logout(self):
        source = read_frontend_runtime_source()

        self.assertIn("sessionRecheckPromise: null", source)
        self.assertIn("async function probeSessionState(timeoutMs = 5000) {", source)
        self.assertIn('cache: "no-store"', source)
        self.assertIn("async function confirmSessionStillValid(fallbackMessage) {", source)
        self.assertIn("const sessionState = await probeSessionState();", source)
        self.assertIn("confirmSessionStillValid(fallbackMessage).catch(() => {});", source)
        self.assertNotIn('clearSessionUi();\n        showLogin(fallbackMessage || "Your session expired. Sign in again to continue.");', source)

    def test_batch_workspace_hides_empty_summary_cards_and_uses_clean_placeholder_copy(self):
        markup_source = read_frontend_markup_source()
        runtime_source = read_frontend_runtime_source()

        self.assertIn('id="batchLayout"', markup_source)
        self.assertIn('class="batch-layout batch-layout--solo"', markup_source)
        self.assertIn('id="batchSidebar"', markup_source)
        self.assertIn('class="batch-sidebar hidden"', markup_source)
        self.assertIn("डिलीवरी बहुत लेट हुई", markup_source)
        self.assertIn("மிகவும் மோசம்", markup_source)
        self.assertIn("చాలా చెడు", markup_source)
        self.assertIn("Hindi, Tamil, and Telugu sample reviews are shown here.", markup_source)
        self.assertIn("function setBatchSummaryVisibility(visible) {", runtime_source)
        self.assertIn('layout.classList.toggle("batch-layout--solo", !visible);', runtime_source)
        self.assertIn('sidebar.classList.toggle("hidden", !visible);', runtime_source)

    def test_dashboard_command_strip_uses_status_snapshot_instead_of_complaint_risk(self):
        markup_source = read_frontend_markup_source()
        dashboard_source = read_frontend_dashboard_source()

        self.assertIn("Status Snapshot", markup_source)
        self.assertNotIn("Complaint Risk", markup_source)
        self.assertIn("function dashboardStatusPillModel(context = {}) {", dashboard_source)
        self.assertIn('return "dashboard-status-pill dashboard-status-pill--spotlight is-" + (resolvedTone || "waiting");', dashboard_source)

    def test_analyst_role_cards_use_navigation_titles_instead_of_repeating_live_metrics(self):
        dashboard_source = read_frontend_dashboard_source()

        self.assertIn('label: "Trend Desk"', dashboard_source)
        self.assertIn('value: "Review Trends"', dashboard_source)
        self.assertIn('label: "Keyword Map"', dashboard_source)
        self.assertIn('value: "Sentiment Insights"', dashboard_source)
        self.assertIn('label: "Voice Board"', dashboard_source)
        self.assertIn('value: "Customer Voice"', dashboard_source)
        self.assertIn('label: "Review Queue"', dashboard_source)
        self.assertIn('value: "Evidence Feed"', dashboard_source)


if __name__ == "__main__":
    unittest.main()
