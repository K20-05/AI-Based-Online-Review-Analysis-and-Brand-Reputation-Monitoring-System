const BrandPulseShared = window.BrandPulseShared;
const BrandPulseDashboard = window.BrandPulseDashboard;
const BrandPulseBrandWorkspace = window.BrandPulseBrandWorkspace;

if (!BrandPulseShared) {
  throw new Error("BrandPulse shared frontend helpers failed to load.");
}

if (!BrandPulseDashboard) {
  throw new Error("BrandPulse dashboard frontend helpers failed to load.");
}

if (!BrandPulseBrandWorkspace) {
  throw new Error("BrandPulse brand workspace frontend helpers failed to load.");
}

const {
  HISTORY_KEY,
  WATCHLIST_KEY,
  ROLE_ACCESS,
  ROLE_NAV_GROUPS,
  ROLE_DEFAULT_VIEW,
  ROLE_NAV_LABELS,
  WORKSPACE_SIGNAL_VIEWS,
  RANDOM_REVIEW_FALLBACKS,
  $,
  $$,
  on,
  onAll,
  clamp,
  storageRead,
  storageWrite,
  emptyBrandScore,
  emptyRealtimeSummary,
  normalizeStorageScope,
  sessionStorageIdentityForUser,
  normalizeReviewLookup,
  normalizeReviewSample,
  humanizeRole,
  normalizeAccessRole,
  allowedViewsForRole,
  defaultViewForRole,
  canonicalView,
  normalizeSessionUser,
  sessionInitials
} = BrandPulseShared;

const state = {
  brandScore: emptyBrandScore(),
  latestSource: "No endpoint call yet",
  latestConfidence: null,
  latestSentiment: "Standby",
  trends: [],
  keywords: [],
  keywordGroups: emptyKeywordGroups(),
  customerVoiceKeywords: [],
  customerVoiceKeywordCache: {},
  customerVoiceKeywordsError: "",
  customerVoiceKeywordsFallback: false,
  customerVoiceLastScopeKey: "",
  customerVoiceLastLoadedScopeKey: "",
  brands: [],
  users: [],
  usersLoaded: false,
  platforms: [],
  realtimeSummary: emptyRealtimeSummary(),
  latestRealtimeReviews: [],
  latestRealtimeReviewsMode: "empty",
  modelMetrics: null,
  modelTrainingAt: "",
  adminNotifications: [],
  trendDrilldownSentiment: "",
  trendReviewSamplesCache: {},
  watchlist: [],
  navButtons: null,
  openNavGroup: {},
  trendWindow: "all",
  trendBrand: "",
  customerVoiceWindow: "all",
  customerVoiceBrand: "",
  customerVoiceKeywordsLoading: false,
  dashboardKeywordsLoading: false,
  dashboardKeywordsError: "",
  trendDataLoading: false,
  customerVoiceRequestSeq: 0,
  dashboardKeywordRequestSeq: 0,
  trendRequestSeq: 0,
  userRole: "analyst",
  currentView: "dashboard",
  insightRequestSeq: 0,
  compareRequestSeq: 0,
  usersLoading: false,
  dashboardAutoRefreshTimer: null,
  dashboardAutoRefreshInFlight: false,
  dashboardRefreshRequestSeq: 0,
  dashboardAnalyticsRequestSeq: 0,
  apiPreferredBaseUrl: "",
  apiPreferredCandidates: {},
  storageScope: "guest",
  sessionRevision: 0,
  isAuthenticated: false,
  sessionRecheckPromise: null
};

let brandWorkspaceModule = null;

async function renderBrandInsights() {
  if (!brandWorkspaceModule) return;
  return brandWorkspaceModule.renderBrandInsights();
}

const {
  renderDashboardOverview,
  updateDashboard,
  renderSignalRadar,
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
} = BrandPulseDashboard.createDashboardModule({
  state,
  $,
  $$,
  normalizeAccessRole,
  normalizeBrandScore,
  formatRealtimeTimestamp,
  riskMeta,
  renderGauge,
  updateDistributionChart,
  renderAnalystCustomerVoice,
  renderMarketingSignals,
  renderAdminOps,
  applyDashboardRolePresentation,
  renderAnalyticsSummaryContext,
  renderPillList,
  customerVoiceWindowLabel,
  activeTrendBrandLabel,
  getScoreExtremes,
  getWindowedTrends,
  sentimentClass,
  escapeHtml,
  callApi,
  sameSessionRevision,
  handleAuthError,
  requestCustomerVoiceKeywordsRefresh,
  viewRouter,
  renderBrandInsights,
  toast
});

brandWorkspaceModule = BrandPulseBrandWorkspace.createBrandWorkspaceModule({
  state,
  $,
  clamp,
  WATCHLIST_KEY,
  normalizeAccessRole,
  normalizeBrandRow,
  riskMeta,
  renderBrandEarlyWarning,
  renderPillList,
  buildPros,
  buildCons,
  buildWhyText,
  buildRecommendation,
  escapeHtml,
  populateCustomerVoiceBrandSelect,
  renderKeywords,
  renderAnalystCustomerVoice,
  renderAnalystFocusPanel,
  renderSmartInsight,
  renderAnalyticsSummaryContext,
  renderRoleDashboardPanel,
  callApi,
  handleAuthError,
  viewRouter,
  toast,
  scopedStorageWrite
});

const {
  renderBrandComparison,
  renderDashboardAnalyticsState,
  addSelectedBrandToWatchlist,
  clearBrandWatchlist,
  handleWatchlistPick,
  handleBrandQuickPick,
  handleInsightQuickPick,
  handleCompareQuickPick
} = brandWorkspaceModule;

let confirmResolve = null;

function scopedStorageKey(baseKey) {
  return baseKey + "::" + normalizeStorageScope(state.storageScope || "guest");
}

function scopedStorageRead(baseKey, fallback) {
  return storageRead(scopedStorageKey(baseKey), fallback);
}

function scopedStorageWrite(baseKey, value) {
  storageWrite(scopedStorageKey(baseKey), value);
}

