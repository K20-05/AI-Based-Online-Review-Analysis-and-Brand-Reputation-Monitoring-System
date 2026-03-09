const HISTORY_KEY = "brandpulse-control-room-history";
    const THEME_KEY = "brandpulse-control-room-theme";
    const WATCHLIST_KEY = "brandpulse-control-room-watchlist";

    const state = {
      brandScore: {
        total_reviews: 0,
        positive_pct: 0,
        neutral_pct: 0,
        negative_pct: 0,
        brand_reputation_score: 0
      },
      latestSource: "No endpoint call yet",
      latestConfidence: null,
      latestSentiment: "Standby",
      trends: [],
      keywords: [],
      customerVoiceKeywords: [],
      customerVoiceKeywordCache: {},
      brands: [],
      users: [],
      platforms: [],
      modelMetrics: null,
      modelTrainingAt: "",
      adminNotifications: [],
      trendDrilldownSentiment: "",
      watchlist: storageRead(WATCHLIST_KEY, []),
      navButtons: null,
      openNavGroup: {},
      trendWindow: "all",
      trendBrand: "",
      customerVoiceWindow: "all",
      customerVoiceBrand: "",
      customerVoiceKeywordsLoading: false,
      customerVoiceRequestSeq: 0,
      trendRequestSeq: 0,
      userRole: "analyst",
      insightRequestSeq: 0,
      compareRequestSeq: 0
    };
    let confirmResolve = null;

    const ROLE_ACCESS = {
      admin: [
        "dashboard",
        "users",
        "model-performance",
        "notifications",
        "history",
        "single",
        "batch",
        "brand-insights",
        "brand-comparison",
        "sentiment-distribution",
        "review-trends",
        "keyword-frequency",
        "customer-intelligence",
        "analytics-summary",
        "about"
      ],
      analyst: ["dashboard", "single", "batch", "review-trends", "sentiment-distribution", "keyword-frequency", "customer-intelligence", "analytics-summary", "about"],
      marketing_staff: ["dashboard", "brand-insights", "brand-comparison", "sentiment-distribution", "keyword-frequency", "analytics-summary", "about"]
    };

    const ROLE_NAV_GROUPS = {
      admin: [
        { type: "link", view: "dashboard" },
        { type: "group", id: "control", label: "Admin Control", views: ["users", "model-performance", "notifications", "history"] },
        { type: "group", id: "analysis", label: "Workspace", views: ["single", "batch", "brand-insights", "brand-comparison", "sentiment-distribution", "review-trends", "keyword-frequency", "customer-intelligence", "analytics-summary"] },
        { type: "link", view: "about" }
      ],
      analyst: [
        { type: "link", view: "dashboard" },
        { type: "group", id: "prediction", label: "Prediction", views: ["single", "batch"] },
        { type: "group", id: "analytics", label: "Analytics", views: ["review-trends", "sentiment-distribution", "keyword-frequency", "customer-intelligence", "analytics-summary"] },
        { type: "link", view: "about" }
      ],
      marketing_staff: [
        { type: "link", view: "dashboard" },
        { type: "group", id: "brand", label: "Brand Monitor", views: ["brand-insights", "brand-comparison"] },
        { type: "group", id: "analytics", label: "Market Signals", views: ["sentiment-distribution", "keyword-frequency", "analytics-summary"] },
        { type: "link", view: "about" }
      ]
    };

    const ROLE_DEFAULT_VIEW = {
      admin: "users",
      analyst: "dashboard",
      marketing_staff: "dashboard"
    };

    const ROLE_NAV_LABELS = {
      admin: {
        dashboard: "Dashboard",
        users: "Users",
        "model-performance": "Model",
        notifications: "Alerts",
        history: "System Logs",
        single: "Single Review",
        batch: "Batch Analysis",
        "brand-insights": "Brand Insights",
        "brand-comparison": "Brand Comparison",
        "sentiment-distribution": "Sentiment Distribution",
        "review-trends": "Review Trends",
        "keyword-frequency": "Keyword Frequency",
        "customer-intelligence": "Customer Voice",
        "analytics-summary": "Summary",
        about: "About"
      },
      analyst: {
        dashboard: "Dashboard",
        single: "Single Review",
        batch: "Batch Analysis",
        "review-trends": "Review Trends",
        "sentiment-distribution": "Sentiment Distribution",
        "keyword-frequency": "Keyword Frequency",
        "customer-intelligence": "Customer Voice",
        "analytics-summary": "Summary",
        about: "About"
      },
      marketing_staff: {
        dashboard: "Dashboard",
        "brand-insights": "Brand Insights",
        "brand-comparison": "Brand Comparison",
        "sentiment-distribution": "Sentiment Distribution",
        "keyword-frequency": "Keyword Insights",
        "analytics-summary": "Business Summary",
        about: "About"
      }
    };

    const $ = (selector) => document.querySelector(selector);
    const $$ = (selector) => Array.from(document.querySelectorAll(selector));

    function clamp(value, min, max) {
      return Math.min(max, Math.max(min, value));
    }

    function storageRead(key, fallback) {
      try {
        const raw = localStorage.getItem(key);
        return raw ? JSON.parse(raw) : fallback;
      } catch (error) {
        return fallback;
      }
    }

    function storageWrite(key, value) {
      try {
        localStorage.setItem(key, JSON.stringify(value));
      } catch (error) {
        return;
      }
    }

    function toast(message, type = "info") {
      const toastEl = document.createElement("div");
      toastEl.className = "toast " + type;
      toastEl.innerHTML = "<strong>" + type + "</strong><p>" + message + "</p>";
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

    function humanizeRole(role) {
      const normalized = String(role || "").trim().toLowerCase();
      if (normalized === "marketing_staff") return "Marketing Staff";
      if (normalized === "analyst") return "Analyst";
      if (normalized === "admin") return "Admin";
      return "Role Unavailable";
    }

    function normalizeAccessRole(role) {
      const normalized = String(role || "").trim().toLowerCase();
      if (normalized === "admin" || normalized === "analyst" || normalized === "marketing_staff") {
        return normalized;
      }
      return "analyst";
    }

    function allowedViewsForRole(role) {
      return ROLE_ACCESS[normalizeAccessRole(role)] || ROLE_ACCESS.analyst;
    }

    function defaultViewForRole(role) {
      const resolved = normalizeAccessRole(role);
      return ROLE_DEFAULT_VIEW[resolved] || "dashboard";
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
      const currentView = ($$(".nav-item.is-active")[0]?.dataset.view) || (location.hash || "").replace("#", "") || defaultViewForRole(resolved);
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
      const eyebrow = document.querySelector("#view-dashboard .eyebrow");
      const title = document.querySelector("#view-dashboard .view-title");
      const copy = document.querySelector("#view-dashboard .view-copy");
      const syncButton = $("#dashboardSyncButton");
      const refreshButton = $("#refreshScoreButton");
      const brandQuickSection = $("#dashboardBrandSection");
      const marketingSignalSection = $("#marketingSignalSection");
      const analystFocusSection = $("#analystFocusSection");
      const gaugeSection = $("#dashboardGaugeSection");
      const statsSection = $("#dashboardStatsSection");
      const summarySection = $("#dashboardSummarySection");
      const alertTitle = $("#dashboardAlertTitle");
      const alertCopy = $("#dashboardAlertCopy");
      const confidenceWidget = $("#signalConfidenceWidget");
      const pressureWidget = $("#signalPressureWidget");
      const adminControlHub = $("#adminControlHub");
      const signalPanel = $("#signalPanel");
      const signalDrawerToggle = $("#signalDrawerToggle");
      const adminSideSummaryWidget = $("#adminSideSummaryWidget");
      const adminSideActionsWidget = $("#adminSideActionsWidget");
      const signalRadarWidget = $("#signalRadarWidget");
      const trendVectorsWidget = $("#signalTrendVectorsWidget");
      renderRoleDashboardPanel();

      if (resolved === "admin") {
        if (eyebrow) eyebrow.textContent = "ADMIN";
        if (title) title.textContent = "System Control Dashboard";
        if (copy) copy.textContent = "Access, alerts, and system status.";
        if (syncButton) syncButton.textContent = "Sync Admin State";
        if (refreshButton) refreshButton.textContent = "Refresh Control Hub";
        if (brandQuickSection) brandQuickSection.classList.remove("hidden");
        if (marketingSignalSection) marketingSignalSection.classList.add("hidden");
        if (analystFocusSection) analystFocusSection.classList.add("hidden");
        if (gaugeSection) gaugeSection.classList.add("hidden");
        if (statsSection) {
          statsSection.classList.remove("hidden");
          statsSection.classList.add("stats-strip--wide");
        }
        if (summarySection) summarySection.classList.add("hidden");
        if (adminControlHub) adminControlHub.classList.remove("hidden");
        if (confidenceWidget) confidenceWidget.classList.add("hidden");
        if (pressureWidget) pressureWidget.classList.add("hidden");
        if (signalRadarWidget) signalRadarWidget.classList.add("hidden");
        if (trendVectorsWidget) trendVectorsWidget.classList.add("hidden");
        if (adminSideSummaryWidget) adminSideSummaryWidget.classList.remove("hidden");
        if (adminSideActionsWidget) adminSideActionsWidget.classList.remove("hidden");
        if (signalPanel) signalPanel.classList.remove("hidden");
        if (signalDrawerToggle) signalDrawerToggle.classList.add("hidden");
        if (alertTitle) alertTitle.textContent = "Platform Monitoring";
        if (alertCopy) alertCopy.textContent = "Track access, alerts, and readiness.";
        renderAdminSidePanel();
        renderAdminControlHub();
        return;
      }

      if (resolved === "marketing_staff") {
        if (eyebrow) eyebrow.textContent = "MARKETING";
        if (title) title.textContent = "Brand Monitoring Dashboard";
        if (copy) copy.textContent = "Brand score, leaderboard, comparison, and insight.";
        if (syncButton) syncButton.textContent = "Insight Sync";
        if (refreshButton) refreshButton.textContent = "Refresh Brand Monitor";
        if (brandQuickSection) brandQuickSection.classList.add("hidden");
        if (marketingSignalSection) marketingSignalSection.classList.remove("hidden");
        if (analystFocusSection) analystFocusSection.classList.add("hidden");
        if (gaugeSection) gaugeSection.classList.add("hidden");
        if (statsSection) {
          statsSection.classList.add("hidden");
          statsSection.classList.remove("stats-strip--wide");
        }
        if (summarySection) summarySection.classList.remove("hidden");
        if (adminControlHub) adminControlHub.classList.add("hidden");
        if (adminSideSummaryWidget) adminSideSummaryWidget.classList.add("hidden");
        if (adminSideActionsWidget) adminSideActionsWidget.classList.add("hidden");
        if (signalRadarWidget) signalRadarWidget.classList.remove("hidden");
        if (trendVectorsWidget) trendVectorsWidget.classList.remove("hidden");
        if (confidenceWidget) confidenceWidget.classList.add("hidden");
        if (pressureWidget) pressureWidget.classList.add("hidden");
        if (signalPanel) signalPanel.classList.remove("hidden");
        if (signalDrawerToggle) signalDrawerToggle.classList.remove("hidden");
        if (alertTitle) alertTitle.textContent = "Market Alert";
        if (alertCopy) alertCopy.textContent = "Use this signal to catch brand risk, campaign pressure, and shifts in customer response before they spread.";
        return;
      }

      if (eyebrow) eyebrow.textContent = "ANALYST";
      if (title) title.textContent = "Analyst Dashboard";
      if (copy) copy.textContent = "Trends, keywords, complaints, and volume.";
      if (syncButton) syncButton.textContent = "Signal Sync";
      if (refreshButton) refreshButton.textContent = "Refresh Analytics";
      if (brandQuickSection) brandQuickSection.classList.add("hidden");
      if (marketingSignalSection) marketingSignalSection.classList.add("hidden");
      if (analystFocusSection) analystFocusSection.classList.remove("hidden");
      if (gaugeSection) gaugeSection.classList.add("hidden");
      if (statsSection) {
        statsSection.classList.add("hidden");
        statsSection.classList.remove("stats-strip--wide");
      }
      if (summarySection) summarySection.classList.add("hidden");
      if (adminControlHub) adminControlHub.classList.add("hidden");
      if (adminSideSummaryWidget) adminSideSummaryWidget.classList.add("hidden");
      if (adminSideActionsWidget) adminSideActionsWidget.classList.add("hidden");
      if (signalRadarWidget) signalRadarWidget.classList.remove("hidden");
      if (trendVectorsWidget) trendVectorsWidget.classList.remove("hidden");
      if (confidenceWidget) confidenceWidget.classList.remove("hidden");
      if (pressureWidget) pressureWidget.classList.remove("hidden");
      if (signalPanel) signalPanel.classList.remove("hidden");
      if (signalDrawerToggle) signalDrawerToggle.classList.remove("hidden");
      if (alertTitle) alertTitle.textContent = "Analysis Alert";
      if (alertCopy) alertCopy.textContent = "Watch trend breaks, sentiment swings, and complaint concentration before pushing analytical conclusions.";
      updatePanelClock();
      renderSignalRadar(state.brandScore || normalizeBrandScore({}));
    }

    function applyRoleAccess(role) {
      state.userRole = normalizeAccessRole(role);
      applyRoleNavLabels(state.userRole);
      applyDashboardRolePresentation(state.userRole);
      applyAnalyticsSummaryPresentation(state.userRole);
      if (state.userRole === "admin" && !state.modelMetrics) loadAdminModelPerformance();
      renderNavAccordion(state.userRole);
    }

    function normalizeSessionUser(payload) {
      if (!payload) return null;
      if (payload.user && typeof payload.user === "object") return payload.user;
      if (typeof payload === "object") {
        return {
          name: payload.name || payload.user_name || payload.username || "",
          email: payload.email || payload.user_email || "",
          role: payload.role || payload.user_role || payload.account_role || ""
        };
      }
      return null;
    }

    function sessionInitials(input) {
      const text = String(input || "").trim();
      if (!text) return "--";
      const cleaned = text.includes("@") ? text.split("@")[0] : text;
      const parts = cleaned.replace(/[^a-zA-Z0-9 ]/g, " ").trim().split(/\s+/).filter(Boolean);
      if (!parts.length) return "--";
      if (parts.length === 1) {
        const token = parts[0];
        return token.slice(0, Math.min(2, token.length)).toUpperCase();
      }
      return (parts[0][0] + parts[1][0]).toUpperCase();
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

    function renderBrandQuickList(brands) {
      const host = $("#brandQuickList");
      const eyebrow = $("#dashboardBrandEyebrow");
      const title = $("#dashboardBrandTitle");
      const note = $("#dashboardBrandNote");
      if (!host) return;
      const role = normalizeAccessRole(state.userRole);
      if (!Array.isArray(brands) || !brands.length) {
        if (eyebrow) eyebrow.textContent = role === "admin" ? "Brand List" : "Brand Leaderboard";
        if (title) title.textContent = role === "admin" ? "Available brands" : "Top brand reputation performers";
        const emptyCopy = role === "admin"
          ? "Brand list will appear after analytics data loads."
          : "Brand leaderboard will appear after analytics data loads.";
        if (note) note.textContent = emptyCopy;
        host.innerHTML = '<div class="mini-note">' + emptyCopy + "</div>";
        return;
      }
      const filtered = brands
        .slice()
        .filter((item) => String(item.brand || "").trim());
      if (role === "admin") {
        if (eyebrow) eyebrow.textContent = "Brand List";
        if (title) title.textContent = "Available brands";
        if (note) note.textContent = "Open any brand to inspect details.";
        const sorted = filtered
          .sort((a, b) => String(a.brand || "").localeCompare(String(b.brand || "")));
        host.innerHTML = sorted.map((brand) => {
          return '<button class="brand-quick-btn" type="button" data-brand="' + brand.brand + '"><span>' + brand.brand + '</span></button>';
        }).join("");
        return;
      }
      if (eyebrow) eyebrow.textContent = "Brand Leaderboard";
      if (title) title.textContent = "Top brand reputation performers";
      if (note) note.textContent = "Current top-ranked brands.";
      const sorted = filtered
        .sort((a, b) => Number(b.brand_reputation_score || 0) - Number(a.brand_reputation_score || 0))
        .slice(0, 6);
      host.innerHTML = sorted.map((brand) => {
        return '<button class="brand-quick-btn" type="button" data-brand="' + brand.brand + '"><span>' + brand.brand + '</span><b>' + Number(brand.brand_reputation_score || 0).toFixed(1) + "</b></button>";
      }).join("");
    }

    function renderMarketingSignals() {
      const leaderboardTitle = $("#marketingLeaderboardTitle");
      const leaderboardHost = $("#marketingLeaderboardList");
      const warningTitle = $("#marketingWarningTitle");
      const warningCopy = $("#marketingWarningCopy");
      if (!leaderboardTitle || !leaderboardHost || !warningTitle || !warningCopy) return;

      const brands = Array.isArray(state.brands) ? state.brands.slice() : [];
      if (!brands.length) {
        leaderboardTitle.textContent = "Top performers";
        leaderboardHost.innerHTML = '<div class="mini-note">Leaderboard will appear after analytics data loads.</div>';
        warningTitle.textContent = "No active warning";
        warningCopy.textContent = "Brand-level warning will appear after analytics data loads.";
        return;
      }

      const sorted = brands
        .filter((item) => String(item.brand || "").trim())
        .sort((a, b) => Number(b.brand_reputation_score || 0) - Number(a.brand_reputation_score || 0));
      leaderboardTitle.textContent = "Current top 4 brands";
      leaderboardHost.innerHTML = sorted.slice(0, 4).map((item, index) => {
        return [
          '<article class="similar-item">',
          '<div><strong>#' + String(index + 1) + " " + item.brand + '</strong><span>Positive ' + Number(item.positive_pct || 0).toFixed(1) + '%</span></div>',
          '<span class="score-chip">Score ' + Number(item.brand_reputation_score || 0).toFixed(1) + "</span>",
          "</article>"
        ].join("");
      }).join("");

      const warningBrand = sorted
        .slice()
        .sort((a, b) => Number(b.negative_pct || 0) - Number(a.negative_pct || 0))[0];
      if (!warningBrand) {
        warningTitle.textContent = "No active warning";
        warningCopy.textContent = "Warning logic will appear after brand analytics load.";
        return;
      }
      const topKeyword = Array.isArray(state.keywords) && state.keywords[0] ? "#" + state.keywords[0].word : "negative complaint topics";
      if (Number(warningBrand.negative_pct || 0) >= 40) {
        warningTitle.textContent = warningBrand.brand + " negative sentiment rising";
        warningCopy.innerHTML = [
          '<div class="marketing-warning">',
          '<span class="marketing-warning-chip warning-critical">High Warning</span>',
          '<div class="marketing-warning-lines">',
          '<div><strong>Signal</strong> Negative share at ' + Number(warningBrand.negative_pct || 0).toFixed(1) + '%.</div>',
          '<div><strong>Topic</strong> ' + (topKeyword.charAt(0) === "#"
            ? topKeyword.replace("#", "").replace(/^\w/, (char) => char.toUpperCase()) + " complaints increasing."
            : "Delivery complaints increasing.") + "</div>",
          '<div><strong>Action</strong> Review campaign impact and service messaging immediately.</div>',
          "</div>",
          "</div>"
        ].join("");
      } else if (Number(warningBrand.brand_reputation_score || 0) < 15) {
        warningTitle.textContent = warningBrand.brand + " reputation weakening";
        warningCopy.innerHTML = [
          '<div class="marketing-warning">',
          '<span class="marketing-warning-chip warning-watch">Watch</span>',
          '<div class="marketing-warning-lines">',
          '<div><strong>Signal</strong> Reputation score at ' + Number(warningBrand.brand_reputation_score || 0).toFixed(1) + ".</div>",
          '<div><strong>Action</strong> Monitor service quality, support feedback, and campaign perception.</div>',
          "</div>",
          "</div>"
        ].join("");
      } else {
        warningTitle.textContent = "Portfolio stable";
        warningCopy.innerHTML = [
          '<div class="marketing-warning">',
          '<span class="marketing-warning-chip warning-stable">Stable</span>',
          '<div class="marketing-warning-lines">',
          '<div><strong>Status</strong> No brand is currently in a strong warning zone.</div>',
          '<div><strong>Action</strong> Continue weekly monitoring for sudden complaint spikes.</div>',
          "</div>",
          "</div>"
        ].join("");
      }
    }

    function calculateCsat(row) {
      const positive = Number(row?.positive_pct || 0);
      const neutral = Number(row?.neutral_pct || 0);
      return clamp(positive + neutral * 0.5, 0, 100);
    }

    function renderCsatList(titleId, hostId, noteId) {
      const title = $("#" + titleId);
      const host = $("#" + hostId);
      const note = $("#" + noteId);
      if (!title || !host || !note) return;
      const brands = Array.isArray(state.brands) ? state.brands.slice() : [];
      if (!brands.length) {
        title.textContent = "CSAT by brand";
        host.innerHTML = '<div class="mini-note">CSAT will appear after brand analytics data loads.</div>';
        note.textContent = titleId === "analystCsatTitle"
          ? "Satisfaction proxy based on sentiment mix."
          : "CSAT is derived from positive share plus half of neutral share for a simple satisfaction proxy.";
        return;
      }
      const ranked = brands
        .filter((item) => String(item.brand || "").trim())
        .map((item) => ({ ...item, csat: calculateCsat(item) }))
        .sort((a, b) => b.csat - a.csat)
        .slice(0, 4);
      title.textContent = "Customer Satisfaction Score";
      host.className = "csat-list";
      host.innerHTML = ranked.map((item) => {
        return [
          '<article class="csat-row">',
          '<div class="csat-main"><span class="csat-brand">' + item.brand + '</span><strong class="csat-score">' + item.csat.toFixed(0) + '/100</strong></div>',
          '<div class="csat-meta"><span class="csat-tag">CSAT</span><span class="csat-positive">Positive ' + Number(item.positive_pct || 0).toFixed(1) + '%</span></div>',
          '</article>'
        ].join("");
      }).join("");
      note.textContent = titleId === "analystCsatTitle"
        ? "Satisfaction proxy based on sentiment mix."
        : "CSAT is calculated as Positive % + 0.5 x Neutral %, shown as a 100-point satisfaction proxy.";
    }

    function renderAnalystCustomerVoice() {
      renderCsatList("analystCsatTitle", "analystCsatList", "analystCsatNote");
      renderComplaintTopics("analystComplaintTopicsList", "analystComplaintTopicsNote");
      renderCustomerVoiceInsight();
    }

    async function refreshCustomerVoiceKeywords() {
      const host = $("#analystComplaintTopicsList");
      const note = $("#analystComplaintTopicsNote");
      const requestSeq = ++state.customerVoiceRequestSeq;
      const cacheKey = [
        String(state.customerVoiceBrand || "").trim().toLowerCase(),
        String(state.customerVoiceWindow || "all").trim().toLowerCase(),
        "negative"
      ].join("|");
      if (state.customerVoiceKeywordCache && Array.isArray(state.customerVoiceKeywordCache[cacheKey])) {
        state.customerVoiceKeywords = state.customerVoiceKeywordCache[cacheKey].slice();
        state.customerVoiceKeywordsLoading = false;
        renderComplaintTopics("analystComplaintTopicsList", "analystComplaintTopicsNote");
        renderCustomerVoiceInsight();
        return;
      }
      state.customerVoiceKeywordsLoading = true;
      state.customerVoiceKeywords = [];
      if (host) host.innerHTML = '<span>Loading complaint themes</span>';
      if (note) note.textContent = "Updating complaint themes for the current brand and time window.";
      renderCustomerVoiceInsight();

      const params = new URLSearchParams();
      if (state.customerVoiceBrand) params.set("brand", state.customerVoiceBrand);
      params.set("months", state.customerVoiceWindow || "all");
      params.set("sentiment", "Negative");

      try {
        const payload = await callApi("/dashboard/keywords?" + params.toString());
        if (requestSeq !== state.customerVoiceRequestSeq) return;
        state.customerVoiceKeywords = Array.isArray(payload.keywords) ? payload.keywords : [];
        state.customerVoiceKeywordCache[cacheKey] = state.customerVoiceKeywords.slice();
      } catch (error) {
        if (requestSeq !== state.customerVoiceRequestSeq) return;
        if (handleAuthError(error)) return;
        state.customerVoiceKeywords = [];
        if (host) host.innerHTML = '<span>Complaint themes unavailable</span>';
        if (note) note.textContent = "Unable to load complaint themes for the current selection.";
      } finally {
        if (requestSeq !== state.customerVoiceRequestSeq) return;
        state.customerVoiceKeywordsLoading = false;
        renderComplaintTopics("analystComplaintTopicsList", "analystComplaintTopicsNote");
        renderCustomerVoiceInsight();
      }
    }

    function renderBrandSideLists(brands) {
      const hosts = [$("#brandInsightQuickList"), $("#brandCompareQuickList")].filter(Boolean);
      if (!hosts.length) return;
      if (!Array.isArray(brands) || !brands.length) {
        hosts.forEach((host) => {
          host.innerHTML = '<div class="mini-note">Brand list will appear after analytics data loads.</div>';
        });
        return;
      }
      const sorted = brands
        .map((item) => String(item.brand || "").trim())
        .filter(Boolean)
        .sort((a, b) => a.localeCompare(b));
      const markup = sorted.map((brand) => {
        return '<button class="brand-quick-btn" type="button" data-brand="' + brand + '">' + brand + "</button>";
      }).join("");
      hosts.forEach((host) => {
        host.innerHTML = markup;
      });
    }

    function renderBrandWatchlist() {
      const host = $("#brandWatchlistPills");
      const note = $("#brandWatchlistNote");
      if (!host || !note) return;
      const watchlist = Array.isArray(state.watchlist) ? state.watchlist.filter(Boolean) : [];
      if (!watchlist.length) {
        host.innerHTML = '<span>No watched brands yet</span>';
        note.textContent = "Use this watchlist to keep high-priority brands one click away.";
        return;
      }
      host.innerHTML = watchlist.map((brand) => '<button class="ghost-btn" type="button" data-watch-brand="' + brand + '">' + brand + "</button>").join("");
      note.textContent = "Watchlist active for " + watchlist.length + " brand" + (watchlist.length === 1 ? "" : "s") + ".";
    }

    function saveWatchlist(nextWatchlist) {
      state.watchlist = Array.from(new Set((nextWatchlist || []).map((item) => String(item || "").trim()).filter(Boolean))).slice(0, 8);
      storageWrite(WATCHLIST_KEY, state.watchlist);
      renderBrandWatchlist();
    }

    function addSelectedBrandToWatchlist() {
      const select = $("#brandInsightSelect");
      const brand = select ? String(select.value || "").trim() : "";
      if (!brand) {
        toast("Select a brand before adding to watchlist.", "error");
        return;
      }
      saveWatchlist([...(state.watchlist || []), brand]);
      toast(brand + " added to watchlist.", "success");
    }

    function clearBrandWatchlist() {
      saveWatchlist([]);
      toast("Brand watchlist cleared.", "info");
    }

    function handleWatchlistPick(event) {
      const button = event.target.closest("button[data-watch-brand]");
      if (!button) return;
      const brand = button.dataset.watchBrand || "";
      if (!brand) return;
      $("#brandInsightSelect").value = brand;
      renderBrandInsights();
      toast("Loaded watchlist brand " + brand + ".", "success");
    }

    function handleBrandQuickPick(event) {
      const button = event.target.closest("button[data-brand]");
      if (!button) return;
      const brand = button.dataset.brand || "";
      if (!brand) return;
      $("#brandInsightSelect").value = brand;
      viewRouter("brand-insights");
      renderBrandInsights();
      toast("Showing insights for " + brand + ".", "success");
    }

    function handleInsightQuickPick(event) {
      const button = event.target.closest("button[data-brand]");
      if (!button) return;
      const brand = button.dataset.brand || "";
      if (!brand) return;
      $("#brandInsightSelect").value = brand;
      renderBrandInsights();
      toast("Loaded brand insight for " + brand + ".", "success");
    }

    function handleCompareQuickPick(event) {
      const button = event.target.closest("button[data-brand]");
      if (!button) return;
      const brand = button.dataset.brand || "";
      if (!brand) return;
      const selectA = $("#compareBrandA");
      const selectB = $("#compareBrandB");
      if (!selectA || !selectB) return;
      if (!selectA.value || selectA.value === brand) {
        selectA.value = brand;
      } else {
        selectB.value = brand;
      }
      renderBrandComparison();
      toast("Comparison slot updated for " + brand + ".", "success");
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
      applyRoleAccess(role);
      hideLogin();
      viewRouter(defaultViewForRole(role));
    }

    function clearSessionUi() {
      $("#sessionChip").classList.add("hidden");
      $("#logoutButton").classList.add("hidden");
      $("#sessionUser").textContent = "Offline";
      $("#sessionRole").textContent = "No session";
      $("#sessionChip").title = "";
      $("#sessionAvatar").textContent = "--";
      applyRoleAccess("analyst");
      viewRouter("dashboard");
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
        clearSessionUi();
        showLogin(fallbackMessage || "Your session expired. Sign in again to continue.");
        return true;
      }
      return false;
    }

    function renderGauge(element, value, options = {}) {
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
      if (!button.dataset.label) {
        button.dataset.label = text || button.textContent.trim();
      }
      button.disabled = loading;
      button.classList.toggle("is-loading", loading);
      button.innerHTML = loading
        ? '<span class="spinner" aria-hidden="true"></span><span>' + loadingText + "</span>"
        : button.dataset.label;
    }

    function updateLoginButtonState() {
      const email = $("#loginEmail").value.trim();
      const password = $("#loginPassword").value;
      const button = $("#loginButton");
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

    function getApiCandidates(path) {
      const normalized = path.startsWith("/") ? path : "/" + path;
      const urls = [];
      const add = (value) => {
        if (!urls.includes(value)) urls.push(value);
      };

      if (location.protocol === "file:") {
        add("http://127.0.0.1:5000/api" + normalized);
        add("http://localhost:5000/api" + normalized);
        add("http://127.0.0.1:5000" + normalized);
        add("http://localhost:5000" + normalized);
        return urls;
      }

      add(normalized);
      add("/api" + normalized);
      add("http://127.0.0.1:5000/api" + normalized);
      return urls;
    }

    async function callApi(path, options = {}) {
      const method = options.method || "GET";
      const fallbackMethods = options.fallbackMethods || [];
      const methods = [method, ...fallbackMethods.filter((item) => item !== method)];
      const candidates = getApiCandidates(path);
      const timeoutMs = Number.isFinite(options.timeoutMs) ? Number(options.timeoutMs) : 12000;
      let lastError = new Error("Request failed");

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
              state.latestSource = currentMethod + " " + url;
              return data;
            }

            const message = data.error || data.message || data.detail || (response.status + " " + response.statusText);
            lastError = new Error(message);
            lastError.status = response.status;
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
      const networkFailure = lastError && (
        String(lastError.message || "").toLowerCase().includes("failed to fetch")
        || String(lastError.message || "").toLowerCase().includes("networkerror")
      );
      if (networkFailure) {
        throw new Error("Cannot connect to backend API. Start Flask server at http://127.0.0.1:5000 and retry.");
      }
      throw lastError;
    }
    function normalizeBrandScore(payload) {
      const raw = payload && payload.brand_score ? payload.brand_score : payload || {};
      return {
        total_reviews: Number(raw.total_reviews || raw.rows || 0),
        positive_pct: Number(raw.positive_pct || raw.positivePercentage || raw.percentages?.Positive || 0),
        neutral_pct: Number(raw.neutral_pct || raw.neutralPercentage || raw.percentages?.Neutral || 0),
        negative_pct: Number(raw.negative_pct || raw.negativePercentage || raw.percentages?.Negative || 0),
        brand_reputation_score: Number(raw.brand_reputation_score || raw.brandScore || 0)
      };
    }

    function normalizeBrandRow(row) {
      return {
        brand: String(row.brand || row.Brand || "Unknown"),
        total_reviews: Number(row.total_reviews || row.totalReviews || 0),
        positive_pct: Number(row.positive_pct || row.positivePercentage || 0),
        neutral_pct: Number(row.neutral_pct || row.neutralPercentage || 0),
        negative_pct: Number(row.negative_pct || row.negativePercentage || 0),
        brand_reputation_score: Number(row.brand_reputation_score || row.brandScore || 0),
        has_trend_data: typeof row.has_trend_data === "boolean" ? row.has_trend_data : true
      };
    }

    function scoreNarrative(score) {
      if (score >= 70) return ["Reputation surge", "Audience response is strongly favorable across the active review stream."];
      if (score >= 40) return ["Healthy trajectory", "Brand sentiment remains positive with manageable negative drag."];
      if (score >= 15) return ["Mixed field conditions", "Positive and negative signals are close enough to require attention."];
      if (score >= 0) return ["Fragile balance", "Negative pressure is near parity and could flip the score quickly."];
      return ["Critical drift", "Negative sentiment is overpowering the positive stream. Escalation recommended."];
    }

    function getTrendLabel(value, positiveDirection = true) {
      if (value >= 60) return positiveDirection ? "Rising" : "High";
      if (value >= 35) return "Stable";
      return positiveDirection ? "Low" : "Contained";
    }

    function updatePanelClock() {
      const clock = $("#panelClock");
      if (!clock) return;
      clock.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }

    function setTrendIcon(icon, direction) {
      const stroke = direction === "up" ? "var(--positive)" : direction === "down" ? "var(--negative)" : "var(--neutral)";
      if (icon) icon.setAttribute("stroke", stroke);
    }

    function updateDashboard(score) {
      const narrative = scoreNarrative(score.brand_reputation_score);
      $("#statTotalReviews").textContent = score.total_reviews.toLocaleString();
      $("#statPositivePct").textContent = score.positive_pct.toFixed(2) + "%";
      $("#statNegativePct").textContent = score.negative_pct.toFixed(2) + "%";
      $("#statBrandScore").textContent = score.brand_reputation_score.toFixed(1);
      $("#dashboardNarrative").textContent = narrative[0];
      $("#dashboardNarrativeCopy").textContent = narrative[1];
      $("#dashboardSource").textContent = state.latestSource;

      const gaugeColor = score.brand_reputation_score >= 40
        ? "var(--positive)"
        : score.brand_reputation_score < 10
          ? "var(--negative)"
          : "var(--neutral)";

      renderGauge($("#brandGauge"), score.brand_reputation_score, {
        displayValue: score.brand_reputation_score.toFixed(1),
        label: "Brand Reputation",
        suffix: "/100 score",
        caption: "Current score from the latest `/dashboard/summary` response.",
        color: gaugeColor
      });
      updateDistributionChart(score);
      updateDashboardAlerts(score);
      renderAnalystCustomerVoice();
      renderAnalystFocusPanel();
      renderSmartInsight();
      renderAnalyticsSummaryContext();
      renderMarketingSignals();
      renderAdminOps();
      applyDashboardRolePresentation(state.userRole);
    }

    function renderSignalRadar(score) {
      const label = $("#signalRadarLabel");
      const value = $("#signalRadarScore");
      const copy = $("#signalRadarCopy");
      const status = $("#panelStatusText");
      if (!label || !value || !copy || !status) return;
      const role = normalizeAccessRole(state.userRole);
      const reputation = Number(score?.brand_reputation_score || 0);
      const negative = Number(score?.negative_pct || 0);
      const leader = getScoreExtremes().leader;
      value.textContent = reputation.toFixed(1);
      if (role === "marketing_staff") {
        label.textContent = "Market Pulse";
        copy.textContent = leader
          ? leader.brand + " is leading right now. Watch negative pressure at " + negative.toFixed(1) + "% and use this panel as a live market snapshot."
          : "Brand leadership and market pulse will appear after analytics data loads.";
        status.textContent = negative >= 40 ? "Campaign Risk" : "Brand Monitoring";
        return;
      }
      if (role === "admin") {
        label.textContent = "Control Pulse";
        copy.textContent = "Admin workspace tracks platform readiness and model state. Current score remains visible for oversight.";
        status.textContent = "Control View";
        return;
      }
      label.textContent = "Realtime Signal";
      copy.textContent = "Current review intelligence score is " + reputation.toFixed(1) + ". Use trend vectors and confidence signals to validate directional movement.";
      status.textContent = negative >= 40 ? "Negative Drift" : "Analysis Live";
    }

    function updateDashboardAlerts(score) {
      const risk = riskMeta(score.brand_reputation_score, score.negative_pct);
      if (risk.label === "High Risk") {
        $("#dashboardAlertTitle").textContent = "High Risk Alert";
        $("#dashboardAlertCopy").textContent = "Negative sentiment is elevated. Prioritize complaint resolution and service recovery actions.";
        return;
      }
      if (risk.label === "Medium Risk") {
        $("#dashboardAlertTitle").textContent = "Watchlist Alert";
        $("#dashboardAlertCopy").textContent = "Sentiment is mixed. Track daily shifts and respond early to rising complaint clusters.";
        return;
      }
      $("#dashboardAlertTitle").textContent = "Stable Signal";
      $("#dashboardAlertCopy").textContent = "Reputation is healthy. Maintain quality controls and continue proactive monitoring.";
    }

    function renderComplaintTopics(hostId = "analystComplaintTopicsList", noteId = "analystComplaintTopicsNote") {
      const host = $("#" + hostId);
      const note = $("#" + noteId);
      if (!host || !note) return;
      const analystView = hostId === "analystComplaintTopicsList";
      const sourceKeywords = analystView ? state.customerVoiceKeywords : state.keywords;
      if (analystView && state.customerVoiceKeywordsLoading) {
        host.innerHTML = '<span>Loading complaint themes</span>';
        note.textContent = "Updating complaint themes for the current brand and time window.";
        return;
      }
      if (!Array.isArray(sourceKeywords) || !sourceKeywords.length) {
        host.innerHTML = '<span>Waiting for keyword analytics</span>';
        note.textContent = analystView
          ? "No complaint themes found for the current brand and time window."
          : "Topics are inferred from frequent keywords and weighted by negative sentiment share.";
        return;
      }
      const topics = sourceKeywords
        .slice(0, 6)
        .map((item) => "#" + String(item.word || "").trim())
        .filter((item) => item !== "#");
      renderPillList(hostId, topics.length ? topics : ["No complaint topics available"]);
      note.textContent = analystView
        ? ((state.customerVoiceBrand ? state.customerVoiceBrand + " selected. " : "All brands selected. ") + "Complaint themes shown for " + customerVoiceWindowLabel().toLowerCase() + ".")
        : "Current negative share: " + Number(state.brandScore?.negative_pct || 0).toFixed(1) + "%. Topics shown from highest-frequency keywords.";
    }

    function renderBrandEarlyWarning(row) {
      const title = $("#brandWarningTitle");
      const copy = $("#brandWarningCopy");
      if (!title || !copy) return;
      if (!row) {
        title.textContent = "Early Warning";
        copy.textContent = "Brand-level risk warning will appear after data loads.";
        return;
      }
      if (row.negative_pct >= 40) {
        title.textContent = "Warning: negative sentiment above 40%";
        copy.textContent = row.brand + " is under pressure. Complaint growth is likely being driven by " + (state.keywords[0] ? "#" + state.keywords[0].word : "high-frequency negative topics") + ".";
        return;
      }
      if (row.brand_reputation_score < 15) {
        title.textContent = "Warning: low reputation zone";
        copy.textContent = row.brand + " has dropped into a weak score band. Investigate service, delivery, and support complaints before sentiment worsens.";
        return;
      }
      title.textContent = "Early Warning: contained";
      copy.textContent = row.brand + " is not in a high-risk state right now. Continue weekly monitoring for complaint spikes and negative drift.";
    }

    function renderTrendMomentum() {
      const title = $("#trendMomentumTitle");
      const copy = $("#trendMomentumCopy");
      if (!title || !copy) return;
      if (!Array.isArray(state.trends) || state.trends.length < 2) {
        title.textContent = "Sentiment Momentum";
        copy.textContent = "Momentum indicator will appear after trend data loads.";
        return;
      }
      const current = state.trends[state.trends.length - 1] || {};
      const previous = state.trends[state.trends.length - 2] || {};
      const positiveDelta = Number(current.Positive || 0) - Number(previous.Positive || 0);
      const negativeDelta = Number(current.Negative || 0) - Number(previous.Negative || 0);
      const scope = state.trendBrand ? activeTrendBrandLabel() : "portfolio";
      if (positiveDelta > 1 && negativeDelta <= 0) {
        title.textContent = "Sentiment Momentum: Improving";
        copy.textContent = scope + " is improving. Positive sentiment rose by " + positiveDelta.toFixed(1) + " points while negative pressure stayed flat or lower.";
        return;
      }
      if (negativeDelta > 1) {
        title.textContent = "Sentiment Momentum: Declining";
        copy.textContent = scope + " is declining. Negative sentiment rose by " + negativeDelta.toFixed(1) + " points in the latest review window.";
        return;
      }
      title.textContent = "Sentiment Momentum: Stable";
      copy.textContent = scope + " is stable. No material movement was detected between the last two periods.";
    }

    function renderTrendMonthlyComparison() {
      const title = $("#trendMonthlyCompareTitle");
      const copy = $("#trendMonthlyCompareCopy");
      if (!title || !copy) return;
      if (!Array.isArray(state.trends) || state.trends.length < 2) {
        title.textContent = "Monthly Comparison";
        copy.textContent = "Monthly comparison will appear after trend data loads.";
        return;
      }
      const current = state.trends[state.trends.length - 1] || {};
      const previous = state.trends[state.trends.length - 2] || {};
      const currentPeriod = String(current.period || "Current");
      const previousPeriod = String(previous.period || "Previous");
      const positiveDelta = Number(current.Positive || 0) - Number(previous.Positive || 0);
      const neutralDelta = Number(current.Neutral || 0) - Number(previous.Neutral || 0);
      const negativeDelta = Number(current.Negative || 0) - Number(previous.Negative || 0);
      title.textContent = "Monthly Comparison: " + previousPeriod + " vs " + currentPeriod;
      copy.textContent =
        "Positive " + (positiveDelta >= 0 ? "+" : "") + positiveDelta.toFixed(1) +
        " pts, Neutral " + (neutralDelta >= 0 ? "+" : "") + neutralDelta.toFixed(1) +
        " pts, Negative " + (negativeDelta >= 0 ? "+" : "") + negativeDelta.toFixed(1) + " pts.";
    }

    function renderSummaryDeepIntelligence() {
      const complaint = $("#summaryComplaintIntelligence");
      const platform = $("#summaryPlatformComparison");
      if (!complaint || !platform) return;

      const topTopics = (Array.isArray(state.keywords) ? state.keywords : [])
        .slice(0, 3)
        .map((item) => "#" + String(item.word || "").trim())
        .filter((item) => item !== "#");
      complaint.textContent = topTopics.length
        ? "Top complaint topics: " + topTopics.join(", ") + "."
        : "Complaint intelligence will appear after analytics load.";

      const platforms = (Array.isArray(state.platforms) ? state.platforms : [])
        .slice()
        .sort((a, b) => Number(b.Positive || 0) - Number(a.Positive || 0))
        .slice(0, 3);
      platform.textContent = platforms.length
        ? platforms.map((item) => item.platform + " " + Number(item.Positive || 0).toFixed(1) + "% positive").join(" | ")
        : "Platform comparison will appear after analytics load.";
    }

    function applyAnalyticsSummaryPresentation(role) {
      const resolved = normalizeAccessRole(role);
      const view = $("#view-analytics-summary");
      if (!view) return;
      const eyebrow = view.querySelector(".eyebrow");
      const title = view.querySelector(".view-title");
      const copy = view.querySelector(".view-copy");
      const snapshotLabel = view.querySelector(".about-sub");

      if (resolved === "marketing_staff") {
        if (eyebrow) eyebrow.textContent = "Market Signals";
        if (title) title.textContent = "Business Summary";
        if (copy) copy.textContent = "Brand score, sentiment mix, complaints, and market spread.";
        if (snapshotLabel) snapshotLabel.textContent = "Business Snapshot";
        return;
      }

      if (resolved === "analyst") {
        if (eyebrow) eyebrow.textContent = "Analysis";
        if (title) title.textContent = "Summary";
        if (copy) copy.textContent = "Key totals, sentiment mix, and complaint spread.";
        if (snapshotLabel) snapshotLabel.textContent = "Analysis Snapshot";
        return;
      }

      if (eyebrow) eyebrow.textContent = "Control Summary";
      if (title) title.textContent = "Summary";
      if (copy) copy.textContent = "Portfolio totals, risk spread, and monitoring context.";
      if (snapshotLabel) snapshotLabel.textContent = "Control Snapshot";
    }

    async function loadAdminModelPerformance() {
      if (normalizeAccessRole(state.userRole) !== "admin") return;
      try {
        const payload = await callApi("/admin/model-performance");
        state.modelMetrics = payload.metrics || null;
        state.modelTrainingAt = payload.last_training_at || "";
        renderAdminModelPerformance();
        renderAdminControlHub();
        renderAdminOps();
        renderRoleDashboardPanel();
      } catch (error) {
        if (handleAuthError(error)) return;
        state.modelMetrics = null;
        state.modelTrainingAt = "";
      }
    }

    function formatAdminTimestamp(value) {
      const parsed = value ? new Date(value) : null;
      if (!parsed || Number.isNaN(parsed.getTime())) return "Waiting";
      return parsed.toLocaleString();
    }

    function renderAdminControlHub() {
      if (normalizeAccessRole(state.userRole) !== "admin") return;
      $("#adminUsersCount").textContent = Number((state.users || []).length || 0).toLocaleString();
      $("#adminBrandsCount").textContent = Number((state.brands || []).length || 0).toLocaleString();
      $("#adminReviewsCount").textContent = Number(state.brandScore?.total_reviews || 0).toLocaleString();
      $("#adminModelAccuracy").textContent = state.modelMetrics && Number.isFinite(Number(state.modelMetrics.test_accuracy))
        ? (Number(state.modelMetrics.test_accuracy) * 100).toFixed(1) + "%"
        : "Waiting";
      $("#adminModelName").textContent = state.modelMetrics && state.modelMetrics.model
        ? String(state.modelMetrics.model)
        : "Latest model metrics will appear after admin data loads.";
      $("#adminTrainingTime").textContent = formatAdminTimestamp(state.modelTrainingAt);
      const pipelineReady = Boolean(state.modelMetrics && Number.isFinite(Number(state.modelMetrics.test_accuracy)));
      $("#adminPipelineStatus").textContent = pipelineReady ? "Healthy" : "Pending";
      $("#adminPipelineCopy").textContent = pipelineReady
        ? "Model metrics are available and the admin control pipeline looks healthy."
        : "Model metrics have not been loaded yet. Refresh model status to verify pipeline health.";
    }

    function renderAdminOps() {
      if (normalizeAccessRole(state.userRole) !== "admin") return;
      const title = $("#adminAlertsTitle");
      const copy = $("#adminAlertsCopy");
      const status = $("#pipelineActionStatus");
      const reviewCount = Number(state.brandScore?.total_reviews || 0);
      const modelAccuracy = Number(state.modelMetrics?.test_accuracy || 0);
      if (title) {
        if (modelAccuracy > 0 && modelAccuracy < 0.8) {
          title.textContent = "Model accuracy warning";
        } else if (Number(state.brandScore?.negative_pct || 0) >= 40) {
          title.textContent = "Complaint spike detected";
        } else {
          title.textContent = "System Status: Stable";
        }
      }
      if (copy) {
        if (modelAccuracy > 0 && modelAccuracy < 0.8) {
          copy.textContent = "Latest model accuracy is below the 80% checkpoint. Review training quality before depending on new outputs.";
        } else if (Number(state.brandScore?.negative_pct || 0) >= 40) {
          copy.textContent = "Negative sentiment is elevated across " + reviewCount.toLocaleString() + " reviews. Keep brand monitoring teams on alert.";
        } else {
          copy.textContent = "Users, model artifacts, and monitored brand coverage are currently in a stable operating range.";
        }
      }
      if (status) {
        status.textContent = state.modelMetrics
          ? "Pipeline status is ready. Last model training: " + formatAdminTimestamp(state.modelTrainingAt) + "."
          : "Model metrics are not available yet. Run preprocessing, features, and training to restore pipeline visibility.";
      }
      buildAdminNotifications();
      renderAdminSidePanel();
    }

    function buildAdminNotifications() {
      const notifications = [];
      const modelAccuracy = Number(state.modelMetrics?.test_accuracy || 0);
      const validationAccuracy = Number(state.modelMetrics?.validation_accuracy || 0);
      const negativePct = Number(state.brandScore?.negative_pct || 0);
      const reviewCount = Number(state.brandScore?.total_reviews || 0);

      if (!state.modelMetrics) {
        notifications.push({
          title: "Model metrics unavailable",
          level: "info",
          summary: "No model metrics are loaded. Refresh model status or run training to restore visibility."
        });
      } else {
        if (modelAccuracy > 0 && modelAccuracy < 0.8) {
          notifications.push({
            title: "Model accuracy warning",
            level: "warning",
            summary: "Latest test accuracy is " + (modelAccuracy * 100).toFixed(1) + "%. Review training quality before trusting new outputs."
          });
        }
        if (validationAccuracy > 0 && modelAccuracy > 0 && Math.abs(validationAccuracy - modelAccuracy) > 0.08) {
          notifications.push({
            title: "Validation gap detected",
            level: "warning",
            summary: "Validation and test accuracy differ noticeably. Check overfitting or dataset drift."
          });
        }
      }

      if (negativePct >= 40) {
        notifications.push({
          title: "Complaint spike detected",
          level: "critical",
          summary: "Negative sentiment reached " + negativePct.toFixed(1) + "% across " + reviewCount.toLocaleString() + " reviews."
        });
      }

      if ((state.users || []).length <= 1) {
        notifications.push({
          title: "Low user coverage",
          level: "info",
          summary: "Only " + Number((state.users || []).length || 0).toLocaleString() + " account is active. Add backup operator access if needed."
        });
      }

      if (!notifications.length) {
        notifications.push({
          title: "System stable",
          level: "success",
          summary: "No critical warnings detected. Users, model metrics, and monitored dataset are in a healthy state."
        });
      }

      state.adminNotifications = notifications;
      renderAdminNotifications();
      updateAdminNotificationBadge();
    }

    function updateAdminNotificationBadge() {
      const badge = $("#adminNotificationBadge");
      if (!badge) return;
      const activeCount = (state.adminNotifications || []).filter((item) => item.level !== "success").length;
      badge.textContent = String(activeCount);
      badge.classList.toggle("hidden", activeCount <= 0 || normalizeAccessRole(state.userRole) !== "admin");
    }

    function renderAdminNotifications() {
      const host = $("#adminNotificationsList");
      const headline = $("#notificationsHeadline");
      if (!host || !headline) return;
      const items = Array.isArray(state.adminNotifications) ? state.adminNotifications : [];
      const activeCount = items.filter((item) => item.level !== "success").length;
      headline.textContent = activeCount > 0
        ? activeCount + " active alert" + (activeCount === 1 ? "" : "s")
        : "No active alerts";
      host.innerHTML = items.map((item) => {
        const level = item.level || "info";
        const label = level === "critical"
          ? "Critical"
          : level === "warning"
            ? "Warning"
            : level === "success"
              ? "Stable"
              : "Info";
        const action = level === "critical"
          ? "Immediate review required"
          : level === "warning"
            ? "Review recommended"
            : level === "success"
              ? "No action needed"
              : "Check system state";
        return [
          '<article class="timeline-item admin-alert-card admin-alert-card--' + level + '">',
          '<div class="admin-alert-head">',
          '<span class="score-chip admin-alert-chip admin-alert-chip--' + level + '">' + label + "</span>",
          '<time>' + new Date().toLocaleString() + "</time>",
          "</div>",
          '<strong>' + item.title + "</strong>",
          '<p>' + item.summary + "</p>",
          '<div class="admin-alert-action">Action: ' + action + "</div>",
          "</article>"
        ].join("");
      }).join("");
    }

    function renderAdminSidePanel() {
      if (normalizeAccessRole(state.userRole) !== "admin") return;
      const alertCount = (state.adminNotifications || []).filter((item) => item.level !== "success").length;
      const userCount = Number((state.users || []).length || 0);
      const brandCount = Number((state.brands || []).length || 0);
      const reviewCount = Number(state.brandScore?.total_reviews || 0);
      const modelAccuracy = Number(state.modelMetrics?.test_accuracy || 0);
      const alertEl = $("#adminSideAlertCount");
      const userEl = $("#adminSideUserCount");
      const brandEl = $("#adminSideBrandCount");
      const copyEl = $("#adminSideSummaryCopy");
      const panelStatus = $("#panelStatusText");
      if (alertEl) alertEl.textContent = alertCount + (alertCount === 1 ? " alert" : " alerts");
      if (userEl) userEl.textContent = userCount.toLocaleString() + (userCount === 1 ? " user" : " users");
      if (brandEl) brandEl.textContent = brandCount.toLocaleString() + (brandCount === 1 ? " brand" : " brands");
      if (copyEl) {
        copyEl.textContent = alertCount > 0
          ? "Operational attention required. Review " + alertCount + " active alert" + (alertCount === 1 ? "" : "s") + ", validate model health, and confirm brand coverage before the next sync."
          : "System monitoring is stable across " + userCount.toLocaleString() + " users, " + brandCount.toLocaleString() + " brands, and " + reviewCount.toLocaleString() + " tracked reviews" + (modelAccuracy > 0 ? " with " + (modelAccuracy * 100).toFixed(1) + "% model accuracy." : ".");
      }
      if (panelStatus) panelStatus.textContent = alertCount > 0 ? "Admin Alerts" : "Admin Stable";
    }

    function renderAdminModelPerformance() {
      const metrics = state.modelMetrics || {};
      $("#modelPageName").textContent = metrics.model || "Waiting";
      $("#modelPageAccuracy").textContent = Number.isFinite(Number(metrics.test_accuracy))
        ? (Number(metrics.test_accuracy) * 100).toFixed(1) + "%"
        : "0%";
      $("#modelPageF1").textContent = Number.isFinite(Number(metrics.test_f1_macro))
        ? (Number(metrics.test_f1_macro) * 100).toFixed(1) + "%"
        : "0%";
      $("#modelPageValidation").textContent = Number.isFinite(Number(metrics.validation_accuracy))
        ? (Number(metrics.validation_accuracy) * 100).toFixed(1) + "%"
        : "0%";
      $("#modelPageLoss").textContent = Number.isFinite(Number(metrics.test_log_loss))
        ? Number(metrics.test_log_loss).toFixed(3)
        : "0.000";
      $("#modelPageTrainedAt").textContent = formatAdminTimestamp(state.modelTrainingAt);
    }

    async function runAdminPipelineAction(endpoint, button, idleLabel, workingLabel, successMessage) {
      if (normalizeAccessRole(state.userRole) !== "admin") return;
      setButtonLoading(button, true, idleLabel, workingLabel);
      $("#pipelineActionStatus").textContent = workingLabel;
      try {
        await callApi(endpoint, { method: "POST", timeoutMs: endpoint === "/train" ? 120000 : 30000 });
        $("#pipelineActionStatus").textContent = successMessage;
        toast(successMessage, "success");
        if (endpoint === "/train") {
          await loadAdminModelPerformance();
        }
      } catch (error) {
        if (handleAuthError(error)) return;
        $("#pipelineActionStatus").textContent = error.message || "Pipeline action failed.";
        toast(error.message || "Pipeline action failed.", "error");
      } finally {
        setButtonLoading(button, false, idleLabel);
      }
    }

    function renderSmartInsight() {
      const title = $("#dashboardInsightTitle");
      const copy = $("#dashboardInsightCopy");
      if (!title || !copy) return;
      const role = normalizeAccessRole(state.userRole);
      const score = state.brandScore || normalizeBrandScore({});
      const extremes = getScoreExtremes();
      const keywords = Array.isArray(state.keywords) ? state.keywords : [];
      const trends = Array.isArray(state.trends) ? state.trends : [];

      if (role === "admin") {
        title.textContent = "System oversight";
        copy.textContent = "Admin should focus on " + Number((state.users || []).length || 0).toLocaleString() + " accounts, " + Number((state.brands || []).length || 0).toLocaleString() + " tracked brands, and current platform readiness.";
        return;
      }

      if (role === "marketing_staff") {
        if (extremes.leader) {
          title.textContent = "Best-performing brand";
          copy.textContent = extremes.leader.brand + " currently leads the portfolio with a reputation score of " + extremes.leader.brand_reputation_score.toFixed(1) + ". Use it as the benchmark for campaign messaging.";
          return;
        }
        title.textContent = "Insight standby";
        copy.textContent = "Brand leadership insight will appear after brand analytics load.";
        return;
      }

      if (trends.length >= 2) {
        const current = trends[trends.length - 1] || {};
        const previous = trends[trends.length - 2] || {};
        const negativeDelta = Number(current.Negative || 0) - Number(previous.Negative || 0);
        if (negativeDelta > 1) {
          title.textContent = "Negative drift detected";
          copy.textContent = "Negative sentiment increased by " + negativeDelta.toFixed(1) + " points in the latest period. Validate the shift before drawing conclusions.";
          return;
        }
      }
      if (keywords[0]) {
        title.textContent = "Language signal";
        copy.textContent = "Keyword " + "#" + keywords[0].word + " is the strongest visible review signal in the current dataset. Use it to guide deeper analysis.";
        return;
      }
      title.textContent = "Analysis standby";
      copy.textContent = "Insight signal will appear after trend and keyword analytics load.";
    }

    function renderTrendReviewVolume() {
      const title = $("#trendReviewVolumeTitle");
      const copy = $("#trendReviewVolumeCopy");
      if (!title || !copy) return;
      const trends = getWindowedTrends();
      if (!Array.isArray(trends) || !trends.length) {
        title.textContent = "Review Volume";
        copy.textContent = "Review volume summary will appear after trend data loads.";
        return;
      }
      const latest = trends[trends.length - 1] || {};
      const previous = trends.length > 1 ? trends[trends.length - 2] || {} : null;
      const latestTotal = Number(latest.Positive || 0) + Number(latest.Neutral || 0) + Number(latest.Negative || 0);
      const previousTotal = previous ? Number(previous.Positive || 0) + Number(previous.Neutral || 0) + Number(previous.Negative || 0) : 0;
      const delta = latestTotal - previousTotal;
      const scope = state.trendBrand ? activeTrendBrandLabel() : "portfolio";
      title.textContent = "Review Volume: " + String(latest.period || "Latest");
      copy.textContent = scope + " captured " + latestTotal.toLocaleString() + " reviews in the latest visible period" +
        (previous ? " (" + (delta >= 0 ? "+" : "") + delta.toLocaleString() + " vs previous period)." : ".");
    }

    function setTrendDrilldownActive(sentiment) {
      state.trendDrilldownSentiment = sentiment || "";
      $$("#view-review-trends .trend-legend span[data-sentiment]").forEach((item) => {
        item.classList.toggle("is-active", item.dataset.sentiment === state.trendDrilldownSentiment);
      });
    }

    function renderTrendDrilldownSamples(samples, sentiment) {
      const title = $("#trendDrilldownTitle");
      const copy = $("#trendDrilldownCopy");
      const host = $("#trendReviewDrilldown");
      if (!title || !copy || !host) return;
      const scope = state.trendBrand ? activeTrendBrandLabel() : "all brands";
      title.textContent = sentiment + " Review Samples";
      if (!Array.isArray(samples) || !samples.length) {
        copy.textContent = "No matching review samples found for " + sentiment + " in " + scope + ".";
        host.innerHTML = '<div class="mini-note">No real review samples are available for this filter combination.</div>';
        return;
      }
      copy.textContent = "Showing real " + sentiment.toLowerCase() + " review samples for " + scope + " in the selected time window.";
      host.innerHTML = samples.map((item) => {
        const meta = [
          item.brand || "Unknown brand",
          item.platform || "Unknown platform",
          item.review_date || "Unknown date",
          item.rating ? "Rating " + item.rating : null
        ].filter(Boolean).join(" | ");
        const preview = String(item.review_text || "");
        const shortPreview = preview.length > 88 ? preview.slice(0, 88).trim() + "..." : preview;
        return [
          '<details class="review-drilldown-item" data-tone="' + sentiment + '"' + (samples.indexOf(item) === 0 ? " open" : "") + '>',
          '<summary>',
          '<div class="review-drilldown-head"><span>' + sentiment + '</span><span>' + meta + "</span></div>",
          '<div class="review-drilldown-preview"><p>"' + shortPreview.replace(/"/g, "&quot;") + '"</p><span class="review-drilldown-toggle">Expand</span></div>',
          '</summary>',
          '<div class="review-drilldown-body">',
          '<div class="review-drilldown-pillrow">',
          '<span>Brand: ' + (item.brand || "Unknown") + "</span>",
          '<span>Platform: ' + (item.platform || "Unknown") + "</span>",
          '<span>Date: ' + (item.review_date || "Unknown") + "</span>",
          (item.rating ? '<span>Rating: ' + item.rating + "</span>" : ""),
          '</div>',
          '<p class="review-drilldown-text">"' + preview.replace(/"/g, "&quot;") + '"</p>',
          '</div>',
          "</details>"
        ].join("");
      }).join("");
    }

    async function loadTrendDrilldown(sentiment) {
      const role = normalizeAccessRole(state.userRole);
      if (role !== "analyst" && role !== "admin") return;
      const title = $("#trendDrilldownTitle");
      const copy = $("#trendDrilldownCopy");
      const host = $("#trendReviewDrilldown");
      if (!title || !copy || !host) return;
      const chosen = String(sentiment || "").trim();
      if (!chosen) return;
      setTrendDrilldownActive(chosen);
      title.textContent = chosen + " Review Samples";
      copy.textContent = "Loading real review samples...";
      host.innerHTML = '<div class="mini-note">Fetching matching reviews from the prediction dataset.</div>';
      try {
        const params = new URLSearchParams({
          sentiment: chosen,
          months: String(state.trendWindow || "all"),
          limit: "5"
        });
        if (state.trendBrand) params.set("brand", state.trendBrand);
        const payload = await callApi("/dashboard/reviews?" + params.toString());
        renderTrendDrilldownSamples(Array.isArray(payload.samples) ? payload.samples : [], chosen);
      } catch (error) {
        if (handleAuthError(error)) return;
        copy.textContent = "Unable to load review samples: " + (error.message || "request failed") + ".";
        host.innerHTML = '<div class="mini-note">Review drill-down is unavailable right now.</div>';
      }
    }

    function downloadBlob(filename, content, type) {
      const blob = new Blob([content], { type });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    }

    function escapeHtml(value) {
      return String(value == null ? "" : value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    function buildHtmlReport(title, sections) {
      const renderedSections = (Array.isArray(sections) ? sections : []).map((section) => {
        const heading = section && section.heading ? '<h2>' + escapeHtml(section.heading) + '</h2>' : "";
        const body = Array.isArray(section?.rows)
          ? section.rows.map((row) => '<li>' + escapeHtml(row) + '</li>').join("")
          : "";
        return '<section class="report-section">' + heading + '<ul>' + body + '</ul></section>';
      }).join("");
      return [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        "<title>" + escapeHtml(title) + "</title>",
        "<style>",
        "body{margin:0;padding:40px;background:#07162f;color:#eaf1ff;font:16px/1.6 'Segoe UI',Arial,sans-serif;}",
        ".report{max-width:960px;margin:0 auto;padding:32px;border:1px solid rgba(103,211,255,.22);border-radius:24px;background:linear-gradient(180deg,rgba(10,27,58,.98),rgba(7,22,47,.98));box-shadow:0 24px 70px rgba(0,0,0,.32);}",
        "h1{margin:0 0 10px;font-size:36px;line-height:1.1;}",
        ".report-meta{display:flex;gap:12px;flex-wrap:wrap;margin:0 0 24px;padding:0;list-style:none;color:#9fb3d9;font-size:14px;letter-spacing:.08em;text-transform:uppercase;}",
        ".report-meta li{padding:8px 12px;border:1px solid rgba(103,211,255,.18);border-radius:999px;background:rgba(20,45,86,.55);}",
        ".report-section{margin-top:24px;padding-top:20px;border-top:1px solid rgba(103,211,255,.14);}",
        ".report-section h2{margin:0 0 12px;font-size:18px;letter-spacing:.08em;text-transform:uppercase;color:#67d3ff;}",
        ".report-section ul{margin:0;padding-left:18px;}",
        ".report-section li{margin:0 0 8px;}",
        "</style></head><body>",
        '<main class="report"><h1>' + escapeHtml(title) + "</h1>",
        '<ul class="report-meta"><li>BrandPulse AI</li><li>Exported Report</li><li>' + escapeHtml(new Date().toLocaleString()) + "</li></ul>",
        renderedSections,
        "</main></body></html>"
      ].join("");
    }

    function exportTrendCsv() {
      const trends = getWindowedTrends();
      if (!trends.length) {
        toast("No trend data available to export.", "error");
        return;
      }
      const rows = ["period,positive,neutral,negative,total"];
      trends.forEach((row) => {
        const positive = Number(row.Positive || 0);
        const neutral = Number(row.Neutral || 0);
        const negative = Number(row.Negative || 0);
        rows.push([row.period, positive, neutral, negative, positive + neutral + negative].join(","));
      });
      downloadBlob("trend-report.csv", rows.join("\n"), "text/csv;charset=utf-8");
      toast("Trend CSV downloaded.", "success");
    }

    function exportTrendReport() {
      const score = state.brandScore || normalizeBrandScore({});
      const trends = getWindowedTrends();
      if (!trends.length) {
        toast("No trend data available to export.", "error");
        return;
      }
      const latest = trends[trends.length - 1] || {};
      const report = buildHtmlReport("Trend Intelligence Report", [
        {
          heading: "Scope",
          rows: [
            "Role: Analyst",
            "Brand scope: " + (state.trendBrand ? activeTrendBrandLabel() : "All brands"),
            "Time window: " + ($("#trendWindowSelect")?.selectedOptions?.[0]?.textContent || "All months"),
            "Latest visible period: " + String(latest.period || "N/A")
          ]
        },
        {
          heading: "Summary Metrics",
          rows: [
            "Total reviews: " + Number(score.total_reviews || 0).toLocaleString(),
            "Positive share: " + Number(score.positive_pct || 0).toFixed(1) + "%",
            "Neutral share: " + Number(score.neutral_pct || 0).toFixed(1) + "%",
            "Negative share: " + Number(score.negative_pct || 0).toFixed(1) + "%",
            "Brand score: " + Number(score.brand_reputation_score || 0).toFixed(1)
          ]
        },
        {
          heading: "Trend Signals",
          rows: [
            ($("#trendMomentumTitle")?.textContent || "Sentiment Momentum") + " - " + ($("#trendMomentumCopy")?.textContent || ""),
            ($("#trendMonthlyCompareTitle")?.textContent || "Monthly Comparison") + " - " + ($("#trendMonthlyCompareCopy")?.textContent || ""),
            ($("#trendReviewVolumeTitle")?.textContent || "Review Volume") + " - " + ($("#trendReviewVolumeCopy")?.textContent || "")
          ]
        }
      ]);
      downloadBlob("trend-report.html", report, "text/html;charset=utf-8");
      toast("Trend HTML report downloaded.", "success");
    }

    function exportTrendPdf() {
      if (!getWindowedTrends().length) {
        toast("No trend data available to print.", "error");
        return;
      }
      window.print();
      toast("Print dialog opened for PDF export.", "info");
    }

    function customerVoiceWindowLabel() {
      const select = $("#customerVoiceWindowSelect");
      return (select && select.selectedOptions && select.selectedOptions[0] ? String(select.selectedOptions[0].textContent || "").trim() : "All months") || "All months";
    }

    function getCustomerVoiceBrands() {
      const selectedBrand = String(state.customerVoiceBrand || "").trim();
      const brands = Array.isArray(state.brands) ? state.brands.slice() : [];
      if (!selectedBrand) return brands;
      return brands.filter((item) => String(item.brand || "").trim() === selectedBrand);
    }

    function populateCustomerVoiceBrandSelect(brands) {
      const select = $("#customerVoiceBrandSelect");
      if (!select) return;
      const previous = state.customerVoiceBrand || select.value || "";
      const options = (Array.isArray(brands) ? brands : [])
        .map((item) => String(item.brand || "").trim())
        .filter(Boolean)
        .sort((a, b) => a.localeCompare(b))
        .map((brand) => '<option value="' + brand + '">' + brand + "</option>")
        .join("");
      select.innerHTML = '<option value="">All brands</option>' + options;
      select.value = previous && Array.from(select.options).some((option) => option.value === previous) ? previous : "";
      state.customerVoiceBrand = select.value || "";
    }

    function renderCustomerVoiceInsight() {
      const findingTitle = $("#customerVoiceFindingTitle");
      const findingCopy = $("#customerVoiceFindingCopy");
      const actionTitle = $("#customerVoiceActionTitle");
      const actionCopy = $("#customerVoiceActionCopy");
      if (!findingTitle || !findingCopy || !actionTitle || !actionCopy) return;
      const selectedBrand = String(state.customerVoiceBrand || "").trim();
      const windowLabel = customerVoiceWindowLabel();
      const brands = getCustomerVoiceBrands();
      if (!brands.length) {
        findingTitle.textContent = "Key Finding";
        findingCopy.textContent = "No brand data is available for the current selection.";
        actionTitle.textContent = "Recommended Action";
        actionCopy.textContent = "Reset the brand filter or refresh analytics data.";
        return;
      }
      const ranked = brands
        .map((item) => ({ ...item, csat: calculateCsat(item) }))
        .sort((a, b) => Number(b.negative_pct || 0) - Number(a.negative_pct || 0));
      const focus = ranked[0];
      const topTopic = Array.isArray(state.customerVoiceKeywords) && state.customerVoiceKeywords[0]
        ? "#" + state.customerVoiceKeywords[0].word
        : "top complaint topics";
      findingTitle.textContent = selectedBrand ? "Key Finding: " + selectedBrand : "Key Finding";
      findingCopy.textContent = focus.brand + " is carrying " + Number(focus.negative_pct || 0).toFixed(1) + "% negative share in the " + windowLabel.toLowerCase() + " view, while CSAT stands at " + calculateCsat(focus).toFixed(0) + "/100.";
      actionTitle.textContent = "Recommended Action";
      actionCopy.textContent = "Investigate " + topTopic + " first and review low-CSAT brands before the next reporting cycle.";
    }

    function exportCustomerVoiceCsv() {
      const brands = getCustomerVoiceBrands()
        .map((item) => ({ ...item, csat: calculateCsat(item) }))
        .sort((a, b) => b.csat - a.csat);
      if (!brands.length) {
        toast("No customer voice data available to export.", "error");
        return;
      }
      const rows = ["brand,csat,positive,neutral,negative,total_reviews"];
      brands.forEach((row) => {
        rows.push([
          row.brand,
          row.csat.toFixed(1),
          Number(row.positive_pct || 0).toFixed(1),
          Number(row.neutral_pct || 0).toFixed(1),
          Number(row.negative_pct || 0).toFixed(1),
          Number(row.total_reviews || 0)
        ].join(","));
      });
      downloadBlob("customer-voice.csv", rows.join("\n"), "text/csv;charset=utf-8");
      toast("Customer voice CSV downloaded.", "success");
    }

    function exportCustomerVoiceReport() {
      const brands = getCustomerVoiceBrands()
        .map((item) => ({ ...item, csat: calculateCsat(item) }))
        .sort((a, b) => b.csat - a.csat);
      if (!brands.length) {
        toast("No customer voice data available to export.", "error");
        return;
      }
      const complaintTopics = ((Array.isArray(state.customerVoiceKeywords) ? state.customerVoiceKeywords.slice(0, 6) : [])
        .map((item) => "#" + String(item.word || "").trim())
        .filter(Boolean));
      const report = buildHtmlReport("Customer Voice Report", [
        {
          heading: "Scope",
          rows: [
            "Role: Analyst",
            "Brand scope: " + (state.customerVoiceBrand || "All brands"),
            "Time window: " + customerVoiceWindowLabel()
          ]
        },
        {
          heading: "Priority Insight",
          rows: [
            ($("#customerVoiceFindingTitle")?.textContent || "Key Finding") + " - " + ($("#customerVoiceFindingCopy")?.textContent || ""),
            ($("#customerVoiceActionTitle")?.textContent || "Recommended Action") + " - " + ($("#customerVoiceActionCopy")?.textContent || "")
          ]
        },
        {
          heading: "Complaint Topics",
          rows: complaintTopics.length ? complaintTopics : ["No complaint topics available for the current selection."]
        },
        {
          heading: "CSAT Snapshot",
          rows: brands.slice(0, 6).map((item) => (
            item.brand + ": CSAT " + item.csat.toFixed(0) + "/100 | Positive " + Number(item.positive_pct || 0).toFixed(1) + "% | Negative " + Number(item.negative_pct || 0).toFixed(1) + "%"
          ))
        }
      ]);
      downloadBlob("customer-voice-report.html", report, "text/html;charset=utf-8");
      toast("Customer voice HTML report downloaded.", "success");
    }

    function exportCustomerVoicePdf() {
      if (!getCustomerVoiceBrands().length) {
        toast("No customer voice data available to print.", "error");
        return;
      }
      window.print();
      toast("Print dialog opened for customer voice export.", "info");
    }

    function updateDistributionChart(score) {
      const values = [
        { id: "Positive", value: clamp(score.positive_pct || 0, 0, 100) },
        { id: "Neutral", value: clamp(score.neutral_pct || 0, 0, 100) },
        { id: "Negative", value: clamp(score.negative_pct || 0, 0, 100) }
      ];
      values.forEach((item) => {
        $("#dist" + item.id + "Bar").style.width = item.value + "%";
        $("#dist" + item.id + "Value").textContent = item.value.toFixed(1) + "%";
      });
      $("#distCaption").textContent = "Sentiment mix across " + Number(score.total_reviews || 0).toLocaleString() + " processed reviews.";
    }

    function riskMeta(score, negativePct) {
      if (score >= 45 && negativePct < 25) return { label: "Low Risk", className: "risk-low" };
      if (score < 10 || negativePct >= 40) return { label: "High Risk", className: "risk-high" };
      return { label: "Medium Risk", className: "risk-medium" };
    }

    function buildPros(row) {
      const pros = [];
      if (row.positive_pct >= 65) pros.push("Strong positive sentiment");
      if (row.brand_reputation_score >= 40) pros.push("Healthy reputation score");
      if (row.negative_pct <= 20) pros.push("Low complaint pressure");
      if (row.total_reviews >= 5000) pros.push("Large review coverage");
      return pros.length ? pros : ["Stable overall sentiment", "Actionable baseline for growth"];
    }

    function buildCons(row) {
      const cons = [];
      if (row.negative_pct >= 35) cons.push("High negative sentiment");
      if (row.brand_reputation_score < 15) cons.push("Weak reputation score");
      if (row.positive_pct < 45) cons.push("Positive momentum is limited");
      if (row.total_reviews < 1000) cons.push("Lower review volume confidence");
      return cons.length ? cons : ["No major structural risk detected", "Continue monitoring for drift"];
    }

    function buildWhyText(row) {
      if (row.brand_reputation_score >= 45) {
        return row.brand + " is performing well because positive sentiment materially outweighs negative reviews, which keeps reputation risk contained.";
      }
      if (row.brand_reputation_score < 10) {
        return row.brand + " is high risk because negative sentiment is too close to or above the positive share, pulling the reputation score down.";
      }
      return row.brand + " is in a mixed zone. Positive reviews still support the brand, but negative pressure is large enough to reduce trust and future conversion.";
    }

    function buildRecommendation(row) {
      if (row.brand_reputation_score >= 45) {
        return "Recommendation: scale what is already working, highlight top positive themes in campaigns, and defend the current service standard to avoid backslide.";
      }
      if (row.brand_reputation_score < 10) {
        return "Recommendation: prioritize complaint clusters, fix service or quality pain points first, and avoid aggressive promotion until negative drivers are reduced.";
      }
      return "Recommendation: improve response quality, reinforce the strongest positive themes, and target the top negative friction points before the next campaign push.";
    }

    function getScoreExtremes() {
      if (!Array.isArray(state.brands) || !state.brands.length) return { leader: null, lagger: null };
      const sorted = state.brands.slice().sort((a, b) => b.brand_reputation_score - a.brand_reputation_score);
      return {
        leader: sorted[0] || null,
        lagger: sorted[sorted.length - 1] || null
      };
    }

    function renderAnalyticsSummaryContext() {
      const score = state.brandScore || normalizeBrandScore({});
      const extremes = getScoreExtremes();
      const risk = riskMeta(score.brand_reputation_score, score.negative_pct);

      $("#summaryTotalReviews").textContent = Number(score.total_reviews || 0).toLocaleString();
      $("#summaryPositiveShare").textContent = Number(score.positive_pct || 0).toFixed(1) + "%";
      $("#summaryNeutralShare").textContent = Number(score.neutral_pct || 0).toFixed(1) + "%";
      $("#summaryNegativeShare").textContent = Number(score.negative_pct || 0).toFixed(1) + "%";
      $("#summaryRiskChip").textContent = risk.label;
      $("#summaryRiskChip").className = "score-chip " + risk.className;

      $("#summaryPositiveBar").style.width = clamp(score.positive_pct, 0, 100) + "%";
      $("#summaryNeutralBar").style.width = clamp(score.neutral_pct, 0, 100) + "%";
      $("#summaryNegativeBar").style.width = clamp(score.negative_pct, 0, 100) + "%";
      $("#summaryPositiveBarText").textContent = Number(score.positive_pct || 0).toFixed(1) + "%";
      $("#summaryNeutralBarText").textContent = Number(score.neutral_pct || 0).toFixed(1) + "%";
      $("#summaryNegativeBarText").textContent = Number(score.negative_pct || 0).toFixed(1) + "%";

      if (extremes.leader && extremes.lagger) {
        $("#summaryLeaderBrand").textContent = extremes.leader.brand + " (" + extremes.leader.brand_reputation_score.toFixed(1) + ")";
        $("#summaryLaggerBrand").textContent = extremes.lagger.brand + " (" + extremes.lagger.brand_reputation_score.toFixed(1) + ")";
        $("#summaryScoreSpread").textContent = (extremes.leader.brand_reputation_score - extremes.lagger.brand_reputation_score).toFixed(1) + " points";
        $("#summaryKeyMessage").textContent = extremes.leader.brand + " leads on reputation score, while " + extremes.lagger.brand + " needs stronger negative-sentiment control to close the gap.";
      } else {
        $("#summaryLeaderBrand").textContent = "Not available";
        $("#summaryLaggerBrand").textContent = "Not available";
        $("#summaryScoreSpread").textContent = "Not available";
        $("#summaryKeyMessage").textContent = "Brand ranking will appear after `/dashboard/brands` data loads.";
      }

      if (Array.isArray(state.trends) && state.trends.length >= 2) {
        const current = state.trends[state.trends.length - 1] || {};
        const previous = state.trends[state.trends.length - 2] || {};
        const positiveDelta = Number(current.Positive || 0) - Number(previous.Positive || 0);
        const negativeDelta = Number(current.Negative || 0) - Number(previous.Negative || 0);
        if (positiveDelta > 1 && negativeDelta <= 0) {
          $("#summaryTrendPulse").textContent = "Improving: positive share increased by " + positiveDelta.toFixed(1) + " points with stable or lower negative pressure.";
        } else if (negativeDelta > 1) {
          $("#summaryTrendPulse").textContent = "Warning: negative share increased by " + negativeDelta.toFixed(1) + " points in the latest period.";
        } else {
          $("#summaryTrendPulse").textContent = "Stable: no material shift in sentiment pressure between the last two periods.";
        }
      } else {
        $("#summaryTrendPulse").textContent = "Trend pulse will appear after trend data loads.";
      }

      const keywordPills = (Array.isArray(state.keywords) ? state.keywords : [])
        .slice(0, 6)
        .map((item) => String(item.word || "").trim())
        .filter(Boolean)
        .map((word) => "#" + word);
      renderPillList("summaryKeywordPills", keywordPills.length ? keywordPills : ["Waiting for keyword analytics"]);

      const priorities = [];
      if (score.negative_pct >= 40) priorities.push("Cut top negative drivers in complaints immediately");
      if (score.positive_pct < 55) priorities.push("Increase positive-review generation programs");
      if (extremes.lagger) priorities.push("Run deep-dive recovery plan for " + extremes.lagger.brand);
      if (Array.isArray(state.trends) && state.trends.length >= 2) {
        const current = state.trends[state.trends.length - 1] || {};
        const previous = state.trends[state.trends.length - 2] || {};
        if ((Number(current.Negative || 0) - Number(previous.Negative || 0)) > 1) {
          priorities.push("Escalate if negative trend persists in next cycle");
        }
      }
      if (!priorities.length) priorities.push("Maintain current service quality and monitor drift weekly");
      renderPillList("summaryPriorityPills", priorities.slice(0, 4));
      renderSummaryDeepIntelligence();
    }

    function renderPillList(hostId, items, toneClass) {
      const host = $("#" + hostId);
      host.innerHTML = items.map((item) => '<span class="' + (toneClass || "") + '">' + item + "</span>").join("");
    }

    function formatRoleCards(items) {
      return (items || []).map((item) => {
        const className = item.view ? "role-mini-card is-link" : "role-mini-card";
        const attrs = item.view ? ' data-view="' + item.view + '" role="button" tabindex="0"' : "";
        return [
          '<article class="' + className + '"' + attrs + '>',
          '<span class="role-mini-label">' + item.label + "</span>",
          '<strong class="role-mini-value">' + item.value + "</strong>",
          '<p class="role-mini-copy">' + item.copy + "</p>",
          item.view ? '<span class="role-mini-action">View Details</span>' : "",
          "</article>"
        ].join("");
      }).join("");
    }

    function renderRoleDashboardPanel() {
      const role = normalizeAccessRole(state.userRole);
      const score = state.brandScore || normalizeBrandScore({});
      const extremes = getScoreExtremes();
      const currentTrend = Array.isArray(state.trends) && state.trends.length ? state.trends[state.trends.length - 1] : null;
      const previousTrend = Array.isArray(state.trends) && state.trends.length > 1 ? state.trends[state.trends.length - 2] : null;
      const negativeDelta = currentTrend && previousTrend
        ? Number(currentTrend.Negative || 0) - Number(previousTrend.Negative || 0)
        : 0;
      const risk = riskMeta(score.brand_reputation_score, score.negative_pct);

      let eyebrow = "Role View";
      let title = "Operational Overview";
      let copy = "Key metrics will appear here.";
      let cards = [];

      if (role === "admin") {
        eyebrow = "System Control";
        title = "Admin Control Snapshot";
        copy = "Access, readiness, and oversight.";
        cards = [
          {
            label: "Active Users",
            value: String((state.users || []).length || 0),
            copy: "Current accounts."
          },
          {
            label: "Tracked Brands",
            value: String((state.brands || []).length || 0),
            copy: "Covered brands."
          },
          {
            label: "Platform Status",
            value: risk.label === "High Risk" ? "Watch" : "Ready",
            copy: "Current system state."
          },
          {
            label: "Model Accuracy",
            value: state.modelMetrics && Number.isFinite(Number(state.modelMetrics.test_accuracy))
              ? (Number(state.modelMetrics.test_accuracy) * 100).toFixed(1) + "%"
              : "Waiting",
            copy: state.modelMetrics && state.modelMetrics.model
              ? String(state.modelMetrics.model) + " test accuracy."
              : "Model metrics pending."
          }
        ];
      } else if (role === "marketing_staff") {
        eyebrow = "Brand Monitoring";
        title = "Marketing Snapshot";
        copy = "Brand score, ranking, comparison, and signal.";
        const comparePair = extremes.leader && extremes.needsAttention
          ? extremes.leader.brand + " vs " + extremes.needsAttention.brand
          : (extremes.leader ? extremes.leader.brand + " lead" : "Waiting");
        cards = [
          {
            label: "Brand Score",
            value: Number(score.brand_reputation_score || 0).toFixed(1),
            copy: "Current score.",
            view: "brand-insights"
          },
          {
            label: "Leaderboard",
            value: extremes.leader ? extremes.leader.brand : "Waiting",
            copy: extremes.leader ? "Top-ranked brand." : "Waiting",
            view: "brand-insights"
          },
          {
            label: "Comparison",
            value: comparePair,
            copy: "Competitor view.",
            view: "brand-comparison"
          },
          {
            label: "Insight Signal",
            value: Array.isArray(state.keywords) && state.keywords[0] ? "#" + state.keywords[0].word : "Waiting",
            copy: "Current keyword cue.",
            view: "analytics-summary"
          },
          {
            label: "Alert",
            value: risk.label,
            copy: "Current warning state.",
            view: "brand-insights"
          }
        ];
      } else {
        eyebrow = "Analysis";
        title = "Analyst Snapshot";
        copy = "Trends, keywords, complaints, and volume.";
        const complaintTopic = Array.isArray(state.customerVoiceKeywords) && state.customerVoiceKeywords[0]
          ? "#" + state.customerVoiceKeywords[0].word
          : (Array.isArray(state.keywords) && state.keywords[0] ? "#" + state.keywords[0].word : "Waiting");
        cards = [
          {
            label: "Review Trends",
            value: Array.isArray(state.trends) ? String(state.trends.length || 0) + " months" : "0 months",
            copy: "Loaded months.",
            view: "review-trends"
          },
          {
            label: "Keyword Analysis",
            value: Array.isArray(state.keywords) && state.keywords[0]
              ? String(state.keywords[0].word || "").replace(/^#/, "").replace(/^\w/, (char) => char.toUpperCase())
              : "Waiting",
            copy: "Top keyword.",
            view: "keyword-frequency"
          },
          {
            label: "Complaint Intel",
            value: complaintTopic && complaintTopic !== "Waiting"
              ? complaintTopic.replace(/^#/, "").replace(/^\w/, (char) => char.toUpperCase()) + " complaints"
              : "Waiting",
            copy: "Top complaint.",
            view: "customer-intelligence"
          },
          {
            label: "Review Volume",
            value: Number(score.total_reviews || 0).toLocaleString(),
            copy: "Review count.",
            view: "review-trends"
          }
        ];
      }

      $("#roleDashboardEyebrow").textContent = eyebrow;
      $("#roleDashboardTitle").textContent = title;
      $("#roleDashboardCopy").textContent = copy;
      $("#roleDashboardCards").innerHTML = formatRoleCards(cards);
    }

    function renderAnalystFocusPanel() {
      const title = $("#analystFocusTitle");
      const metric = $("#analystFocusMetric");
      const copy = $("#analystFocusCopy");
      const tagA = $("#analystFocusTagA");
      const tagB = $("#analystFocusTagB");
      const tagC = $("#analystFocusTagC");
      const keywordTitle = $("#analystKeywordSpotlight");
      const keywordCopy = $("#analystKeywordSpotlightCopy");
      const complaintTitle = $("#analystComplaintSpotlight");
      const complaintCopy = $("#analystComplaintSpotlightCopy");
      if (!title || !metric || !copy || !tagA || !tagB || !tagC || !keywordTitle || !keywordCopy || !complaintTitle || !complaintCopy) return;

      const trends = Array.isArray(state.trends) ? state.trends : [];
      const current = trends.length ? trends[trends.length - 1] : null;
      const previous = trends.length > 1 ? trends[trends.length - 2] : null;
      const negativeDelta = current && previous ? Number(current.Negative || 0) - Number(previous.Negative || 0) : 0;
      const topKeyword = Array.isArray(state.keywords) && state.keywords[0] ? String(state.keywords[0].word || "") : "";
      const topComplaint = Array.isArray(state.customerVoiceKeywords) && state.customerVoiceKeywords[0] ? String(state.customerVoiceKeywords[0].word || "") : "";

      title.textContent = negativeDelta > 0
        ? "Negative review volume is rising."
        : negativeDelta < 0
          ? "Negative review volume is cooling."
          : "Trend movement is stable.";
      metric.textContent = (negativeDelta > 0 ? "+" : "") + Number(negativeDelta || 0).toFixed(0);
      copy.textContent = trends.length
        ? "Latest period change compared with the previous month window."
        : "Load analytics to reveal the dominant shift in review behaviour.";
      tagA.textContent = trends.length ? (current ? String(current.period || "Trend") : "Trend") : "Trend";
      tagB.textContent = topKeyword ? "#" + topKeyword : "Keyword";
      tagC.textContent = topComplaint ? "#" + topComplaint : "Complaint";

      keywordTitle.textContent = topKeyword ? topKeyword.replace(/^\w/, (char) => char.toUpperCase()) : "Waiting";
      keywordCopy.textContent = topKeyword
        ? "Top keyword from the current analyst keyword view."
        : "Top keyword signal will appear here.";

      complaintTitle.textContent = topComplaint ? topComplaint.replace(/^\w/, (char) => char.toUpperCase()) : "Waiting";
      complaintCopy.textContent = topComplaint
        ? "Top complaint theme from customer voice."
        : "Top complaint theme will appear here.";
    }

    function populateTrendBrandSelect(brands) {
      const select = $("#trendBrandSelect");
      if (!select) return;
      const trendReadyBrands = brands.filter((item) => item.has_trend_data !== false);
      const sourceBrands = trendReadyBrands.length ? trendReadyBrands : brands;
      const previous = state.trendBrand || select.value || "";
      const options = sourceBrands
        .map((item) => '<option value="' + item.brand + '">' + item.brand + "</option>")
        .join("");
      select.innerHTML = '<option value="">All brands</option>' + options;
      const available = new Set(sourceBrands.map((item) => item.brand));
      const next = available.has(previous) ? previous : "";
      select.value = next;
      state.trendBrand = next;
    }

    function renderBrandSelectors(brands) {
      const sorted = brands.slice().sort((a, b) => b.brand_reputation_score - a.brand_reputation_score);
      const insightSelect = $("#brandInsightSelect");
      const compareASelect = $("#compareBrandA");
      const compareBSelect = $("#compareBrandB");

      const previousInsight = insightSelect.value;
      const previousCompareA = compareASelect.value;
      const previousCompareB = compareBSelect.value;

      const brandOptions = sorted
        .map((item) => '<option value="' + item.brand + '">' + item.brand + "</option>")
        .join("");

      insightSelect.innerHTML = '<option value="">Select a brand</option>' + (brandOptions || "");
      compareASelect.innerHTML = '<option value="">Select brand A</option>' + (brandOptions || "");
      compareBSelect.innerHTML = '<option value="">Select brand B</option>' + (brandOptions || "");

      const available = new Set(sorted.map((item) => item.brand));
      insightSelect.value = available.has(previousInsight) ? previousInsight : "";
      compareASelect.value = available.has(previousCompareA) ? previousCompareA : "";
      compareBSelect.value = available.has(previousCompareB) ? previousCompareB : "";
      populateTrendBrandSelect(sorted);
      populateCustomerVoiceBrandSelect(sorted);
    }

    function getBrandByName(name) {
      return state.brands.find((item) => item.brand === name) || null;
    }

    function renderSimilarBrands(items) {
      const host = $("#similarBrandList");
      if (!Array.isArray(items) || !items.length) {
        host.innerHTML = '<div class="mini-note">No similar brands available.</div>';
        return;
      }

      host.innerHTML = items.map((item) => {
        const metrics = item.metrics || item;
        const risk = item.risk || riskMeta(metrics.brand_reputation_score, metrics.negative_pct);
        return [
          '<div class="similar-item">',
          '<div><strong>' + item.brand + '</strong><span>Score ' + Number(metrics.brand_reputation_score || 0).toFixed(1) + ' • Positive ' + Number(metrics.positive_pct || 0).toFixed(1) + '%</span></div>',
          '<span class="score-chip ' + (risk.level ? 'risk-' + risk.level : risk.className) + '">' + risk.label + '</span>',
          '</div>'
        ].join("");
      }).join("");
    }

    function clearBrandInsights(message) {
      $("#insightScoreValue").textContent = "0.0";
      $("#insightRiskChip").textContent = "No data";
      $("#insightRiskChip").className = "score-chip risk-medium";
      renderBrandEarlyWarning(null);
      $("#insightWhyText").textContent = message || "Select a brand to view insights.";
      $("#insightRecommendation").textContent = "Choose a brand from the dropdown to load reputation details.";
      renderPillList("insightProsList", []);
      renderPillList("insightConsList", []);
      $("#similarBrandList").innerHTML = '<div class="mini-note">Select a brand to view similar brands.</div>';
    }

    async function renderBrandInsights() {
      const selectedBrand = $("#brandInsightSelect").value;
      const row = getBrandByName(selectedBrand);
      const requestSeq = ++state.insightRequestSeq;
      if (!row) {
        clearBrandInsights(
          state.brands.length
            ? "Select a brand to view insights."
            : "No brand data available yet."
        );
        return;
      }

      try {
        const [insightsPayload, similarPayload] = await Promise.all([
          callApi("/dashboard/insights?brand=" + encodeURIComponent(row.brand)),
          callApi("/dashboard/similar?brand=" + encodeURIComponent(row.brand) + "&limit=3")
        ]);
        if (requestSeq !== state.insightRequestSeq) return;

        const metrics = normalizeBrandRow(insightsPayload.metrics || row);
        const risk = insightsPayload.risk || riskMeta(metrics.brand_reputation_score, metrics.negative_pct);
        $("#insightScoreValue").textContent = metrics.brand_reputation_score.toFixed(1);
        $("#insightRiskChip").textContent = risk.label;
        $("#insightRiskChip").className = "score-chip " + (risk.level ? "risk-" + risk.level : risk.className);
        renderBrandEarlyWarning(metrics);
        $("#insightWhyText").textContent = insightsPayload.why || buildWhyText(metrics);
        $("#insightRecommendation").textContent = insightsPayload.recommendation || buildRecommendation(metrics);
        renderPillList("insightProsList", insightsPayload.pros || buildPros(metrics));
        renderPillList("insightConsList", insightsPayload.cons || buildCons(metrics));
        renderSimilarBrands(similarPayload.similar || []);
      } catch (error) {
        if (requestSeq !== state.insightRequestSeq) return;
        if (handleAuthError(error)) return;
        const risk = riskMeta(row.brand_reputation_score, row.negative_pct);
        $("#insightScoreValue").textContent = row.brand_reputation_score.toFixed(1);
        $("#insightRiskChip").textContent = risk.label;
        $("#insightRiskChip").className = "score-chip " + risk.className;
        renderBrandEarlyWarning(row);
        $("#insightWhyText").textContent = buildWhyText(row);
        $("#insightRecommendation").textContent = buildRecommendation(row);
        renderPillList("insightProsList", buildPros(row));
        renderPillList("insightConsList", buildCons(row));
        renderSimilarBrands([]);
      }
    }

    function clearBrandComparison(message) {
      $("#compareScoreA").style.width = "0%";
      $("#compareScoreB").style.width = "0%";
      $("#comparePositiveA").style.width = "0%";
      $("#comparePositiveB").style.width = "0%";
      $("#compareNegativeA").style.width = "0%";
      $("#compareNegativeB").style.width = "0%";
      $("#compareScoreText").textContent = "0.0 vs 0.0";
      $("#comparePositiveText").textContent = "0.0% vs 0.0%";
      $("#compareNegativeText").textContent = "0.0% vs 0.0%";
      $("#compareSummary").textContent = message || "Choose two brands to compare advantage, risk, and sentiment balance.";
    }

    async function renderBrandComparison() {
      const selectedA = $("#compareBrandA").value;
      const selectedB = $("#compareBrandB").value;
      const brandA = getBrandByName(selectedA);
      const brandB = getBrandByName(selectedB);
      const requestSeq = ++state.compareRequestSeq;
      if (!brandA || !brandB) {
        clearBrandComparison();
        return;
      }

      try {
        const payload = await callApi(
          "/dashboard/compare?brand_a=" + encodeURIComponent(brandA.brand) + "&brand_b=" + encodeURIComponent(brandB.brand)
        );
        if (requestSeq !== state.compareRequestSeq) return;
        const left = normalizeBrandRow(payload.brand_a || brandA);
        const right = normalizeBrandRow(payload.brand_b || brandB);
        $("#compareScoreA").style.width = clamp(left.brand_reputation_score, 0, 100) + "%";
        $("#compareScoreB").style.width = clamp(right.brand_reputation_score, 0, 100) + "%";
        $("#comparePositiveA").style.width = clamp(left.positive_pct, 0, 100) + "%";
        $("#comparePositiveB").style.width = clamp(right.positive_pct, 0, 100) + "%";
        $("#compareNegativeA").style.width = clamp(left.negative_pct, 0, 100) + "%";
        $("#compareNegativeB").style.width = clamp(right.negative_pct, 0, 100) + "%";
        $("#compareScoreText").textContent = left.brand_reputation_score.toFixed(1) + " vs " + right.brand_reputation_score.toFixed(1);
        $("#comparePositiveText").textContent = left.positive_pct.toFixed(1) + "% vs " + right.positive_pct.toFixed(1) + "%";
        $("#compareNegativeText").textContent = left.negative_pct.toFixed(1) + "% vs " + right.negative_pct.toFixed(1) + "%";
        $("#compareSummary").textContent = payload.summary || "Comparison loaded.";
        return;
      } catch (error) {
        if (requestSeq !== state.compareRequestSeq) return;
        if (handleAuthError(error)) return;
      }

      $("#compareScoreA").style.width = clamp(brandA.brand_reputation_score, 0, 100) + "%";
      $("#compareScoreB").style.width = clamp(brandB.brand_reputation_score, 0, 100) + "%";
      $("#comparePositiveA").style.width = clamp(brandA.positive_pct, 0, 100) + "%";
      $("#comparePositiveB").style.width = clamp(brandB.positive_pct, 0, 100) + "%";
      $("#compareNegativeA").style.width = clamp(brandA.negative_pct, 0, 100) + "%";
      $("#compareNegativeB").style.width = clamp(brandB.negative_pct, 0, 100) + "%";

      $("#compareScoreText").textContent = brandA.brand_reputation_score.toFixed(1) + " vs " + brandB.brand_reputation_score.toFixed(1);
      $("#comparePositiveText").textContent = brandA.positive_pct.toFixed(1) + "% vs " + brandB.positive_pct.toFixed(1) + "%";
      $("#compareNegativeText").textContent = brandA.negative_pct.toFixed(1) + "% vs " + brandB.negative_pct.toFixed(1) + "%";

      const leader = brandA.brand_reputation_score >= brandB.brand_reputation_score ? brandA : brandB;
      const lagger = leader.brand === brandA.brand ? brandB : brandA;
      $("#compareSummary").textContent = leader.brand + " leads on brand reputation score, while " + lagger.brand + " needs more work on negative sentiment control and trust recovery.";
    }

    function updateSignalPanel(score) {
      $("#trendReputationText").textContent = getTrendLabel(score.brand_reputation_score, true);
      $("#trendPositiveText").textContent = getTrendLabel(score.positive_pct, true);
      $("#trendNegativeText").textContent = getTrendLabel(score.negative_pct, false);

      setTrendIcon($("#trendReputationIcon"), score.brand_reputation_score >= 40 ? "up" : score.brand_reputation_score < 10 ? "down" : "flat");
      setTrendIcon($("#trendPositiveIcon"), score.positive_pct >= 50 ? "up" : "flat");
      setTrendIcon($("#trendNegativeIcon"), score.negative_pct >= 40 ? "down" : "flat");
      updatePanelClock();
      renderSignalRadar(score);
    }

    function updateConfidenceSignal(confidence, sentiment) {
      const numeric = Number.isFinite(confidence) ? clamp(confidence, 0, 100) : 0;
      const color = sentimentClass(sentiment) === "sentiment-positive"
        ? "var(--positive)"
        : sentimentClass(sentiment) === "sentiment-negative"
          ? "var(--negative)"
          : "var(--neutral)";

      renderGauge($("#signalConfidenceGauge"), numeric, {
        displayValue: numeric ? numeric.toFixed(0) : "0",
        label: "Latest Signal",
        suffix: "%",
        caption: numeric ? "Confidence from the most recent prediction event." : "Confidence updates after prediction events.",
        color
      });

      $("#signalConfidenceNote").textContent = numeric
        ? sentiment + " classification detected with " + numeric.toFixed(1) + "% confidence."
        : "No recent prediction event.";
    }

    function pathFromPoints(points) {
      if (!points.length) return "";
      return points.map((point, index) => (index ? "L" : "M") + point.x + " " + point.y).join(" ");
    }

    function trendsEndpoint(selectedBrand = "") {
      const params = new URLSearchParams();
      if (selectedBrand) params.set("brand", selectedBrand);
      if (state.trendWindow && String(state.trendWindow).trim()) params.set("months", String(state.trendWindow).trim());
      const query = params.toString();
      return "/dashboard/trends" + (query ? "?" + query : "");
    }

    function getWindowedTrends() {
      if (!Array.isArray(state.trends) || !state.trends.length) return [];
      const windowSize = Number(state.trendWindow || "all");
      if (!Number.isFinite(windowSize) || windowSize <= 0) return state.trends;
      return state.trends.slice(-windowSize);
    }

    function activeTrendBrand() {
      const select = $("#trendBrandSelect");
      return (select && typeof select.value === "string" ? select.value : state.trendBrand) || "";
    }

    function activeTrendBrandLabel() {
      const select = $("#trendBrandSelect");
      if (select && select.selectedOptions && select.selectedOptions[0]) {
        return String(select.selectedOptions[0].textContent || "").trim();
      }
      return state.trendBrand || "All brands";
    }

    async function refreshTrendView(brandOverride) {
      const requestSeq = ++state.trendRequestSeq;
      const selectedBrand = typeof brandOverride === "string" ? brandOverride : activeTrendBrand();
      state.trendBrand = selectedBrand;
      $("#trendCaption").textContent = "Loading trend data...";
      try {
        const payload = await callApi(trendsEndpoint(selectedBrand), { timeoutMs: 12000 });
        if (requestSeq !== state.trendRequestSeq) return;
        state.trends = Array.isArray(payload.trends) ? payload.trends : [];
        renderTrendChart(getWindowedTrends());
        renderTrendMomentum();
        renderTrendMonthlyComparison();
        renderTrendReviewVolume();
        if (state.trendDrilldownSentiment) loadTrendDrilldown(state.trendDrilldownSentiment);
        if (selectedBrand && !state.trends.length) {
          $("#trendCaption").textContent = "No monthly trend data for " + activeTrendBrandLabel() + ". Missing valid review dates for this brand.";
        }
      } catch (error) {
        if (requestSeq !== state.trendRequestSeq) return;
        state.trends = [];
        renderTrendChart([]);
        renderTrendMomentum();
        renderTrendMonthlyComparison();
        renderTrendReviewVolume();
        if (!state.trendDrilldownSentiment) {
          $("#trendReviewDrilldown").innerHTML = '<div class="mini-note">Review samples will appear here after you click a sentiment line or legend item.</div>';
        }
        $("#trendCaption").textContent = "Unable to load trend graph: " + (error.message || "request failed") + ".";
      }
    }

    function renderTrendChart(trends) {
      const grid = $("#trendGrid");
      const labels = $("#trendLabels");
      grid.innerHTML = "";
      labels.innerHTML = "";

      if (!Array.isArray(trends) || !trends.length) {
        $("#trendPositivePath").setAttribute("d", "");
        $("#trendNeutralPath").setAttribute("d", "");
        $("#trendNegativePath").setAttribute("d", "");
        $("#trendCaption").textContent = "Trend graph waiting for `/dashboard/trends` data.";
        return;
      }

      const width = 320;
      const height = 180;
      const padding = { top: 16, right: 14, bottom: 34, left: 10 };
      const maxValue = Math.max(1, ...trends.flatMap((item) => [Number(item.Positive || 0), Number(item.Neutral || 0), Number(item.Negative || 0)]));
      const usableWidth = width - padding.left - padding.right;
      const usableHeight = height - padding.top - padding.bottom;
      const step = trends.length > 1 ? usableWidth / (trends.length - 1) : usableWidth / 2;

      [0, 0.25, 0.5, 0.75, 1].forEach((ratio) => {
        const y = padding.top + usableHeight * ratio;
        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("x1", padding.left);
        line.setAttribute("x2", width - padding.right);
        line.setAttribute("y1", y);
        line.setAttribute("y2", y);
        line.setAttribute("stroke", "rgba(142,165,195,0.14)");
        line.setAttribute("stroke-width", "1");
        grid.appendChild(line);
      });

      const pointSet = { Positive: [], Neutral: [], Negative: [] };
      const labelStep = trends.length > 10 ? 2 : 1;
      trends.forEach((item, index) => {
        const x = padding.left + step * index;
        ["Positive", "Neutral", "Negative"].forEach((key) => {
          const value = Number(item[key] || 0);
          const y = padding.top + usableHeight - (value / maxValue) * usableHeight;
          pointSet[key].push({ x, y });
        });

        if (index % labelStep !== 0 && index !== trends.length - 1) return;
        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", x);
        label.setAttribute("y", height - 8);
        label.setAttribute("fill", "var(--muted)");
        label.setAttribute("font-size", "10");
        label.setAttribute("text-anchor", index === 0 ? "start" : index === trends.length - 1 ? "end" : "middle");
        label.textContent = String(item.period || "").slice(2);
        labels.appendChild(label);
      });

      $("#trendPositivePath").setAttribute("d", pathFromPoints(pointSet.Positive));
      $("#trendNeutralPath").setAttribute("d", pathFromPoints(pointSet.Neutral));
      $("#trendNegativePath").setAttribute("d", pathFromPoints(pointSet.Negative));
      const scope = state.trendBrand ? " for " + activeTrendBrandLabel() : " for all brands";
      $("#trendCaption").textContent = "Trend graph rendered from " + trends.length + " months" + scope + ".";
    }

    function renderKeywords(keywords) {
      const host = $("#keywordList");
      if (!Array.isArray(keywords) || !keywords.length) {
        host.innerHTML = '<div class="keyword-caption">Keyword chart waiting for `/dashboard/keywords` data.</div>';
        return;
      }

      const maxCount = Math.max(1, ...keywords.map((item) => Number(item.count || 0)));
      host.innerHTML = keywords.slice(0, 8).map((item) => {
        const width = clamp((Number(item.count || 0) / maxCount) * 100, 0, 100);
        return [
          '<div class="keyword-row">',
          "<strong>" + item.word + "</strong>",
          '<div class="keyword-bar"><span style="width:' + width.toFixed(2) + '%;"></span></div>',
          "<span>" + Number(item.count || 0).toLocaleString() + "</span>",
          "</div>"
        ].join("");
      }).join("");
    }

    async function refreshDashboardAnalytics() {
      try {
        const role = normalizeAccessRole(state.userRole);
        const requests = [
          callApi("/dashboard/keywords"),
          callApi("/dashboard/brands")
        ];
        if (role === "admin") {
          requests.push(callApi("/admin/model-performance"));
        } else if (role === "marketing_staff" || role === "analyst") {
          requests.push(callApi("/dashboard/platforms"));
        }
        const [keywordsPayload, brandsPayload, optionalPayload] = await Promise.all(requests);
        state.keywords = Array.isArray(keywordsPayload.keywords) ? keywordsPayload.keywords : [];
        state.brands = Array.isArray(brandsPayload.brands) ? brandsPayload.brands.map(normalizeBrandRow) : [];
        if (role === "admin") {
          state.modelMetrics = optionalPayload && optionalPayload.metrics ? optionalPayload.metrics : null;
          state.modelTrainingAt = optionalPayload && optionalPayload.last_training_at ? optionalPayload.last_training_at : "";
          state.platforms = [];
          renderAdminModelPerformance();
          renderAdminControlHub();
          renderAdminOps();
          renderAdminSidePanel();
        } else {
          state.platforms = optionalPayload && Array.isArray(optionalPayload.platforms) ? optionalPayload.platforms : [];
        }

        // Render brand-driven UI immediately so it is not blocked by trend latency/errors.
        renderKeywords(state.keywords);
        renderBrandSelectors(state.brands);
        renderBrandQuickList(state.brands);
        renderBrandSideLists(state.brands);
        renderBrandWatchlist();
        renderBrandInsights();
        renderBrandComparison();
        renderAnalystCustomerVoice();
        renderAnalystFocusPanel();
        refreshCustomerVoiceKeywords();
        renderSmartInsight();
        renderAnalyticsSummaryContext();

        try {
          await refreshTrendView();
        } catch (trendError) {
          if (handleAuthError(trendError)) return;
          $("#trendCaption").textContent = "Unable to load trend graph: " + (trendError.message || "request failed") + ".";
        }
      } catch (error) {
        if (handleAuthError(error)) return;
        state.platforms = [];
        state.modelMetrics = null;
        state.modelTrainingAt = "";
        state.customerVoiceKeywords = [];
        state.customerVoiceKeywordCache = {};
        state.customerVoiceKeywordsLoading = false;
        $("#trendCaption").textContent = "Unable to load trend graph: " + (error.message || "request failed") + ".";
        $("#keywordList").innerHTML = '<div class="keyword-caption">Unable to load keyword chart.</div>';
        $("#compareSummary").textContent = "Unable to load brand comparison data.";
        $("#similarBrandList").innerHTML = '<div class="mini-note">Unable to load similar brand data.</div>';
        renderAnalystCustomerVoice();
        renderAnalystFocusPanel();
        renderSmartInsight();
        renderAnalyticsSummaryContext();
      }
    }

    function ratingExpectation(rating) {
      if (!Number.isFinite(rating)) return null;
      if (rating >= 4) return "Positive";
      if (rating <= 2) return "Negative";
      return "Neutral";
    }

    function sentimentClass(sentiment) {
      if ((sentiment || "").toLowerCase() === "positive") return "sentiment-positive";
      if ((sentiment || "").toLowerCase() === "negative") return "sentiment-negative";
      return "sentiment-neutral";
    }

    function extractSentiment(payload) {
      return payload.predicted_sentiment || payload.final_sentiment || payload.sentiment || "Neutral";
    }

    function extractConfidence(payload, sentiment) {
      const candidates = [payload.confidence, payload.prediction_confidence, payload.final_confidence];
      for (const item of candidates) {
        if (Number.isFinite(Number(item))) {
          const value = Number(item);
          return value <= 1 ? value * 100 : value;
        }
      }

      const probabilityMaps = [payload.final_class_probabilities, payload.class_probabilities, payload.probabilities];
      for (const map of probabilityMaps) {
        if (map && Number.isFinite(Number(map[sentiment]))) {
          const value = Number(map[sentiment]);
          return value <= 1 ? value * 100 : value;
        }
      }

      return null;
    }

    function updateSingleResult(payload, submittedRating) {
      const sentiment = extractSentiment(payload);
      const confidence = extractConfidence(payload, sentiment);
      state.latestConfidence = confidence;
      state.latestSentiment = sentiment;
      $("#singleResultShell").classList.remove("is-empty");
      $("#singleResultIntro").textContent = "Prediction complete. Inspect sentiment, confidence, and any rating mismatch below.";

      const badge = $("#singleSentimentBadge");
      badge.className = "sentiment-badge " + sentimentClass(sentiment);
      badge.textContent = sentiment;

      const meterWidth = Number.isFinite(confidence) ? clamp(confidence, 0, 100) : 0;
      $("#singleConfidenceBar").style.width = meterWidth + "%";
      $("#singleConfidenceText").textContent = Number.isFinite(confidence) ? meterWidth.toFixed(1) + "%" : "Unavailable";

      const expected = ratingExpectation(submittedRating);
      const mismatch = Boolean(payload.is_mismatch_with_rating) || (expected && expected !== sentiment);
      const warning = $("#ratingWarning");
      if (mismatch && expected) {
        warning.classList.add("is-visible");
        warning.textContent = "Rating suggests " + expected + " sentiment, but the classifier returned " + sentiment + ". Review the mismatch before actioning this signal.";
      } else {
        warning.classList.remove("is-visible");
        warning.textContent = "";
      }

      $("#singleTechnicalJson").textContent = JSON.stringify(payload, null, 2);
      updateConfidenceSignal(confidence, sentiment);
    }

    function sentimentTagClass(value) {
      const normalized = (value || "").toLowerCase();
      if (normalized === "positive") return "positive";
      if (normalized === "negative") return "negative";
      if (normalized === "neutral") return "neutral";
      return "unknown";
    }

    function buildBatchPreview(payload, submittedLines) {
      const candidates = [payload.results, payload.predictions, payload.preview, payload.items];
      for (const list of candidates) {
        if (Array.isArray(list) && list.length) {
          return list.slice(0, 10).map((item, index) => {
            const sentiment = item.predicted_sentiment || item.final_sentiment || item.sentiment || "Processed";
            const confidence = extractConfidence(item, sentiment);
            return {
              review_id: item.review_id || item.id || index + 1,
              sentiment,
              confidence
            };
          });
        }
      }

      return submittedLines.slice(0, 10).map((line, index) => ({
        review_id: index + 1,
        sentiment: "Processed",
        confidence: null
      }));
    }

    function renderBatchTable(rows) {
      const tbody = $("#batchTableBody");
      if (!rows.length) {
        tbody.innerHTML = '<tr><td colspan="3" class="signal-note">No batch results available yet.</td></tr>';
        return;
      }

      tbody.innerHTML = rows.map((row) => {
        const confidenceText = Number.isFinite(row.confidence) ? row.confidence.toFixed(1) + "%" : "Unavailable";
        return [
          "<tr>",
          "<td>" + row.review_id + "</td>",
          '<td><span class="tag ' + sentimentTagClass(row.sentiment) + '">' + row.sentiment + "</span></td>",
          "<td>" + confidenceText + "</td>",
          "</tr>"
        ].join("");
      }).join("");
    }

    function getHistory() {
      const data = storageRead(HISTORY_KEY, []);
      return Array.isArray(data) ? data : [];
    }

    function storeHistory(entry) {
      const next = [entry, ...getHistory()].slice(0, 10);
      storageWrite(HISTORY_KEY, next);
      renderHistory();
    }

    function renderHistory() {
      const entries = getHistory();
      const shell = $("#historyTimeline");
      if (!entries.length) {
        shell.innerHTML = '<div class="empty-state">No local activity has been recorded yet.</div>';
        return;
      }

      shell.innerHTML = entries.map((entry) => {
        return [
          '<article class="timeline-item">',
          "<strong>" + entry.title + "</strong>",
          "<time>" + entry.time + "</time>",
          "<p>" + entry.summary + "</p>",
          "</article>"
        ].join("");
      }).join("");
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

    function viewRouter(nextView) {
      const hashView = (location.hash || "").replace("#", "");
      const view = nextView || hashView || defaultViewForRole(state.userRole);
      const validViews = allowedViewsForRole(state.userRole);
      const fallbackView = validViews[0] || "dashboard";
      const resolved = validViews.includes(view) ? view : fallbackView;
      const activeGroup = groupForView(state.userRole, resolved);
      if (activeGroup) {
        state.openNavGroup[normalizeAccessRole(state.userRole)] = activeGroup.id;
      }
      $$(".view").forEach((section) => {
        section.classList.toggle("is-active", section.id === "view-" + resolved);
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
      document.body.classList.remove("drawer-open");
      $("#signalDrawerToggle").setAttribute("aria-expanded", "false");
      resetViewScroll();
    }

    function applyTheme(theme) {
      const resolved = theme === "light" ? "light" : "dark";
      document.body.setAttribute("data-theme", resolved);
      $("#themeToggle").setAttribute("aria-pressed", String(resolved === "light"));
      $("#themeLabel").textContent = resolved === "light" ? "Dark Mode" : "Light Mode";
      $("#themeIcon").innerHTML = resolved === "light"
        ? '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"></path>'
        : '<circle cx="12" cy="12" r="4"></circle><path d="M12 2v2.5"></path><path d="M12 19.5V22"></path><path d="M4.9 4.9l1.8 1.8"></path><path d="M17.3 17.3l1.8 1.8"></path><path d="M2 12h2.5"></path><path d="M19.5 12H22"></path><path d="M4.9 19.1l1.8-1.8"></path><path d="M17.3 6.7l1.8-1.8"></path>';
      storageWrite(THEME_KEY, resolved);
    }

    async function refreshBrandScore() {
      const button = $("#refreshScoreButton");
      setButtonLoading(button, true, "Refresh Brand Score");
      try {
        const payload = await callApi("/dashboard/summary");
        const score = normalizeBrandScore(payload);
        state.brandScore = score;
        updateDashboard(score);
        updateSignalPanel(score);
        refreshDashboardAnalytics();
        toast("Brand score refreshed successfully.", "success");
      } catch (error) {
        if (handleAuthError(error)) return;
        toast(error.message || "Failed to refresh brand score.", "error");
      } finally {
        setButtonLoading(button, false, "Refresh Brand Score");
      }
    }

    async function handleSingleSubmit(event) {
      event.preventDefault();
      const shell = $("#singleFormShell");
      const reviewText = $("#singleReviewText").value.trim();
      if (!reviewText) {
        shake(shell);
        toast("Single review text is required.", "error");
        return;
      }

      const ratingValue = $("#singleRating").value.trim();
      const rating = ratingValue ? Number(ratingValue) : null;
      const button = $("#singlePredictButton");
      setButtonLoading(button, true, "Predict Sentiment");

      const payload = {
        review_text: reviewText,
        platform: $("#singlePlatform").value.trim() || "Manual Input",
        brand: $("#singleBrand").value.trim() || $("#singlePlatform").value.trim() || "Manual Input"
      };

      if (Number.isFinite(rating)) payload.rating = rating;

      try {
        const data = await callApi("/predict", { method: "POST", body: payload });
        updateSingleResult(data, rating);
        storeHistory({
          title: "Single review prediction",
          time: new Date().toLocaleString(),
          summary: "Sentiment: " + extractSentiment(data) + (Number.isFinite(state.latestConfidence) ? " with " + state.latestConfidence.toFixed(1) + "% confidence." : ".")
        });
        toast("Single review prediction completed.", "success");
      } catch (error) {
        if (handleAuthError(error)) return;
        $("#singleTechnicalJson").textContent = JSON.stringify({ error: error.message || "Request failed" }, null, 2);
        $("#singleResultShell").classList.remove("is-empty");
        $("#singleResultIntro").textContent = "Prediction failed. Review the error payload and try again.";
        $("#singleSentimentBadge").className = "sentiment-badge sentiment-negative";
        $("#singleSentimentBadge").textContent = "Error";
        $("#singleConfidenceBar").style.width = "0%";
        $("#singleConfidenceText").textContent = "Unavailable";
        $("#ratingWarning").classList.remove("is-visible");
        toast(error.message || "Prediction failed.", "error");
      } finally {
        setButtonLoading(button, false, "Predict Sentiment");
      }
    }

    async function handleBatchSubmit(event) {
      event.preventDefault();
      const shell = $("#batchFormShell");
      const lines = $("#batchReviewText").value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
      if (!lines.length) {
        shake(shell);
        toast("Batch input requires at least one review line.", "error");
        return;
      }

      const button = $("#batchRunButton");
      setButtonLoading(button, true, "Run Batch");

      const payload = {
        reviews: lines.map((review_text, index) => ({ review_id: index + 1, review_text })),
        save_to_dataset: $("#saveToDataset").checked
      };

      try {
        const data = await callApi("/predict/batch", { method: "POST", body: payload });
        $("#batchTechnicalJson").textContent = JSON.stringify(data, null, 2);
        const score = normalizeBrandScore(data);
        if (score.total_reviews || score.brand_reputation_score || data.brand_score) {
          state.brandScore = score;
          updateDashboard(score);
          updateSignalPanel(score);
          refreshDashboardAnalytics();
          renderGauge($("#batchGauge"), score.brand_reputation_score, {
            displayValue: score.brand_reputation_score.toFixed(1),
            label: "Batch Score",
            suffix: "/100",
            caption: "Updated from the batch response.",
            color: score.brand_reputation_score >= 40 ? "var(--positive)" : score.brand_reputation_score < 10 ? "var(--negative)" : "var(--neutral)"
          });
        }

        $("#batchProcessedCount").textContent = Number(data.rows || score.total_reviews || lines.length).toLocaleString();
        renderBatchTable(buildBatchPreview(data, lines));
        storeHistory({
          title: "Batch run",
          time: new Date().toLocaleString(),
          summary: "Processed " + Number(data.rows || lines.length).toLocaleString() + " reviews. Updated score: " + (score.brand_reputation_score || 0).toFixed(1) + "."
        });
        toast("Batch prediction completed.", "success");
      } catch (error) {
        if (handleAuthError(error)) return;
        $("#batchTechnicalJson").textContent = JSON.stringify({ error: error.message || "Request failed" }, null, 2);
        renderBatchTable([]);
        toast(error.message || "Batch prediction failed.", "error");
      } finally {
        setButtonLoading(button, false, "Run Batch");
      }
    }

    function clearHistory() {
      storageWrite(HISTORY_KEY, []);
      renderHistory();
      toast("Local history cleared.", "info");
    }

    function userRoleTagClass(role) {
      const normalized = normalizeAccessRole(role);
      if (normalized === "admin") return "admin";
      if (normalized === "marketing_staff") return "marketing";
      return "analyst";
    }

    function userRoleActions(row) {
      if (row.is_protected) return '<span class="users-note">Protected admin account</span>';
      if (row.is_self) return '<span class="users-note">Your account</span>';

      const analystActive = row.role === "analyst";
      const marketingActive = row.role === "marketing_staff";
      return [
        '<div class="users-actions">',
        '<button class="ghost-btn user-action-btn ' + (analystActive ? "is-active" : "") + '" type="button" data-action="set-role" data-email="' + row.email + '" data-role="analyst" ' + (analystActive ? "disabled" : "") + '>Analyst</button>',
        '<button class="ghost-btn user-action-btn ' + (marketingActive ? "is-active" : "") + '" type="button" data-action="set-role" data-email="' + row.email + '" data-role="marketing_staff" ' + (marketingActive ? "disabled" : "") + '>Marketing Staff</button>',
        '<button class="ghost-btn user-action-btn user-delete-btn" type="button" data-action="delete-user" data-email="' + row.email + '">Delete</button>',
        '</div>'
      ].join("");
    }

    function renderUsersTable(users) {
      const tbody = $("#usersTableBody");
      if (!Array.isArray(users) || !users.length) {
        tbody.innerHTML = '<tr><td colspan="4" class="users-note">No users available.</td></tr>';
        return;
      }
      tbody.innerHTML = users.map((row) => {
        const roleLabel = humanizeRole(row.role);
        return [
          "<tr>",
          "<td>" + (row.name || "Unknown") + "</td>",
          "<td>" + (row.email || "") + "</td>",
          '<td><span class="tag ' + userRoleTagClass(row.role) + '">' + roleLabel + "</span></td>",
          "<td>" + userRoleActions(row) + "</td>",
          "</tr>"
        ].join("");
      }).join("");
    }

    async function loadUsersManagement() {
      const button = $("#refreshUsersButton");
      if (button) setButtonLoading(button, true, "Refresh Users");
      try {
        const payload = await callApi("/admin/users");
        const users = Array.isArray(payload.users) ? payload.users : [];
        state.users = users;
        renderUsersTable(users);
        renderRoleDashboardPanel();
      } catch (error) {
        if (handleAuthError(error)) return;
        renderUsersTable([]);
        toast(error.message || "Failed to load users.", "error");
      } finally {
        if (button) setButtonLoading(button, false, "Refresh Users");
      }
    }

    async function handleUsersTableAction(event) {
      const button = event.target.closest("button[data-action]");
      if (!button) return;
      const action = button.dataset.action || "";
      const email = button.dataset.email || "";
      const role = button.dataset.role || "";
      if (!email) return;

      if (action === "delete-user") {
        const confirmed = window.confirm("Delete user " + email + "? This action cannot be undone.");
        if (!confirmed) return;
      }

      const workingText = action === "delete-user" ? "Deleting..." : "Updating...";
      setButtonLoading(button, true, button.textContent.trim(), workingText);
      try {
        if (action === "delete-user") {
          await callApi("/admin/users/delete", {
            method: "POST",
            body: { email }
          });
          toast("User deleted.", "success");
        } else if (action === "set-role") {
          if (!role) return;
          await callApi("/admin/users/role", {
            method: "POST",
            body: { email, role }
          });
          toast("User role updated.", "success");
        } else {
          return;
        }
        await loadUsersManagement();
      } catch (error) {
        if (handleAuthError(error)) return;
        toast(error.message || "User update failed.", "error");
      } finally {
        setButtonLoading(button, false, button.dataset.label || button.textContent.trim());
      }
    }

    function bindEvents() {
      $$(".nav-item").forEach((button) => {
        button.addEventListener("click", () => viewRouter(button.dataset.view));
      });
      $("#navRail").addEventListener("click", (event) => {
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
      $("#themeToggle").addEventListener("click", () => {
        const nextTheme = document.body.getAttribute("data-theme") === "dark" ? "light" : "dark";
        applyTheme(nextTheme);
      });
      $("#signalDrawerToggle").addEventListener("click", () => {
        const next = !document.body.classList.contains("drawer-open");
        document.body.classList.toggle("drawer-open", next);
        $("#signalDrawerToggle").setAttribute("aria-expanded", String(next));
      });
      $("#refreshScoreButton").addEventListener("click", refreshBrandScore);
      $("#dashboardSyncButton").addEventListener("click", refreshBrandScore);
      $("#brandInsightSelect").addEventListener("change", () => {
        renderBrandInsights();
      });
      $("#compareBrandA").addEventListener("change", renderBrandComparison);
      $("#compareBrandB").addEventListener("change", renderBrandComparison);
      $("#singleForm").addEventListener("submit", handleSingleSubmit);
      $("#batchForm").addEventListener("submit", handleBatchSubmit);
      $("#clearHistoryButton").addEventListener("click", clearHistory);
      $("#confirmOkButton").addEventListener("click", () => closeConfirmDialog(true));
      $("#confirmCancelButton").addEventListener("click", () => closeConfirmDialog(false));
      $("#confirmOverlay").addEventListener("click", (event) => {
        if (event.target.id === "confirmOverlay") closeConfirmDialog(false);
      });
      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeConfirmDialog(false);
      });
      $("#refreshUsersButton").addEventListener("click", loadUsersManagement);
      if ($("#refreshModelButton")) $("#refreshModelButton").addEventListener("click", loadAdminModelPerformance);
      if ($("#adminOpenAlertsButton")) $("#adminOpenAlertsButton").addEventListener("click", () => viewRouter("notifications"));
      if ($("#adminOpenUsersButton")) $("#adminOpenUsersButton").addEventListener("click", () => viewRouter("users"));
      if ($("#adminOpenModelButton")) $("#adminOpenModelButton").addEventListener("click", () => viewRouter("model-performance"));
      if ($("#runPreprocessButton")) $("#runPreprocessButton").addEventListener("click", () => runAdminPipelineAction("/preprocess", $("#runPreprocessButton"), "Preprocess", "Running preprocess...", "Preprocessing completed."));
      if ($("#runFeaturesButton")) $("#runFeaturesButton").addEventListener("click", () => runAdminPipelineAction("/features", $("#runFeaturesButton"), "Features", "Running feature extraction...", "Feature extraction completed."));
      if ($("#runTrainButton")) $("#runTrainButton").addEventListener("click", () => runAdminPipelineAction("/train", $("#runTrainButton"), "Train Model", "Training model...", "Model training completed."));
      $("#usersTableBody").addEventListener("click", handleUsersTableAction);
      if ($("#roleDashboardCards")) $("#roleDashboardCards").addEventListener("click", (event) => {
        const card = event.target.closest(".role-mini-card[data-view]");
        if (!card) return;
        viewRouter(card.dataset.view || "");
      });
      if ($("#roleDashboardCards")) $("#roleDashboardCards").addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        const card = event.target.closest(".role-mini-card[data-view]");
        if (!card) return;
        event.preventDefault();
        viewRouter(card.dataset.view || "");
      });
      $$(".analyst-focus-btn[data-analyst-view]").forEach((button) => {
        button.addEventListener("click", () => viewRouter(button.dataset.analystView || ""));
      });
      $("#brandQuickList").addEventListener("click", handleBrandQuickPick);
      if ($("#brandInsightQuickList")) $("#brandInsightQuickList").addEventListener("click", handleInsightQuickPick);
      if ($("#brandCompareQuickList")) $("#brandCompareQuickList").addEventListener("click", handleCompareQuickPick);
      if ($("#brandWatchlistPills")) $("#brandWatchlistPills").addEventListener("click", handleWatchlistPick);
      if ($("#addWatchlistButton")) $("#addWatchlistButton").addEventListener("click", addSelectedBrandToWatchlist);
      if ($("#clearWatchlistButton")) $("#clearWatchlistButton").addEventListener("click", clearBrandWatchlist);
      if ($("#customerVoiceWindowSelect")) $("#customerVoiceWindowSelect").addEventListener("change", async (event) => {
        state.customerVoiceWindow = event.target.value || "all";
        renderAnalystCustomerVoice();
        await refreshCustomerVoiceKeywords();
      });
      if ($("#customerVoiceBrandSelect")) $("#customerVoiceBrandSelect").addEventListener("change", async (event) => {
        state.customerVoiceBrand = event.target.value || "";
        renderAnalystCustomerVoice();
        await refreshCustomerVoiceKeywords();
      });
      $("#trendWindowSelect").addEventListener("change", async (event) => {
        state.trendWindow = event.target.value || "all";
        try {
          await refreshTrendView(state.trendBrand || "");
          renderAnalyticsSummaryContext();
        } catch (error) {
          if (handleAuthError(error)) return;
          $("#trendCaption").textContent = "Unable to load trend graph: " + (error.message || "request failed") + ".";
        }
      });
      $("#trendBrandSelect").addEventListener("change", async (event) => {
        state.trendBrand = event.target.value || "";
        try {
          await refreshTrendView(state.trendBrand);
          renderAnalyticsSummaryContext();
        } catch (error) {
          if (handleAuthError(error)) return;
          $("#trendCaption").textContent = "Unable to load trend graph: " + (error.message || "request failed") + ".";
        }
      });
      if ($("#downloadTrendCsvButton")) $("#downloadTrendCsvButton").addEventListener("click", exportTrendCsv);
      if ($("#downloadTrendReportButton")) $("#downloadTrendReportButton").addEventListener("click", exportTrendReport);
      if ($("#downloadTrendPdfButton")) $("#downloadTrendPdfButton").addEventListener("click", exportTrendPdf);
      if ($("#downloadCustomerVoiceCsvButton")) $("#downloadCustomerVoiceCsvButton").addEventListener("click", exportCustomerVoiceCsv);
      if ($("#downloadCustomerVoiceReportButton")) $("#downloadCustomerVoiceReportButton").addEventListener("click", exportCustomerVoiceReport);
      if ($("#downloadCustomerVoicePdfButton")) $("#downloadCustomerVoicePdfButton").addEventListener("click", exportCustomerVoicePdf);
      $$("#view-review-trends .trend-legend span[data-sentiment]").forEach((item) => {
        item.addEventListener("click", () => loadTrendDrilldown(item.dataset.sentiment || ""));
      });
      ["#trendPositivePath", "#trendNeutralPath", "#trendNegativePath"].forEach((selector) => {
        const node = $(selector);
        if (!node) return;
        node.addEventListener("click", () => loadTrendDrilldown(node.dataset.sentiment || ""));
      });
      $("#loginTab").addEventListener("click", () => setAuthMode("login"));
      $("#registerTab").addEventListener("click", () => setAuthMode("register"));

      $("#switchToLogin").addEventListener("click", () => setAuthMode("login"));
      $("#toggleLoginPassword").addEventListener("click", () => {
        const input = $("#loginPassword");
        const toggle = $("#toggleLoginPassword");
        const reveal = input.type === "password";
        input.type = reveal ? "text" : "password";
        toggle.textContent = reveal ? "Hide" : "Show";
        toggle.setAttribute("aria-label", reveal ? "Hide password" : "Show password");
        toggle.setAttribute("aria-pressed", String(reveal));
      });
      $("#loginEmail").addEventListener("input", updateLoginButtonState);
      $("#loginPassword").addEventListener("input", updateLoginButtonState);
      $("#loginForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        const email = $("#loginEmail").value.trim();
        const password = $("#loginPassword").value;
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
          refreshBrandScore();
        } catch (error) {
          $("#authError").textContent = error.message || "Login failed.";
        } finally {
          setButtonLoading(button, false, "Login");
          updateLoginButtonState();
        }
      });
      $("#registerForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        const name = $("#registerName").value.trim();
        const email = $("#registerEmail").value.trim();
        const password = $("#registerPassword").value;
        const role = $("#registerRole").value || "analyst";
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
      $("#logoutButton").addEventListener("click", async () => {
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
      const savedTheme = storageRead(THEME_KEY, "dark");
      applyTheme(savedTheme);
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
        label: "Batch Score",
        suffix: "/100",
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
      try {
        const sessionState = await callApi("/auth/session");
        if (sessionState && sessionState.authenticated) {
          setSession(normalizeSessionUser(sessionState));
          refreshBrandScore();
        } else {
          clearSessionUi();
          showLogin();
        }
      } catch (error) {
        clearSessionUi();
        showLogin("Unable to verify the backend session. Make sure the Flask app is running, then sign in.");
      }
    }

    bootUi();
