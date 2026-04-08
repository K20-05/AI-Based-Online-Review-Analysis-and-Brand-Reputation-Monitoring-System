(function () {
  const HISTORY_KEY = "brandpulse-control-room-history";
  const WATCHLIST_KEY = "brandpulse-control-room-watchlist";

  const ROLE_ACCESS = {
    admin: [
      "dashboard",
      "users",
      "model-performance",
      "notifications",
      "history",
      "single",
      "brand-insights",
      "sentiment-distribution",
      "review-trends",
      "customer-intelligence",
      "analytics-summary",
      "about"
    ],
    analyst: ["dashboard", "single", "review-trends", "sentiment-distribution", "customer-intelligence", "analytics-summary", "about"],
    marketing_staff: ["dashboard", "brand-insights", "sentiment-distribution", "analytics-summary", "about"]
  };

  const ROLE_NAV_GROUPS = {
    admin: [
      { type: "link", view: "dashboard" },
      { type: "group", id: "control", label: "Admin Control", views: ["users", "model-performance", "notifications", "history"] },
      { type: "group", id: "analysis", label: "Workspace", views: ["single", "brand-insights", "sentiment-distribution", "review-trends", "customer-intelligence", "analytics-summary"] },
      { type: "link", view: "about" }
    ],
    analyst: [
      { type: "link", view: "dashboard" },
      { type: "group", id: "prediction", label: "Prediction", views: ["single"] },
      { type: "group", id: "analytics", label: "Analytics", views: ["review-trends", "sentiment-distribution", "customer-intelligence", "analytics-summary"] },
      { type: "link", view: "about" }
    ],
    marketing_staff: [
      { type: "link", view: "dashboard" },
      { type: "group", id: "brand", label: "Brand Monitor", views: ["brand-insights"] },
      { type: "group", id: "analytics", label: "Market Signals", views: ["sentiment-distribution", "analytics-summary"] },
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
      single: "Review Analysis",
      "brand-insights": "Brand Intelligence",
      "sentiment-distribution": "Sentiment Insights",
      "review-trends": "Review Trends",
      "customer-intelligence": "Customer Voice",
      "analytics-summary": "Summary",
      about: "About"
    },
    analyst: {
      dashboard: "Dashboard",
      single: "Review Analysis",
      "review-trends": "Review Trends",
      "sentiment-distribution": "Sentiment Insights",
      "customer-intelligence": "Customer Voice",
      "analytics-summary": "Summary",
      about: "About"
    },
    marketing_staff: {
      dashboard: "Dashboard",
      "brand-insights": "Brand Intelligence",
      "sentiment-distribution": "Sentiment Insights",
      "analytics-summary": "Business Summary",
      about: "About"
    }
  };

  const WORKSPACE_SIGNAL_VIEWS = new Set([
    "single",
    "brand-insights",
    "sentiment-distribution",
    "review-trends",
    "customer-intelligence",
    "analytics-summary"
  ]);

  const RANDOM_REVIEW_FALLBACKS = [
    {
      review_text: "Delivery was two days late, but the product quality was excellent and worth the wait.",
      brand: "Amazon",
      platform: "Amazon",
      rating: 4
    },
    {
      review_text: "Packaging was damaged and the item stopped working after one day. Very disappointing experience.",
      brand: "Flipkart",
      platform: "Flipkart",
      rating: 1
    },
    {
      review_text: "Nice fabric and color looked exactly like the photos. Size was slightly loose but still good overall.",
      brand: "Myntra",
      platform: "Myntra",
      rating: 4
    },
    {
      review_text: "The order arrived quickly, but customer support did not help with the missing accessory.",
      brand: "Meesho",
      platform: "Meesho",
      rating: 2
    },
    {
      review_text: "Good value for money and the app experience was smooth from browsing to checkout.",
      brand: "Ajio",
      platform: "Ajio",
      rating: 5
    },
    {
      review_text: "Return pickup was delayed and I had to follow up multiple times before the refund was processed.",
      brand: "Nykaa",
      platform: "Nykaa",
      rating: 2
    }
  ];

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => Array.from(document.querySelectorAll(selector));
  const on = (target, eventName, handler, options) => {
    const node = typeof target === "string" ? $(target) : target;
    if (!node) return null;
    node.addEventListener(eventName, handler, options);
    return node;
  };
  const onAll = (selector, eventName, handler, options) => {
    const nodes = $$(selector);
    nodes.forEach((node) => node.addEventListener(eventName, handler, options));
    return nodes;
  };

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

  function emptyBrandScore() {
    return {
      total_reviews: 0,
      positive_pct: 0,
      neutral_pct: 0,
      negative_pct: 0,
      brand_reputation_score: 0
    };
  }

  function emptyRealtimeSummary() {
    return {
      total_reviews: 0,
      platforms: [],
      brands: [],
      latest_ingested_at: null
    };
  }

  function normalizeStorageScope(identity) {
    const normalized = String(identity || "guest")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9@._-]+/g, "-")
      .replace(/^-+|-+$/g, "");
    return normalized || "guest";
  }

  function sessionStorageIdentityForUser(user) {
    if (user && typeof user === "object") {
      return user.email || user.name || user.role || "guest";
    }
    return user || "guest";
  }

  function normalizeReviewLookup(value) {
    return String(value || "")
      .trim()
      .toLowerCase()
      .replace(/[_\s]+/g, " ");
  }

  function normalizeReviewSample(sample) {
    if (!sample || typeof sample !== "object") return null;
    const reviewText = String(sample.review_text || sample.normalized_review || "").trim();
    if (!reviewText) return null;
    const rating = sample.rating === null || sample.rating === undefined || String(sample.rating).trim() === ""
      ? ""
      : String(sample.rating);
    return {
      review_text: reviewText,
      brand: String(sample.brand || "").trim(),
      platform: String(sample.platform || sample.brand || "").trim(),
      rating
    };
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

  function canonicalView(view) {
    const normalized = String(view || "").trim().toLowerCase();
    if (normalized === "batch") return "single";
    if (normalized === "brand-comparison") return "brand-insights";
    if (normalized === "keyword-frequency") return "sentiment-distribution";
    return normalized;
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

  window.BrandPulseShared = {
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
  };
}());