function sameSessionRevision(revision) {
  return revision === state.sessionRevision;
}

    function fillSingleReviewSample(sample) {
      const normalized = normalizeReviewSample(sample);
      if (!normalized) return null;
      const reviewInput = $("#singleReviewText");
      const brandInput = $("#singleBrand");
      const platformInput = $("#singlePlatform");
      const ratingInput = $("#singleRating");
      if (!reviewInput) return null;
      reviewInput.value = normalized.review_text;
      if (brandInput) brandInput.value = normalized.brand || brandInput.value || "";
      if (platformInput) platformInput.value = normalized.platform || normalized.brand || platformInput.value || "";
      if (ratingInput) ratingInput.value = normalized.rating;
      setSingleReviewValidationState("");
      return normalized;
    }

    function fallbackRandomReviewSample(requestedBrand = "") {
      const requested = normalizeReviewLookup(requestedBrand);
      const realtimePool = (Array.isArray(state.latestRealtimeReviews) ? state.latestRealtimeReviews : [])
        .map((row) => normalizeReviewSample(row))
        .filter(Boolean);
      const matchingRealtime = requested
        ? realtimePool.filter((item) => {
          const brand = normalizeReviewLookup(item.brand);
          const platform = normalizeReviewLookup(item.platform);
          return brand === requested || platform === requested;
        })
        : realtimePool;
      const preferredRealtime = matchingRealtime.length ? matchingRealtime : realtimePool;
      if (preferredRealtime.length) {
        return preferredRealtime[Math.floor(Math.random() * preferredRealtime.length)];
      }

      const localPool = RANDOM_REVIEW_FALLBACKS
        .map((row) => normalizeReviewSample(row))
        .filter(Boolean);
      const matchingLocal = requested
        ? localPool.filter((item) => {
          const brand = normalizeReviewLookup(item.brand);
          const platform = normalizeReviewLookup(item.platform);
          return brand === requested || platform === requested;
        })
        : localPool;
      const preferredLocal = matchingLocal.length ? matchingLocal : localPool;
      if (!preferredLocal.length) return null;
      return preferredLocal[Math.floor(Math.random() * preferredLocal.length)];
    }

    function toast(message, type = "info") {
      const toastEl = document.createElement("div");
      toastEl.className = "toast " + type;
      const titleEl = document.createElement("strong");
      const bodyEl = document.createElement("p");
      titleEl.textContent = type;
      bodyEl.textContent = message;
      toastEl.appendChild(titleEl);
      toastEl.appendChild(bodyEl);
      $("#toastStack").appendChild(toastEl);
      $("#srAnnouncements").textContent = message;
      window.setTimeout(() => {
        toastEl.remove();
      }, 3400);
    }

    function closeConfirmDialog(result) {
      const overlay = $("#confirmOverlay");
      if (!overlay || overlay.classList.contains("hidden")) return;
      overlay.classList.add("hidden");
      const resolver = confirmResolve;
      confirmResolve = null;
      if (resolver) resolver(Boolean(result));
    }

    function showConfirmDialog(message, title = "Confirm Action", confirmLabel = "OK", cancelLabel = "Cancel") {
      const overlay = $("#confirmOverlay");
      if (!overlay) return Promise.resolve(false);
      $("#confirmTitle").textContent = title;
      $("#confirmMessage").textContent = message;
      $("#confirmOkButton").textContent = confirmLabel;
      $("#confirmCancelButton").textContent = cancelLabel;
      overlay.classList.remove("hidden");
      $("#confirmOkButton").focus();
      return new Promise((resolve) => {
        confirmResolve = resolve;
      });
    }

    function setAuthMode(mode) {
      const isRegister = mode === "register";
      $("#loginTab").classList.toggle("is-active", !isRegister);
      $("#registerTab").classList.toggle("is-active", isRegister);
      $("#loginTab").setAttribute("aria-selected", String(!isRegister));
      $("#registerTab").setAttribute("aria-selected", String(isRegister));
      $("#loginForm").classList.toggle("is-active", !isRegister);
      $("#registerForm").classList.toggle("is-active", isRegister);
      $("#authTitle").textContent = isRegister ? "Create Your Account" : "Enter the Control Room";
      $("#authMessage").textContent = isRegister
        ? "Create an account, then sign in with the same credentials."
        : "Use the dashboard account configured in the backend to unlock protected API calls.";
      $("#authError").textContent = "";
      $("#registerError").textContent = "";
      updateLoginButtonState();
    }

    function showLogin(message = "Use the dashboard account configured in the backend to unlock protected API calls.") {
      document.body.classList.add("auth-locked");
      $("#authOverlay").classList.remove("hidden");
      setAuthMode("login");
      $("#loginEmail").value = "";
      $("#authMessage").textContent = message;
    }

    function hideLogin() {
      document.body.classList.remove("auth-locked");
      $("#authOverlay").classList.add("hidden");
      $("#authError").textContent = "";
    }

    function ensureNavButtonMap() {
      if (state.navButtons) return state.navButtons;
      state.navButtons = {};
      $$("#navRail .nav-item").forEach((button) => {
        const view = button.dataset.view || "";
        if (view) state.navButtons[view] = button;
      });
      return state.navButtons;
    }

    function groupForView(role, view) {
      const resolved = normalizeAccessRole(role);
      const groups = ROLE_NAV_GROUPS[resolved] || [];
      return groups.find((item) => item.type === "group" && (item.views || []).includes(view)) || null;
    }

    function renderNavAccordion(role) {
      const rail = $("#navRail");
      if (!rail) return;
      const resolved = normalizeAccessRole(role);
      const allowedViews = new Set(allowedViewsForRole(resolved));
      const buttonMap = ensureNavButtonMap();
      const groups = ROLE_NAV_GROUPS[resolved] || [];
      const currentView = canonicalView(($$(".nav-item.is-active")[0]?.dataset.view) || (location.hash || "").replace("#", "") || defaultViewForRole(resolved));
      const hasStoredGroup = Object.prototype.hasOwnProperty.call(state.openNavGroup, resolved);
      const storedGroup = hasStoredGroup ? state.openNavGroup[resolved] : null;
      rail.innerHTML = "";

      groups.forEach((entry) => {
        if (entry.type === "link") {
          const button = buttonMap[entry.view];
          if (!button || !allowedViews.has(entry.view)) return;
          button.classList.remove("hidden");
          rail.appendChild(button);
          return;
        }

        const views = (entry.views || []).filter((view) => allowedViews.has(view) && buttonMap[view]);
        if (!views.length) return;

        const wrapper = document.createElement("div");
        wrapper.className = "nav-group";
        wrapper.dataset.group = entry.id;

        const toggle = document.createElement("button");
        toggle.type = "button";
        toggle.className = "nav-group-toggle";
        toggle.dataset.groupToggle = entry.id;
        toggle.setAttribute("aria-expanded", String(storedGroup === null ? views.includes(currentView) : storedGroup === entry.id));
        toggle.innerHTML = '<strong>' + entry.label + '</strong><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"></path></svg>';

        const submenu = document.createElement("div");
        submenu.className = "nav-submenu";

        views.forEach((view) => {
          const button = buttonMap[view];
          if (!button) return;
          button.classList.remove("hidden");
          submenu.appendChild(button);
        });

        const shouldOpen = storedGroup === null ? views.includes(currentView) : storedGroup === entry.id;
        wrapper.classList.toggle("is-open", shouldOpen);
        if (!hasStoredGroup && shouldOpen) state.openNavGroup[resolved] = entry.id;
        toggle.setAttribute("aria-expanded", String(shouldOpen));

        wrapper.appendChild(toggle);
        wrapper.appendChild(submenu);
        rail.appendChild(wrapper);
      });
    }

    function toggleNavGroup(groupId) {
      const resolved = normalizeAccessRole(state.userRole);
      const current = state.openNavGroup[resolved] || "";
      state.openNavGroup[resolved] = current === groupId ? "" : groupId;
      renderNavAccordion(resolved);
    }

    function applyRoleNavLabels(role) {
      const resolved = normalizeAccessRole(role);
      const labels = ROLE_NAV_LABELS[resolved] || ROLE_NAV_LABELS.analyst;
      $$(".nav-item").forEach((button) => {
        const labelEl = button.querySelector("span");
        if (!labelEl) return;
        if (!button.dataset.defaultLabel) button.dataset.defaultLabel = labelEl.textContent.trim();
        const view = button.dataset.view || "";
        labelEl.textContent = labels[view] || button.dataset.defaultLabel;
      });
    }

    function applyDashboardRolePresentation(role) {
      const resolved = normalizeAccessRole(role);
      const dashboardView = $("#view-dashboard");
      const previousRole = dashboardView?.getAttribute("data-role") || "";
      const eyebrow = document.querySelector("#view-dashboard .eyebrow");
      const title = document.querySelector("#view-dashboard .view-title");
      const copy = document.querySelector("#view-dashboard .view-copy");
      const commandStrip = $("#dashboardCommandStrip");
      const roleDashboardPanel = $("#roleDashboardPanel");
      const dashboardLayout = $("#dashboardLayout");
      const syncButton = $("#dashboardSyncButton");
      const refreshButton = $("#refreshScoreButton");
      const brandQuickSection = $("#dashboardBrandSection");
      const marketingSignalSection = $("#marketingSignalSection");
      const analystFocusSection = $("#analystFocusSection");
      const dashboardDisclosure = $("#dashboardDisclosure");
      const gaugeSection = $("#dashboardGaugeSection");
      const statsSection = $("#dashboardStatsSection");
      const summarySection = $("#dashboardSummarySection");
      const dashboardInsightCard = $("#dashboardInsightCard");
      const dashboardActivityCard = $("#dashboardActivityCard");
      const alertEyebrow = $("#dashboardAlertEyebrow");
      const alertTitle = $("#dashboardAlertTitle");
      const alertCopy = $("#dashboardAlertCopy");
      const disclosureEyebrow = $("#dashboardDisclosureEyebrow");
      const disclosureTitle = $("#dashboardDisclosureTitle");
      const disclosureHint = $("#dashboardDisclosureHint");
      const adminControlHub = $("#adminControlHub");
      if (dashboardView) dashboardView.setAttribute("data-role", resolved);
      renderRoleDashboardPanel();
      renderDashboardOverview(state.brandScore || normalizeBrandScore({}));

      if (commandStrip) commandStrip.classList.add("hidden");
      if (roleDashboardPanel) roleDashboardPanel.classList.remove("hidden");
      if (brandQuickSection) brandQuickSection.classList.add("hidden");
      if (marketingSignalSection) marketingSignalSection.classList.add("hidden");
      if (analystFocusSection) analystFocusSection.classList.add("hidden");
      if (dashboardDisclosure) dashboardDisclosure.classList.add("hidden");
      if (gaugeSection) gaugeSection.classList.remove("hidden");
      if (dashboardLayout) {
        dashboardLayout.classList.remove("dashboard-layout--stats-only");
        dashboardLayout.classList.add("dashboard-layout--hero-only");
      }
      if (statsSection) {
        statsSection.classList.add("hidden");
        statsSection.classList.remove("stats-strip--wide");
      }
      if (summarySection) summarySection.classList.remove("hidden");
      if (dashboardInsightCard) dashboardInsightCard.classList.add("hidden");
      if (dashboardActivityCard) dashboardActivityCard.classList.remove("hidden");
      if (adminControlHub) adminControlHub.classList.add("hidden");

      if (resolved === "admin") {
        if (eyebrow) eyebrow.textContent = "DASHBOARD";
        if (title) title.textContent = "Executive Dashboard";
        if (copy) copy.textContent = "Key system health, risk, and readiness at a glance.";
        if (commandStrip) commandStrip.classList.remove("hidden");
        if (roleDashboardPanel) roleDashboardPanel.classList.remove("hidden");
        if (dashboardInsightCard) dashboardInsightCard.classList.add("hidden");
        if (dashboardActivityCard) dashboardActivityCard.classList.add("hidden");
        if (adminControlHub) adminControlHub.classList.remove("hidden");
        if (dashboardDisclosure) dashboardDisclosure.classList.remove("hidden");
        if (syncButton) syncButton.textContent = "Sync";
        if (refreshButton) refreshButton.textContent = "Refresh";
        if (alertEyebrow) alertEyebrow.textContent = "Executive Note";
        if (alertTitle) alertTitle.textContent = "System Alert";
        if (alertCopy) alertCopy.textContent = "Watch model readiness, complaint pressure, and ingest health.";
        if (disclosureEyebrow) disclosureEyebrow.textContent = "Detailed View";
        if (disclosureTitle) disclosureTitle.textContent = "Diagnostics and supporting signals";
        if (disclosureHint) disclosureHint.textContent = "Open";
        if (dashboardDisclosure) {
          dashboardDisclosure.classList.remove("hidden");
          dashboardDisclosure.open = false;
        }
        return;
      }

      if (resolved === "marketing_staff") {
        if (eyebrow) eyebrow.textContent = "MARKETING";
        if (title) title.textContent = "Brand Monitoring Dashboard";
        if (copy) copy.textContent = "Leaders, comparison readiness, and brand risk in one campaign-facing view.";
        if (brandQuickSection) brandQuickSection.classList.remove("hidden");
        if (marketingSignalSection) marketingSignalSection.classList.remove("hidden");
        if (dashboardDisclosure) {
          dashboardDisclosure.classList.remove("hidden");
          if (previousRole !== resolved) dashboardDisclosure.open = true;
        }
        if (syncButton) syncButton.textContent = "Sync";
        if (refreshButton) refreshButton.textContent = "Refresh";
        if (alertEyebrow) alertEyebrow.textContent = "Market Note";
        if (alertTitle) alertTitle.textContent = "Market Alert";
        if (alertCopy) alertCopy.textContent = "Catch brand risk and customer shifts early.";
        if (disclosureEyebrow) disclosureEyebrow.textContent = "Market Monitor";
        if (disclosureTitle) disclosureTitle.textContent = "Brand leaderboard and early warnings";
        if (disclosureHint) disclosureHint.textContent = "Expand";
        return;
      }

      if (eyebrow) eyebrow.textContent = "ANALYST";
      if (title) title.textContent = "Analyst Dashboard";
      if (copy) copy.textContent = "Investigate trend changes, complaint spikes, and the latest review evidence.";
      if (analystFocusSection) analystFocusSection.classList.remove("hidden");
      if (dashboardDisclosure) {
        dashboardDisclosure.classList.remove("hidden");
        if (previousRole !== resolved) dashboardDisclosure.open = true;
      }
      if (syncButton) syncButton.textContent = "Sync";
      if (refreshButton) refreshButton.textContent = "Refresh";
      if (alertEyebrow) alertEyebrow.textContent = "Analysis Note";
      if (alertTitle) alertTitle.textContent = "Analysis Alert";
      if (alertCopy) alertCopy.textContent = "Watch sentiment swings before drawing conclusions.";
      if (disclosureEyebrow) disclosureEyebrow.textContent = "Investigation Desk";
      if (disclosureTitle) disclosureTitle.textContent = "Diagnostic signals and quick analysis actions";
      if (disclosureHint) disclosureHint.textContent = "Inspect";
    }

    function applyRoleAccess(role, options = {}) {
      const { loadAdminData = true } = options;
      state.userRole = normalizeAccessRole(role);
      applyRoleNavLabels(state.userRole);
      applyDashboardRolePresentation(state.userRole);
      applyAnalyticsSummaryPresentation(state.userRole);
      if (loadAdminData && state.userRole === "admin" && !state.modelMetrics) loadAdminModelPerformance();
      syncShellLayout();
      renderNavAccordion(state.userRole);
    }

    function syncShellLayout() {
      const shell = document.querySelector(".shell");
      const signalPanel = $("#signalPanel");
      const signalDrawerToggle = $("#signalDrawerToggle");
      const showSignalPanel = WORKSPACE_SIGNAL_VIEWS.has(canonicalView(state.currentView));
      const hideSignalPanel = !showSignalPanel;

      if (shell) shell.classList.toggle("shell--dashboard-compact", hideSignalPanel);
      if (signalPanel) signalPanel.classList.toggle("hidden", hideSignalPanel);
      if (signalDrawerToggle) {
        signalDrawerToggle.classList.toggle("hidden", hideSignalPanel);
        signalDrawerToggle.setAttribute("aria-expanded", "false");
      }
      if (hideSignalPanel) document.body.classList.remove("drawer-open");
    }

    function resetTrendDrilldownPanel() {
      setTrendDrilldownActive("");
      $("#trendDrilldownTitle").textContent = "Interactive Chart Drill-down";
      $("#trendDrilldownCopy").textContent = "Click a sentiment to load review samples.";
      $("#trendReviewDrilldown").innerHTML = '<div class="mini-note">Review samples will appear here after you click a sentiment line or legend item.</div>';
    }

    function resetSingleAspectResult() {
      const panel = $("#singleAspectPanel");
      const title = $("#singleAspectTitle");
      const summary = $("#singleAspectSummary");
      const primary = $("#singleAspectPrimary");
      const tags = $("#singleAspectTags");
      if (panel) panel.classList.add("hidden");
      if (title) title.textContent = "Aspect Analysis";
      if (summary) summary.textContent = "Aspect signals will appear after prediction.";
      if (primary) {
        primary.className = "tag neutral";
        primary.textContent = "Waiting";
      }
      if (tags) tags.innerHTML = "<span>No aspect signal yet.</span>";
    }

    function resetSingleResultView() {
      $("#singleResultShell").classList.add("is-empty");
      $("#singleResultIntro").textContent = "Run a prediction to inspect sentiment, confidence, aspect signals, and rating alignment.";
      $("#singleSentimentBadge").className = "sentiment-badge sentiment-neutral";
      $("#singleSentimentBadge").textContent = "Standby";
      $("#singleConfidenceBar").style.width = "0%";
      $("#singleConfidenceText").textContent = "Unavailable";
      $("#singleTechnicalJson").textContent = "{}";
      $("#ratingWarning").classList.remove("is-visible");
      $("#ratingWarning").textContent = "";
      resetSingleAspectResult();
    }

    function setBatchSummaryVisibility(visible) {
      const layout = $("#batchLayout");
      const sidebar = $("#batchSidebar");
      if (layout) layout.classList.toggle("batch-layout--solo", !visible);
      if (sidebar) sidebar.classList.toggle("hidden", !visible);
    }

    function resetBatchResultView() {
      setBatchSummaryVisibility(false);
      $("#batchProcessedCount").textContent = "0";
      $("#batchTechnicalJson").textContent = "{}";
      renderGauge($("#batchGauge"), 0, {
        displayValue: "0.0",
        label: "Batch Confidence",
        suffix: "%",
        caption: "Waiting for batch response.",
        color: "var(--accent)"
      });
      renderBatchTable([]);
    }

    function resetSessionScopedState(options = {}) {
      const nextRole = normalizeAccessRole(options.role || "analyst");
      const storageIdentity = options.storageIdentity || "guest";
      state.sessionRevision += 1;
      state.storageScope = normalizeStorageScope(storageIdentity);
      state.brandScore = emptyBrandScore();
      state.latestSource = "No endpoint call yet";
      state.latestConfidence = null;
      state.latestSentiment = "Standby";
      state.trends = [];
      state.keywords = [];
      state.keywordGroups = emptyKeywordGroups();
      state.customerVoiceKeywords = [];
      state.customerVoiceKeywordCache = {};
      state.customerVoiceKeywordsError = "";
      state.customerVoiceKeywordsFallback = false;
      state.customerVoiceLastScopeKey = "";
      state.customerVoiceLastLoadedScopeKey = "";
      state.brands = [];
      state.users = [];
      state.usersLoaded = false;
      state.usersLoading = false;
      state.platforms = [];
      state.realtimeSummary = emptyRealtimeSummary();
      state.latestRealtimeReviews = [];
      state.latestRealtimeReviewsMode = "empty";
      state.modelMetrics = null;
      state.modelTrainingAt = "";
      state.adminNotifications = [];
      state.trendDrilldownSentiment = "";
      state.trendReviewSamplesCache = {};
      state.watchlist = scopedStorageRead(WATCHLIST_KEY, []);
      state.openNavGroup = {};
      state.trendWindow = "all";
      state.trendBrand = "";
      state.customerVoiceWindow = "all";
      state.customerVoiceBrand = "";
      state.customerVoiceKeywordsLoading = false;
      state.dashboardKeywordsLoading = false;
      state.dashboardKeywordsError = "";
      state.trendDataLoading = false;
      state.customerVoiceRequestSeq += 1;
      state.dashboardKeywordRequestSeq = 0;
      state.trendRequestSeq += 1;
      state.insightRequestSeq += 1;
      state.compareRequestSeq += 1;
      state.usersLoading = false;
      state.dashboardAutoRefreshInFlight = false;
      state.dashboardAnalyticsRequestSeq = 0;

      applyRoleAccess(nextRole, { loadAdminData: false });
      updateDashboard(state.brandScore);
      updateSignalPanel(state.brandScore);
      updateConfidenceSignal(null, "Neutral");
      renderDashboardAnalyticsState();
      renderTrendChart([]);
      renderTrendMomentum();
      renderTrendMonthlyComparison();
      renderTrendReviewVolume();
      resetTrendDrilldownPanel();
      renderAdminModelPerformance();
      renderUsersTable([]);
      renderAdminNotifications();
      updateAdminNotificationBadge();
      resetSingleResultView();
      resetBatchResultView();
      renderHistory();
    }

    function getAllBrandNames() {
      const fromState = (state.brands || [])
        .map((item) => String(item.brand || "").trim())
        .filter(Boolean);
      if (fromState.length) return Array.from(new Set(fromState));
      return Array.from($("#brandInsightSelect")?.options || [])
        .map((option) => String(option.value || "").trim())
        .filter((value) => value && value.toLowerCase() !== "no brands available");
    }

    function getBrandMatches(query) {
      const value = String(query || "").trim().toLowerCase();
      const names = getAllBrandNames();
      if (!value) return names;
      return names.filter((name) => name.toLowerCase().includes(value));
    }

    function findBrandByQuery(query) {
      const value = String(query || "").trim().toLowerCase();
      const names = getAllBrandNames();
      if (!value || !names.length) return null;
      const exact = names.find((name) => name.toLowerCase() === value);
      if (exact) return exact;
      const partial = names.find((name) => name.toLowerCase().includes(value));
      return partial || null;
    }

    function refreshTopSearchSuggestions(query = "") {
      const datalist = $("#topSearchSuggestions");
      if (!datalist) return;
      const brandOptions = getBrandMatches(query).sort((a, b) => a.localeCompare(b));
      datalist.replaceChildren();
      brandOptions.forEach((brand) => {
        const option = document.createElement("option");
        option.value = brand;
        datalist.appendChild(option);
      });
    }

    function navigateFromSearch(query) {
      const brandMatch = findBrandByQuery(query);
      if (brandMatch) {
        $("#brandInsightSelect").value = brandMatch;
        viewRouter("brand-insights");
        renderBrandInsights();
        toast("Showing insights for " + brandMatch + ".", "success");
        return;
      }
      toast("No matching brand found. Please choose a brand name from the list.", "info");
    }

    function setSession(user) {
      state.isAuthenticated = true;
      $("#sessionChip").classList.remove("hidden");
      $("#logoutButton").classList.remove("hidden");
      let role = "analyst";
      if (user && typeof user === "object") {
        role = normalizeAccessRole(user.role);
        $("#sessionUser").textContent = user.name || user.email || "Active";
        $("#sessionRole").textContent = humanizeRole(role);
        $("#sessionChip").title = user.email || "";
        $("#sessionAvatar").textContent = sessionInitials(user.name || user.email || "");
      } else {
        $("#sessionUser").textContent = user || "Active";
        $("#sessionRole").textContent = humanizeRole(role);
        $("#sessionChip").title = "";
        $("#sessionAvatar").textContent = sessionInitials(user || "Active");
      }
      resetSessionScopedState({
        role,
        storageIdentity: sessionStorageIdentityForUser(user)
      });
      applyRoleAccess(role);
      hideLogin();
      viewRouter(defaultViewForRole(role));
      startDashboardAutoRefresh();
    }

    function clearSessionUi() {
      state.isAuthenticated = false;
      stopDashboardAutoRefresh();
      resetSessionScopedState({ role: "analyst", storageIdentity: "guest" });
      $("#sessionChip").classList.add("hidden");
      $("#logoutButton").classList.add("hidden");
      $("#sessionUser").textContent = "Offline";
      $("#sessionRole").textContent = "No session";
      $("#sessionChip").title = "";
      $("#sessionAvatar").textContent = "--";
      viewRouter("dashboard");
    }

    function warmDashboardAfterSession(options = {}) {
      const { showToast = false } = options;
      refreshBrandScore({ showToast }).catch((error) => {
        if (handleAuthError(error)) return;
        console.error("Dashboard warm-up failed.", error);
      });
    }

    function validateRegistrationForm(name, email, password) {
      if (!name.trim()) return "Name is required.";
      if (!email.trim()) return "Email is required.";
      if (!email.includes("@")) return "Enter a valid email address.";
      if (password.length < 8) return "Password must be at least 8 characters long.";
      if (!/[A-Z]/.test(password)) return "Password must include at least one uppercase letter.";
      if (!/[a-z]/.test(password)) return "Password must include at least one lowercase letter.";
      if (!/\d/.test(password)) return "Password must include at least one number.";
      if (!/[^A-Za-z0-9]/.test(password)) return "Password must include at least one special character.";
      return "";
    }

    function handleAuthError(error, fallbackMessage) {
      if (error && error.status === 401) {
        confirmSessionStillValid(fallbackMessage).catch(() => {});
        return true;
      }
      return false;
    }

    function renderGauge(element, value, options = {}) {
      if (!element) return;
      const numeric = Number.isFinite(Number(value)) ? Number(value) : 0;
      const clamped = clamp(numeric, 0, 100);
      const color = options.color || "var(--accent)";
      element.style.setProperty("--value", clamped.toFixed(2));
      element.style.setProperty("--ring-color", color);
      const numberEl = element.querySelector("[data-gauge-number]");
      const suffixEl = element.querySelector("[data-gauge-suffix]");
      const labelEl = element.querySelector("[data-gauge-label]");
      const captionEl = element.querySelector("[data-gauge-caption]");
      if (numberEl) numberEl.textContent = options.displayValue ?? numeric.toFixed(1);
      if (suffixEl) suffixEl.textContent = options.suffix ?? "";
      if (labelEl) labelEl.textContent = options.label ?? "";
      if (captionEl) captionEl.textContent = options.caption ?? "";
    }

    function setButtonLoading(button, loading, text, loadingText = "Working...") {
      if (!button) return;
      if (!button.dataset.label) {
        button.dataset.label = text || button.textContent.trim();
      }
      button.disabled = loading;
      button.classList.toggle("is-loading", loading);
      button.innerHTML = loading
        ? '<span class="spinner" aria-hidden="true"></span><span>' + loadingText + "</span>"
        : button.dataset.label;
    }

    function setDashboardSyncStatus(message, tone = "idle") {
      const status = $("#dashboardSyncStatus");
      if (!status) return;
      status.textContent = message || "Quick sync updates live data. Refresh rebuilds analytics.";
      status.dataset.tone = tone;
    }

    function dashboardSyncTimestampLabel() {
      return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    }

    function setDashboardActionBusy(activeButton, loading, loadingText) {
      const syncButton = $("#dashboardSyncButton");
      const refreshButton = $("#refreshScoreButton");
      const buttons = [syncButton, refreshButton].filter(Boolean);
      buttons.forEach((button) => {
        if (!button.dataset.label) {
          button.dataset.label = button.textContent.trim();
        }
        const isActive = button === activeButton;
        button.classList.toggle("is-busy", loading && !isActive);
        if (isActive) {
          setButtonLoading(button, loading, button.dataset.label, loadingText);
          return;
        }
        button.disabled = loading;
        button.classList.remove("is-loading");
        button.innerHTML = button.dataset.label;
      });
    }

    function updateLoginButtonState() {
      const button = $("#loginButton");
      const emailInput = $("#loginEmail");
      const passwordInput = $("#loginPassword");
      if (!button || !emailInput || !passwordInput) return;
      const email = emailInput.value.trim();
      const password = passwordInput.value;
      const canSubmit = Boolean(email && password);
      if (!button.classList.contains("is-loading")) {
        button.disabled = !canSubmit;
      }
    }

    function shake(element) {
      element.classList.remove("is-invalid");
      void element.offsetWidth;
      element.classList.add("is-invalid");
      window.setTimeout(() => element.classList.remove("is-invalid"), 320);
    }

    function setSingleReviewValidationState(message = "") {
      const field = $("#singleReviewText")?.closest(".field");
      const note = $("#singleReviewNote");
      if (!field || !note) return;
      const hasError = Boolean(message);
      field.classList.toggle("has-error", hasError);
      $("#singleReviewText").setAttribute("aria-invalid", hasError ? "true" : "false");
      note.textContent = hasError
        ? message
        : "Required. Paste one customer review here before prediction.";
    }

    function getApiCandidates(path) {
      const normalized = path.startsWith("/") ? path : "/" + path;
      const urls = [];
      const add = (value) => {
        if (!urls.includes(value)) urls.push(value);
      };
      const apiBases = [];
      const addApiBase = (value) => {
        if (value && !apiBases.includes(value)) apiBases.push(value);
      };
      const preferred = state.apiPreferredCandidates && state.apiPreferredCandidates[normalized];
      if (preferred && String(preferred).includes("/api/")) add(preferred);
      if (state.apiPreferredBaseUrl) addApiBase(state.apiPreferredBaseUrl);
      const protocol = location.protocol === "https:" ? "https:" : "http:";
      const hostname = String(location.hostname || "").trim().toLowerCase();
      const isLoopbackHost = hostname === "localhost" || hostname === "127.0.0.1";
      if (location.origin && location.origin !== "null" && location.port === "5000") {
        addApiBase(location.origin);
      }
      if (hostname) {
        addApiBase(protocol + "//" + hostname + ":5000");
        if (hostname === "localhost") addApiBase(protocol + "//127.0.0.1:5000");
        if (hostname === "127.0.0.1") addApiBase(protocol + "//localhost:5000");
      }
      addApiBase("http://127.0.0.1:5000");
      addApiBase("http://localhost:5000");
      const preferDedicatedBackendHost = Boolean(isLoopbackHost && location.port && location.port !== "5000");

      if (location.protocol === "file:") {
        apiBases.forEach((base) => add(base + "/api" + normalized));
        apiBases.forEach((base) => add(base + normalized));
        return urls;
      }

      if (normalized.startsWith("/api/")) {
        if (!preferDedicatedBackendHost) add(normalized);
        apiBases.forEach((base) => add(base + normalized));
        if (preferDedicatedBackendHost) add(normalized);
        return urls;
      }

      if (!preferDedicatedBackendHost) add("/api" + normalized);
      apiBases.forEach((base) => add(base + "/api" + normalized));
      if (preferDedicatedBackendHost) add("/api" + normalized);
      return urls;
    }

    function rememberPreferredApiCandidate(normalizedPath, url, method = "") {
      if (!state.apiPreferredCandidates) state.apiPreferredCandidates = {};
      state.apiPreferredCandidates[normalizedPath] = url;
      if (method) state.latestSource = method + " " + url;
      try {
        const resolvedUrl = new URL(url, window.location.href);
        const sameOriginUrl = window.location.origin !== "null" && resolvedUrl.origin === window.location.origin;
        if (resolvedUrl.pathname.startsWith("/api/") && (resolvedUrl.port === "5000" || sameOriginUrl)) {
          state.apiPreferredBaseUrl = resolvedUrl.origin;
        }
      } catch (error) {
        // Keep the last working API base when URL parsing fails.
      }
    }

    function pickPreferredHttpError(currentError, nextError) {
      if (!currentError) return nextError;
      const currentStatus = Number(currentError.status || 0);
      const nextStatus = Number(nextError.status || 0);
      if (currentStatus && currentStatus !== 401 && nextStatus === 401) return currentError;
      if (nextStatus && nextStatus !== 401 && currentStatus === 401) return nextError;
      const priorityForStatus = (status) => {
        if (status === 403) return 5;
        if (status >= 500) return 4;
        if (status >= 400 && status !== 401) return 3;
        if (status === 401) return 1;
        return 0;
      };
      return priorityForStatus(nextStatus) > priorityForStatus(currentStatus) ? nextError : currentError;
    }

    async function probeSessionState(timeoutMs = 5000) {
      const normalizedPath = "/auth/session";
      const candidates = getApiCandidates(normalizedPath);
      let unauthenticated = false;

      for (const url of candidates) {
        const controller = new AbortController();
        const timeoutHandle = setTimeout(() => controller.abort(), timeoutMs);
        try {
          const response = await fetch(url, {
            method: "GET",
            credentials: "include",
            cache: "no-store",
            signal: controller.signal
          });
          const raw = await response.text();
          let data = {};
          try {
            data = raw ? JSON.parse(raw) : {};
          } catch (error) {
            data = {};
          }
          if (!response.ok) continue;
          if (data && data.authenticated) {
            rememberPreferredApiCandidate(normalizedPath, url);
            return {
              authenticated: true,
              user: normalizeSessionUser(data)
            };
          }
          unauthenticated = true;
        } catch (error) {
          // Try the next backend candidate before treating the session as expired.
        } finally {
          clearTimeout(timeoutHandle);
        }
      }

      if (unauthenticated) return { authenticated: false, user: null };
      return null;
    }

    async function confirmSessionStillValid(fallbackMessage) {
      if (state.sessionRecheckPromise) return state.sessionRecheckPromise;
      stopDashboardAutoRefresh();
      state.sessionRecheckPromise = (async () => {
        const sessionState = await probeSessionState();
        if (sessionState && sessionState.authenticated) {
          state.isAuthenticated = true;
          return false;
        }
        if (sessionState && sessionState.authenticated === false) {
          clearSessionUi();
          showLogin(fallbackMessage || "Your session expired. Sign in again to continue.");
          return true;
        }
        return false;
      })();
      try {
        return await state.sessionRecheckPromise;
      } finally {
        state.sessionRecheckPromise = null;
        syncDashboardAutoRefresh();
      }
    }

    async function callApi(path, options = {}) {
      const method = options.method || "GET";
      const fallbackMethods = options.fallbackMethods || [];
      const methods = [method, ...fallbackMethods.filter((item) => item !== method)];
      const normalizedPath = path.startsWith("/") ? path : "/" + path;
      const candidates = getApiCandidates(path);
      const timeoutMs = Number.isFinite(options.timeoutMs) ? Number(options.timeoutMs) : 12000;
      let lastError = new Error("Request failed");
      let bestHttpError = null;

      for (const currentMethod of methods) {
        for (const url of candidates) {
          const controller = new AbortController();
          const timeoutHandle = setTimeout(() => controller.abort(), timeoutMs);
          try {
            const response = await fetch(url, {
              method: currentMethod,
              credentials: "include",
              headers: options.body ? { "Content-Type": "application/json" } : {},
              body: options.body ? JSON.stringify(options.body) : undefined,
              signal: controller.signal
            });

            const raw = await response.text();
            let data = {};
            try {
              data = raw ? JSON.parse(raw) : {};
            } catch (error) {
              data = { message: raw };
            }

            if (response.ok) {
              rememberPreferredApiCandidate(normalizedPath, url, currentMethod);
              return data;
            }

            const message = data.error || data.message || data.detail || (response.status + " " + response.statusText);
            const httpError = new Error(message);
            httpError.status = response.status;
            lastError = httpError;
            bestHttpError = pickPreferredHttpError(bestHttpError, httpError);
          } catch (error) {
            if (error && error.name === "AbortError") {
              lastError = new Error("Request timeout after " + timeoutMs + "ms");
            } else {
              lastError = error;
            }
          } finally {
            clearTimeout(timeoutHandle);
          }
        }
      }
      if (bestHttpError) {
        throw bestHttpError;
      }
      const networkFailure = lastError && (
        String(lastError.message || "").toLowerCase().includes("failed to fetch")
        || String(lastError.message || "").toLowerCase().includes("networkerror")
      );
      if (networkFailure) {
        throw new Error("Cannot connect to the backend API. Start the backend server or update the deployed API origin and retry.");
      }
      throw lastError;
    }
    function updatePanelClock() {
      const clock = $("#panelClock");
      const currentTime = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
      if (clock) clock.textContent = currentTime;
    }

    function resetViewScroll() {
      const stage = document.querySelector(".stage");
      const mainShell = document.querySelector(".app-shell");
      if (stage) stage.scrollTop = 0;
      if (mainShell) mainShell.scrollTop = 0;
      document.documentElement.scrollTop = 0;
      document.body.scrollTop = 0;
      window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    }

    function scrollStageToTarget(targetId) {
      const target = document.getElementById(targetId);
      const stage = document.querySelector(".stage");
      if (!target) return;
      const stageIsScrollable = Boolean(
        stage
        && stage.scrollHeight > stage.clientHeight + 8
        && window.getComputedStyle(stage).overflowY !== "visible"
      );
      if (stageIsScrollable) {
        const stageRect = stage.getBoundingClientRect();
        const targetRect = target.getBoundingClientRect();
        const nextTop = stage.scrollTop + (targetRect.top - stageRect.top) - 18;
        stage.scrollTo({ top: Math.max(0, nextTop), behavior: "smooth" });
        return;
      }
      const nextTop = target.getBoundingClientRect().top + window.scrollY - 96;
      window.scrollTo({ top: Math.max(0, nextTop), behavior: "smooth" });
    }

    function navigateRoleDashboardCard(card) {
      if (!card) return;
      const view = card.dataset.view || "";
      const scrollTarget = card.dataset.scrollTarget || "";
      const compareA = card.dataset.compareA || "";
      const compareB = card.dataset.compareB || "";
      viewRouter(view);
      if (view === "brand-insights" && (compareA || compareB)) {
        const compareSelectA = $("#compareBrandA");
        const compareSelectB = $("#compareBrandB");
        if (compareSelectA && Array.from(compareSelectA.options || []).some((option) => option.value === compareA)) {
          compareSelectA.value = compareA;
        }
        if (compareSelectB && Array.from(compareSelectB.options || []).some((option) => option.value === compareB)) {
          compareSelectB.value = compareB;
        }
        renderBrandComparison();
      }
      if (scrollTarget) {
        window.setTimeout(() => scrollStageToTarget(scrollTarget), 60);
      }
    }

    function viewRouter(nextView) {
      const hashView = canonicalView((location.hash || "").replace("#", ""));
      const view = canonicalView(nextView || hashView || defaultViewForRole(state.userRole));
      const validViews = allowedViewsForRole(state.userRole);
      const fallbackView = validViews[0] || "dashboard";
      const resolved = validViews.includes(view) ? view : fallbackView;
      state.currentView = resolved;
      const activeGroup = groupForView(state.userRole, resolved);
      const normalizedRole = normalizeAccessRole(state.userRole);
      if (activeGroup) {
        state.openNavGroup[normalizedRole] = activeGroup.id;
      } else {
        state.openNavGroup[normalizedRole] = "";
      }
      $$(".view").forEach((section) => {
        const isActive = section.id === "view-" + resolved;
        section.classList.toggle("is-active", isActive);
        section.hidden = !isActive;
        section.setAttribute("aria-hidden", String(!isActive));
      });
      $$(".nav-item").forEach((button) => {
        button.classList.toggle("is-active", button.dataset.view === resolved);
      });
      renderNavAccordion(state.userRole);
      if (location.hash !== "#" + resolved) {
        history.replaceState(null, "", "#" + resolved);
      }
      if (resolved === "dashboard" && state.userRole === "admin" && !(state.users || []).length) loadUsersManagement();
      if (resolved === "model-performance" && state.userRole === "admin") loadAdminModelPerformance();
      if (resolved === "notifications" && state.userRole === "admin") renderAdminNotifications();
      if (resolved === "history") renderHistory();
      if (resolved === "users" && state.userRole === "admin") loadUsersManagement();
      if (resolved === "customer-intelligence") renderAnalystCustomerVoice();
      if (
        resolved === "customer-intelligence"
        && canLoadCustomerVoiceKeywords()
      ) {
        requestCustomerVoiceKeywordsRefresh();
      }
      if (
        resolved === "sentiment-distribution"
        && state.isAuthenticated
        && !state.dashboardKeywordsLoading
        && !hasKeywordGroups(state.keywordGroups)
      ) {
        refreshDashboardKeywordGroups({ sessionRevision: state.sessionRevision, timeoutMs: 90000 }).catch(() => {});
      }
      document.body.classList.remove("drawer-open");
      $("#signalDrawerToggle").setAttribute("aria-expanded", "false");
      syncShellLayout();
      resetViewScroll();
      syncDashboardAutoRefresh();
    }

    async function refreshBrandScore(options = {}) {
      const { showToast = true, withButton = true, includeAnalytics = true, forceRecalculate = false, buttonEl = null } = options;
      const button = buttonEl || $("#refreshScoreButton");
      const idleLabel = button ? (button.dataset.label || button.textContent.trim()) : "Refresh";
      const shouldAnnounceStatus = Boolean(withButton);
      const sessionRevision = state.sessionRevision;
      const requestSeq = ++state.dashboardRefreshRequestSeq;
      const analyticsRequestSeq = includeAnalytics ? ++state.dashboardAnalyticsRequestSeq : state.dashboardAnalyticsRequestSeq;
      if (withButton && button) {
        setDashboardActionBusy(button, true, forceRecalculate ? "Refreshing..." : "Syncing...");
      }
      if (shouldAnnounceStatus) {
        setDashboardSyncStatus(
          forceRecalculate
            ? "Refreshing analytics and rebuilding dashboard data..."
            : "Syncing latest live dashboard data...",
          "working"
        );
      }
      try {
        const summaryEndpoint = forceRecalculate ? "/dashboard/summary?refresh=1" : "/dashboard/summary";
        const [payload, realtimeSummaryPayload, realtimeReviewsPayload] = await Promise.all([
          callApi(summaryEndpoint, { timeoutMs: forceRecalculate ? 65000 : 60000 }),
          callApi("/dashboard/realtime-summary"),
          callApi("/dashboard/realtime-reviews?limit=5")
        ]);
        if (!sameSessionRevision(sessionRevision) || requestSeq !== state.dashboardRefreshRequestSeq) return;
        const score = normalizeBrandScore(payload);
        const summaryBrands = Array.isArray(payload.brand_scores) ? payload.brand_scores.map(normalizeBrandRow) : [];
        state.realtimeSummary = {
          total_reviews: Number(realtimeSummaryPayload.total_reviews || 0),
          platforms: Array.isArray(realtimeSummaryPayload.platforms) ? realtimeSummaryPayload.platforms : [],
          brands: Array.isArray(realtimeSummaryPayload.brands) ? realtimeSummaryPayload.brands : [],
          latest_ingested_at: realtimeSummaryPayload.latest_ingested_at || null
        };
        state.latestRealtimeReviews = Array.isArray(realtimeReviewsPayload.reviews) ? realtimeReviewsPayload.reviews : [];
        state.latestRealtimeReviewsMode = String(
          realtimeReviewsPayload.source_mode || (state.latestRealtimeReviews.length ? "live" : "empty")
        ).trim().toLowerCase() || "empty";
        state.brandScore = score;
        if (summaryBrands.length) state.brands = summaryBrands;
        updateDashboard(score);
        updateSignalPanel(score);
        renderRoleDashboardPanel();
        if (summaryBrands.length) renderDashboardAnalyticsState();
        if (includeAnalytics) {
          const analyticsRefresh = refreshDashboardAnalytics({ sessionRevision, requestSeq: analyticsRequestSeq });
          if (forceRecalculate) {
            await analyticsRefresh;
            if (shouldAnnounceStatus) setDashboardSyncStatus("Refresh completed at " + dashboardSyncTimestampLabel() + ".", "success");
          } else {
            if (shouldAnnounceStatus) setDashboardSyncStatus("Live data synced. Analytics will continue updating in the background.", "success");
            analyticsRefresh
              .then(() => {
                if (!sameSessionRevision(sessionRevision) || requestSeq !== state.dashboardRefreshRequestSeq) return;
                if (shouldAnnounceStatus) setDashboardSyncStatus("Dashboard synced at " + dashboardSyncTimestampLabel() + ".", "success");
              })
              .catch(() => {});
          }
        } else {
          if (shouldAnnounceStatus) setDashboardSyncStatus("Live dashboard synced at " + dashboardSyncTimestampLabel() + ".", "success");
        }
        if (showToast) toast(forceRecalculate ? "Brand score refreshed successfully." : "Dashboard synced successfully.", "success");
      } catch (error) {
        if (!sameSessionRevision(sessionRevision) || requestSeq !== state.dashboardRefreshRequestSeq) return;
        if (handleAuthError(error)) return;
        if (shouldAnnounceStatus) setDashboardSyncStatus(error.message || "Sync failed.", "error");
        if (showToast) toast(error.message || "Failed to refresh brand score.", "error");
      } finally {
        if (withButton && button && requestSeq === state.dashboardRefreshRequestSeq) {
          setDashboardActionBusy(button, false);
        }
      }
    }

    function shouldAutoRefreshDashboard() {
      const sessionChip = $("#sessionChip");
      return Boolean(
        sessionChip &&
        !sessionChip.classList.contains("hidden") &&
        state.currentView === "dashboard" &&
        document.visibilityState !== "hidden"
      );
    }

    function isDashboardManualRefreshActive() {
      const syncButton = $("#dashboardSyncButton");
      const refreshButton = $("#refreshScoreButton");
      return Boolean(
        (syncButton && syncButton.disabled)
        || (refreshButton && refreshButton.disabled)
      );
    }

    async function autoRefreshDashboardNumbers() {
      if (!shouldAutoRefreshDashboard()) return;
      if (state.dashboardAutoRefreshInFlight) return;
      if (isDashboardManualRefreshActive()) return;
      state.dashboardAutoRefreshInFlight = true;
      try {
        await refreshBrandScore({ showToast: false, withButton: false, includeAnalytics: false });
      } finally {
        state.dashboardAutoRefreshInFlight = false;
      }
    }

    function startDashboardAutoRefresh() {
      if (state.dashboardAutoRefreshTimer) return;
      state.dashboardAutoRefreshTimer = window.setInterval(autoRefreshDashboardNumbers, 10000);
    }

    function stopDashboardAutoRefresh() {
      if (state.dashboardAutoRefreshTimer) {
        window.clearInterval(state.dashboardAutoRefreshTimer);
        state.dashboardAutoRefreshTimer = null;
      }
      state.dashboardAutoRefreshInFlight = false;
    }

    function syncDashboardAutoRefresh() {
      if (shouldAutoRefreshDashboard()) {
        startDashboardAutoRefresh();
        return;
      }
      stopDashboardAutoRefresh();
    }

    function bindEvents() {
      on("#navRail", "click", (event) => {
        const toggle = event.target.closest("[data-group-toggle]");
        if (toggle) {
          event.preventDefault();
          toggleNavGroup(toggle.dataset.groupToggle || "");
          return;
        }
        const navItem = event.target.closest(".nav-item[data-view]");
        if (!navItem || !$("#navRail").contains(navItem)) return;
        event.preventDefault();
        viewRouter(navItem.dataset.view || "");
      });

      window.addEventListener("hashchange", () => viewRouter());
      document.addEventListener("visibilitychange", syncDashboardAutoRefresh);
      on("#signalDrawerToggle", "click", () => {
        const next = !document.body.classList.contains("drawer-open");
        document.body.classList.toggle("drawer-open", next);
        $("#signalDrawerToggle").setAttribute("aria-expanded", String(next));
      });
      on("#refreshScoreButton", "click", () => refreshBrandScore({
        forceRecalculate: true,
        buttonEl: $("#refreshScoreButton")
      }));
      on("#dashboardSyncButton", "click", () => refreshBrandScore({
        forceRecalculate: false,
        includeAnalytics: false,
        buttonEl: $("#dashboardSyncButton")
      }));
      on("#brandInsightSelect", "change", () => {
        renderBrandInsights();
      });
      on("#compareBrandA", "change", renderBrandComparison);
      on("#compareBrandB", "change", renderBrandComparison);
      on("#singleForm", "submit", handleSingleSubmit);
      on("#singleReviewText", "input", () => setSingleReviewValidationState(""));
      on("#singleRandomReviewButton", "click", (event) => {
        loadRandomBrandReview(event).catch((error) => {
          console.error("Random review load failed.", error);
        });
      });
      on("#batchForm", "submit", handleBatchSubmit);
      on("#clearHistoryButton", "click", clearHistory);
      on("#confirmOkButton", "click", () => closeConfirmDialog(true));
      on("#confirmCancelButton", "click", () => closeConfirmDialog(false));
      on("#confirmOverlay", "click", (event) => {
        if (event.target.id === "confirmOverlay") closeConfirmDialog(false);
      });
      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeConfirmDialog(false);
      });
      on("#refreshUsersButton", "click", loadUsersManagement);
      on("#refreshModelButton", "click", loadAdminModelPerformance);
      on("#adminOpenAlertsButton", "click", () => viewRouter("notifications"));
      on("#adminOpenUsersButton", "click", () => viewRouter("users"));
      on("#adminOpenModelButton", "click", () => viewRouter("model-performance"));
      on("#runPreprocessButton", "click", () => runAdminPipelineAction("/preprocess", $("#runPreprocessButton"), "Preprocess", "Running preprocess...", "Preprocessing completed."));
      on("#runFeaturesButton", "click", () => runAdminPipelineAction("/features", $("#runFeaturesButton"), "Features", "Running feature extraction...", "Feature extraction completed."));
      on("#runTrainButton", "click", () => runAdminPipelineAction("/train", $("#runTrainButton"), "Train Model", "Training model...", "Model training completed."));
      on("#usersTableBody", "click", handleUsersTableAction);
      on("#roleDashboardCards", "click", (event) => {
        const brandButton = event.target.closest("button[data-brand]");
        if (brandButton) {
          openBrandFromRoleDashboard(brandButton);
          return;
        }
        const card = event.target.closest(".role-mini-card[data-view]");
        if (!card) return;
        navigateRoleDashboardCard(card);
      });
      on("#roleDashboardCards", "keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        const brandButton = event.target.closest("button[data-brand]");
        if (brandButton) {
          event.preventDefault();
          openBrandFromRoleDashboard(brandButton);
          return;
        }
        const card = event.target.closest(".role-mini-card[data-view]");
        if (!card) return;
        event.preventDefault();
        navigateRoleDashboardCard(card);
      });
      onAll(".analyst-focus-btn[data-analyst-view]", "click", (event) => {
        viewRouter(event.currentTarget.dataset.analystView || "");
      });
      on("#brandQuickList", "click", handleBrandQuickPick);
      on("#brandInsightQuickList", "click", handleInsightQuickPick);
      on("#brandCompareQuickList", "click", handleCompareQuickPick);
      on("#brandWatchlistPills", "click", handleWatchlistPick);
      on("#addWatchlistButton", "click", addSelectedBrandToWatchlist);
      on("#clearWatchlistButton", "click", clearBrandWatchlist);
      on("#customerVoiceWindowSelect", "change", async (event) => {
        state.customerVoiceWindow = event.target.value || "all";
        renderAnalystCustomerVoice();
        await refreshCustomerVoiceKeywords();
      });
      on("#customerVoiceBrandSelect", "change", async (event) => {
        state.customerVoiceBrand = event.target.value || "";
        renderAnalystCustomerVoice();
        await refreshCustomerVoiceKeywords();
      });
      on("#trendWindowSelect", "change", async (event) => {
        state.trendWindow = event.target.value || "all";
        try {
          await refreshTrendView(state.trendBrand || "");
          renderAnalyticsSummaryContext();
        } catch (error) {
          if (handleAuthError(error)) return;
          $("#trendCaption").textContent = "Unable to load trend graph: " + (error.message || "request failed") + ".";
        }
      });
      on("#trendBrandSelect", "change", async (event) => {
        state.trendBrand = event.target.value || "";
        try {
          await refreshTrendView(state.trendBrand);
          renderAnalyticsSummaryContext();
        } catch (error) {
          if (handleAuthError(error)) return;
          $("#trendCaption").textContent = "Unable to load trend graph: " + (error.message || "request failed") + ".";
        }
      });
      on("#downloadTrendCsvButton", "click", exportTrendCsv);
      on("#downloadTrendReportButton", "click", exportTrendReport);
      on("#downloadTrendPdfButton", "click", exportTrendPdf);
      on("#downloadCustomerVoiceCsvButton", "click", exportCustomerVoiceCsv);
      on("#downloadCustomerVoiceReportButton", "click", exportCustomerVoiceReport);
      on("#downloadCustomerVoicePdfButton", "click", exportCustomerVoicePdf);
      onAll("#view-review-trends .trend-legend span[data-sentiment]", "click", (event) => {
        loadTrendDrilldown(event.currentTarget.dataset.sentiment || "");
      });
      ["#trendPositivePath", "#trendNeutralPath", "#trendNegativePath"].forEach((selector) => {
        on(selector, "click", (event) => loadTrendDrilldown(event.currentTarget.dataset.sentiment || ""));
      });
      on("#loginTab", "click", () => setAuthMode("login"));
      on("#registerTab", "click", () => setAuthMode("register"));

      on("#switchToLogin", "click", () => setAuthMode("login"));
      on("#toggleLoginPassword", "click", () => {
        const input = $("#loginPassword");
        const toggle = $("#toggleLoginPassword");
        if (!input || !toggle) return;
        const reveal = input.type === "password";
        input.type = reveal ? "text" : "password";
        toggle.textContent = reveal ? "Hide" : "Show";
        toggle.setAttribute("aria-label", reveal ? "Hide password" : "Show password");
        toggle.setAttribute("aria-pressed", String(reveal));
      });
      on("#loginEmail", "input", updateLoginButtonState);
      on("#loginPassword", "input", updateLoginButtonState);
      on("#loginForm", "submit", async (event) => {
        event.preventDefault();
        const email = $("#loginEmail")?.value.trim() || "";
        const password = $("#loginPassword")?.value || "";
        if (!email || !password) {
          $("#authError").textContent = "Email and password are required.";
          updateLoginButtonState();
          return;
        }

        const button = $("#loginButton");
        setButtonLoading(button, true, "Login", "Signing in...");
        $("#authError").textContent = "";
        try {
          const payload = await callApi("/auth/login", {
            method: "POST",
            body: { email, password }
          });
          setSession(normalizeSessionUser(payload) || email);
          toast("Login successful.", "success");
          warmDashboardAfterSession();
        } catch (error) {
          $("#authError").textContent = error.message || "Login failed.";
        } finally {
          setButtonLoading(button, false, "Login");
          updateLoginButtonState();
        }
      });
      on("#registerForm", "submit", async (event) => {
        event.preventDefault();
        const name = $("#registerName")?.value.trim() || "";
        const email = $("#registerEmail")?.value.trim() || "";
        const password = $("#registerPassword")?.value || "";
        const role = $("#registerRole")?.value || "analyst";
        const validationError = validateRegistrationForm(name, email, password);
        if (validationError) {
          $("#registerError").textContent = validationError;
          return;
        }

        const button = $("#registerButton");
        setButtonLoading(button, true, "Create Account");
        $("#registerError").textContent = "";
        try {
          await callApi("/auth/register", {
            method: "POST",
            body: { name, email, password, role }
          });
          $("#loginEmail").value = email;
          $("#loginPassword").value = "";
          $("#registerForm").reset();
          setAuthMode("login");
          $("#authMessage").textContent = "Account created. Sign in with your new credentials.";
          toast("Account created successfully. Please log in.", "success");
        } catch (error) {
          $("#registerError").textContent = error.message || "Account creation failed.";
        } finally {
          setButtonLoading(button, false, "Create Account");
        }
      });
      on("#logoutButton", "click", async () => {
        const confirmed = await showConfirmDialog(
          "Are you sure you want to log out?",
          "Confirm Logout",
          "Log Out",
          "Stay Signed In"
        );
        if (!confirmed) return;
        try {
          await callApi("/auth/logout", { method: "POST" });
        } catch (error) {
          // Ignore logout API errors and still clear local session UI.
        }
        clearSessionUi();
        showLogin("Signed out. Sign in again to continue.");
      });
    }

    async function bootUi() {
      applyRoleAccess(state.userRole);
      renderGauge($("#brandGauge"), 0, {
        displayValue: "0.0",
        label: "Brand Reputation",
        suffix: "/100 score",
        caption: "Waiting for score data.",
        color: "var(--accent)"
      });
      renderGauge($("#batchGauge"), 0, {
        displayValue: "0",
        label: "Batch Confidence",
        suffix: "%",
        caption: "Waiting for batch response.",
        color: "var(--accent)"
      });
      updateConfidenceSignal(null, "Neutral");
      updatePanelClock();
      renderSignalRadar(state.brandScore);
      window.setInterval(updatePanelClock, 30000);
      renderHistory();
      bindEvents();
      updateLoginButtonState();
      viewRouter();
      const sessionState = await probeSessionState();
      if (sessionState && sessionState.authenticated) {
        setSession(sessionState.user);
        warmDashboardAfterSession({ showToast: false });
      } else if (sessionState && sessionState.authenticated === false) {
        clearSessionUi();
        showLogin();
      } else {
        clearSessionUi();
        showLogin("Unable to verify the backend session. Make sure the Flask app is running, then sign in.");
      }
    }

    bootUi();
