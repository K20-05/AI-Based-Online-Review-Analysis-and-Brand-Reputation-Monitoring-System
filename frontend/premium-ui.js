(function () {
  const $ = (selector, scope) => (scope || document).querySelector(selector);
  const $$ = (selector, scope) => Array.from((scope || document).querySelectorAll(selector));

  const revealSelector = [
    ".view-head",
    ".dashboard-status-pill",
    ".surface",
    ".signal-widget",
    ".table-shell",
    ".timeline-item",
    ".metric-card",
    ".stats-cluster",
    ".admin-control-card",
    ".analyst-focus-card",
    ".role-mini-card"
  ].join(", ");

  const animatedNumberSelector = [
    ".ring-gauge__value",
    ".metric-value span",
    ".dashboard-quick-stat strong",
    ".admin-control-card strong",
    ".role-mini-card strong",
    ".signal-radar-score",
    ".analyst-focus-metric",
    "#insightScoreValue",
    ".processed-count",
    "#adminSideAlertCount",
    "#adminSideUserCount",
    "#adminSideBrandCount"
  ].join(", ");

  let revealObserver = null;
  let mutationObserver = null;
  let refreshScheduled = false;
  let ignoreMutationsUntil = 0;

  function setTextSafely(element, text) {
    if (!element || element.textContent === text) return;
    ignoreMutationsUntil = performance.now() + 50;
    element.textContent = text;
  }

  function parseAnimatedNumber(rawText) {
    const text = String(rawText || "").trim();
    if (!text) return null;

    const normalized = text.replace(/,/g, "");
    const match = normalized.match(/^([^-\d]*)(-?\d+(?:\.\d+)?)(.*)$/);
    if (!match) return null;

    const value = Number(match[2]);
    const suffix = match[3] || "";
    if (!Number.isFinite(value) || suffix.includes(":") || suffix.includes("/")) return null;

    return {
      raw: text,
      prefix: match[1] || "",
      value,
      suffix,
      decimals: (match[2].split(".")[1] || "").length,
      grouped: text.includes(",") || Math.abs(value) >= 1000
    };
  }

  function formatAnimatedNumber(value, spec) {
    const options = {
      minimumFractionDigits: spec.decimals,
      maximumFractionDigits: spec.decimals
    };

    const rendered = spec.grouped
      ? value.toLocaleString(undefined, options)
      : (spec.decimals ? value.toFixed(spec.decimals) : String(Math.round(value)));

    return spec.prefix + rendered + spec.suffix;
  }

  function animateNumberElement(element, spec) {
    if (!element || element.dataset.premiumTargetRaw === spec.raw) return;

    const previous = Number(element.dataset.premiumLastValue);
    const startValue = Number.isFinite(previous) ? previous : spec.value;
    const delta = Math.abs(spec.value - startValue);

    element.dataset.premiumTargetRaw = spec.raw;
    element.dataset.premiumLastValue = String(spec.value);

    if (!delta || delta < 0.01) {
      setTextSafely(element, spec.raw);
      return;
    }

    const duration = 720;
    const startTime = performance.now();

    function tick(now) {
      const progress = Math.min(1, (now - startTime) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      const nextValue = startValue + (spec.value - startValue) * eased;
      setTextSafely(element, progress >= 1 ? spec.raw : formatAnimatedNumber(nextValue, spec));
      if (progress < 1) requestAnimationFrame(tick);
    }

    requestAnimationFrame(tick);
  }

  function enhanceNumbers() {
    $$(animatedNumberSelector).forEach((element) => {
      const spec = parseAnimatedNumber(element.textContent);
      if (!spec) return;
      animateNumberElement(element, spec);
    });
  }

  function updateClockChip() {
    const target = $("#topbarClockValue");
    if (!target) return;
    setTextSafely(target, new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit"
    }));
  }

  function updateExecutiveChips() {
    const statusValue = $("#executiveStatusValue");
    const statusMeta = $("#executiveStatusMeta");
    const syncValue = $("#topbarSyncValue");
    const syncChip = $("#topbarSyncChip") || $("#executiveStatusChip");
    const sessionChip = $("#sessionChip");
    const sessionRole = $("#sessionRole");
    const panelStatus = $("#panelStatusText");
    const sourceBadge = $("#dashboardSourceBadge");
    const sourceText = $("#dashboardSource");

    if (statusValue) {
      const roleText = sessionChip && !sessionChip.classList.contains("hidden")
        ? (sessionRole && sessionRole.textContent.trim()) || "Operator"
        : "Guest Preview";
      const panelText = (panelStatus && panelStatus.textContent.trim()) || "Live operations";
      const combined = roleText === "No session" ? panelText : roleText + " | " + panelText;
      setTextSafely(statusValue, combined);
    }

    if (syncValue) {
      const syncText = (sourceBadge && sourceBadge.textContent.trim()) ||
        (sourceText && sourceText.textContent.trim()) ||
        "Awaiting refresh";
      const compactSync = syncText.length > 32 ? syncText.slice(0, 29) + "..." : syncText;
      setTextSafely(syncValue, syncText);
      if (syncChip) {
        syncChip.classList.toggle("topbar-chip--live", !/awaiting|waiting|standby|no endpoint/i.test(syncText));
      }
      if (statusMeta) {
        setTextSafely(statusMeta, compactSync);
      }
    } else if (statusMeta) {
      const syncText = (sourceBadge && sourceBadge.textContent.trim()) ||
        (sourceText && sourceText.textContent.trim()) ||
        "Awaiting refresh";
      const compactSync = syncText.length > 32 ? syncText.slice(0, 29) + "..." : syncText;
      setTextSafely(statusMeta, compactSync);
    }
  }

  function markEmptyStates() {
    $$(".mini-note, .empty-state, .result-shell.is-empty").forEach((element) => {
      element.classList.add("premium-empty");
    });
  }

  function ensureRevealObserver() {
    if (revealObserver || !("IntersectionObserver" in window)) return;

    revealObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        revealObserver.unobserve(entry.target);
      });
    }, {
      rootMargin: "0px 0px -10% 0px",
      threshold: 0.12
    });
  }

  function bindRevealTargets() {
    ensureRevealObserver();
    $$(revealSelector).forEach((element) => {
      if (element.dataset.premiumRevealBound === "1") return;
      element.dataset.premiumRevealBound = "1";
      element.classList.add("premium-reveal");
      if (revealObserver) {
        revealObserver.observe(element);
      } else {
        element.classList.add("is-visible");
      }
    });
  }

  function refreshEnhancements() {
    refreshScheduled = false;
    updateClockChip();
    updateExecutiveChips();
    markEmptyStates();
    bindRevealTargets();
    enhanceNumbers();
  }

  function scheduleRefresh() {
    if (refreshScheduled) return;
    refreshScheduled = true;
    requestAnimationFrame(refreshEnhancements);
  }

  function initMutationObserver() {
    if (mutationObserver) return;
    mutationObserver = new MutationObserver(() => {
      if (performance.now() < ignoreMutationsUntil) return;
      scheduleRefresh();
    });
    mutationObserver.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true
    });
  }

  function init() {
    document.body.classList.add("premium-ui-active");
    refreshEnhancements();
    initMutationObserver();
    window.setInterval(updateClockChip, 30000);
    window.setInterval(updateExecutiveChips, 3000);
    window.addEventListener("hashchange", scheduleRefresh);
    window.addEventListener("resize", scheduleRefresh);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
}());
