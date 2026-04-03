async function refreshDashboardAnalyticsSupplementary(role, options = {}) {
  const sessionRevision = Number.isFinite(Number(options.sessionRevision)) ? Number(options.sessionRevision) : state.sessionRevision;
  const requestSeq = Number.isFinite(Number(options.requestSeq)) ? Number(options.requestSeq) : state.dashboardAnalyticsRequestSeq;
  await refreshDashboardKeywordGroups({ sessionRevision, timeoutMs: 90000 });
  if (!sameSessionRevision(sessionRevision) || requestSeq !== state.dashboardAnalyticsRequestSeq) return;

  if (canLoadCustomerVoiceKeywords()) {
    refreshCustomerVoiceKeywords();
  }
  renderDashboardAnalyticsState();

  try {
    await refreshTrendView();
  } catch (trendError) {
    if (!sameSessionRevision(sessionRevision) || requestSeq !== state.dashboardAnalyticsRequestSeq) return;
    if (handleAuthError(trendError)) return;
    $("#trendCaption").textContent = "Unable to load trend graph: " + (trendError.message || "request failed") + ".";
  }

  if (!sameSessionRevision(sessionRevision) || requestSeq !== state.dashboardAnalyticsRequestSeq) return;
  renderAnalyticsSummaryContext();
  renderRoleDashboardPanel();
}

async function refreshDashboardAnalytics(options = {}) {
  const role = normalizeAccessRole(state.userRole);
  const sessionRevision = Number.isFinite(Number(options.sessionRevision)) ? Number(options.sessionRevision) : state.sessionRevision;
  const requestSeq = Number.isFinite(Number(options.requestSeq)) ? Number(options.requestSeq) : state.dashboardAnalyticsRequestSeq;
  try {
    const brandsRequest = callApi("/dashboard/brands?include_trend_availability=1", { timeoutMs: 35000 });
    const optionalRequest = role === "admin"
      ? callApi("/admin/model-performance")
      : (role === "marketing_staff" || role === "analyst")
        ? callApi("/dashboard/platforms")
        : Promise.resolve(null);
    const [brandsResult, optionalResult] = await Promise.allSettled([brandsRequest, optionalRequest]);
    if (!sameSessionRevision(sessionRevision) || requestSeq !== state.dashboardAnalyticsRequestSeq) return;
    if (brandsResult.status === "fulfilled") {
      state.brands = Array.isArray(brandsResult.value.brands) ? brandsResult.value.brands.map(normalizeBrandRow) : state.brands;
    } else if (!state.brands.length) {
      throw brandsResult.reason;
    }
    if (role === "admin") {
      if (optionalResult.status === "fulfilled") {
        state.modelMetrics = optionalResult.value && optionalResult.value.metrics ? optionalResult.value.metrics : null;
        state.modelTrainingAt = optionalResult.value && optionalResult.value.last_training_at ? optionalResult.value.last_training_at : "";
      }
      state.platforms = [];
      renderAdminModelPerformance();
      renderAdminControlHub();
      renderAdminOps();
      renderAdminSidePanel();
    } else if (optionalResult.status === "fulfilled") {
      state.platforms = optionalResult.value && Array.isArray(optionalResult.value.platforms) ? optionalResult.value.platforms : [];
    }

    renderDashboardAnalyticsState();
    refreshDashboardAnalyticsSupplementary(role, { sessionRevision, requestSeq }).catch(() => {});
  } catch (error) {
    if (!sameSessionRevision(sessionRevision) || requestSeq !== state.dashboardAnalyticsRequestSeq) return;
    if (handleAuthError(error)) return;
    state.platforms = [];
    state.modelMetrics = null;
    state.modelTrainingAt = "";
    state.customerVoiceKeywords = [];
    state.customerVoiceKeywordCache = {};
    state.customerVoiceKeywordsError = "";
    state.customerVoiceKeywordsFallback = false;
    state.customerVoiceKeywordsLoading = false;
    state.dashboardKeywordsError = error.message || "Unable to load sentiment keyword groups.";
    $("#trendCaption").textContent = "Unable to load trend graph: " + (error.message || "request failed") + ".";
    $("#keywordList").innerHTML = '<div class="keyword-caption">Unable to load keyword chart.</div>';
    $("#compareSummary").textContent = "Unable to load brand comparison data.";
    $("#similarBrandList").innerHTML = '<div class="mini-note">Unable to load similar brand data.</div>';
    renderDashboardAnalyticsState();
  }
}
