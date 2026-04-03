(function () {
  function createDashboardModule(deps) {
    const {
      $,
      renderGauge,
      updateDistributionChart,
      renderAnalystCustomerVoice,
      renderMarketingSignals,
      renderAdminOps,
      applyDashboardRolePresentation
    } = deps;

    const DashboardFragments = window.BrandPulseDashboardFragments;
    const DashboardOverview = window.BrandPulseDashboardOverview;
    const DashboardPanels = window.BrandPulseDashboardPanels;

    if (!DashboardFragments) {
      throw new Error("BrandPulse dashboard fragment helpers failed to load.");
    }

    if (!DashboardOverview) {
      throw new Error("BrandPulse dashboard overview helpers failed to load.");
    }

    if (!DashboardPanels) {
      throw new Error("BrandPulse dashboard panel helpers failed to load.");
    }

    const runtimeDeps = Object.assign({}, deps, DashboardFragments.createDashboardFragmentHelpers(deps));
    const overviewModule = DashboardOverview.createDashboardOverviewModule(runtimeDeps);
    const panelsModule = DashboardPanels.createDashboardPanelsModule(runtimeDeps);

    const {
      activeAdminAlertCount,
      renderDashboardOverview,
      renderDashboardRealtimeReviews,
      renderSignalRadar,
      updateDashboardAlerts
    } = overviewModule;

    const {
      renderComplaintTopics,
      renderBrandEarlyWarning,
      renderTrendMomentum,
      renderTrendMonthlyComparison,
      renderSummaryDeepIntelligence,
      applyAnalyticsSummaryPresentation,
      renderSmartInsight,
      renderTrendReviewVolume,
      renderRoleDashboardPanel,
      renderAnalystFocusPanel,
      openBrandFromRoleDashboard,
      setTrendDrilldownActive,
      prefetchTrendDrilldownSamples,
      loadTrendDrilldown,
      renderTrendChart
    } = panelsModule;

    function updateDashboard(score) {
      const sentimentMargin = Number(score.positive_pct || 0) - Number(score.negative_pct || 0);
      $("#statTotalReviews").textContent = score.total_reviews.toLocaleString();
      $("#statPositivePct").textContent = score.positive_pct.toFixed(2) + "%";
      $("#statNegativePct").textContent = score.negative_pct.toFixed(2) + "%";
      $("#statSentimentMargin").textContent = sentimentMargin.toFixed(1);
      $("#statRealtimeReviews").textContent = Number(runtimeDeps.state.realtimeSummary?.total_reviews || 0).toLocaleString();
      $("#statRealtimeUpdated").textContent = runtimeDeps.formatRealtimeTimestamp(runtimeDeps.state.realtimeSummary?.latest_ingested_at);
      const overviewModel = renderDashboardOverview(score);
      renderDashboardRealtimeReviews();

      const gaugeColor = score.brand_reputation_score >= 40
        ? "var(--positive)"
        : score.brand_reputation_score < 10
          ? "var(--negative)"
          : "var(--neutral)";

      renderGauge($("#brandGauge"), score.brand_reputation_score, {
        displayValue: score.brand_reputation_score.toFixed(1),
        label: overviewModel?.gaugeLabel || "Brand Reputation",
        suffix: "/100 score",
        caption: overviewModel?.gaugeCaption || "Current score from the latest `/dashboard/summary` response.",
        color: gaugeColor
      });
      updateDistributionChart(score);
      updateDashboardAlerts(score);
      renderAnalystCustomerVoice();
      renderAnalystFocusPanel();
      renderSmartInsight();
      runtimeDeps.renderAnalyticsSummaryContext();
      renderMarketingSignals();
      renderAdminOps();
      applyDashboardRolePresentation(runtimeDeps.state.userRole);
    }

    return {
      activeAdminAlertCount,
      renderDashboardOverview,
      renderDashboardRealtimeReviews,
      updateDashboard,
      renderSignalRadar,
      updateDashboardAlerts,
      renderComplaintTopics,
      renderBrandEarlyWarning,
      renderTrendMomentum,
      renderTrendMonthlyComparison,
      renderSummaryDeepIntelligence,
      applyAnalyticsSummaryPresentation,
      renderSmartInsight,
      renderTrendReviewVolume,
      renderRoleDashboardPanel,
      renderAnalystFocusPanel,
      openBrandFromRoleDashboard,
      setTrendDrilldownActive,
      prefetchTrendDrilldownSamples,
      loadTrendDrilldown,
      renderTrendChart
    };
  }

  window.BrandPulseDashboard = { createDashboardModule };
}());
