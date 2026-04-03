const KEYWORD_SENTIMENTS = ["Positive", "Neutral", "Negative"];
const SENTIMENT_KEYWORD_FALLBACK_URL = "/sentiment-keyword-groups.json?v=20260401a";

function emptyKeywordGroups() {
  return {
    Positive: [],
    Neutral: [],
    Negative: []
  };
}

function hasKeywordGroups(keywordGroups) {
  const groups = Array.isArray(keywordGroups)
    ? { ...emptyKeywordGroups(), Negative: keywordGroups }
    : (keywordGroups ? { ...emptyKeywordGroups(), ...keywordGroups } : emptyKeywordGroups());
  return KEYWORD_SENTIMENTS.some((sentiment) => Array.isArray(groups[sentiment]) && groups[sentiment].length);
}

function normalizeKeywordGroups(keywordGroups) {
  return Array.isArray(keywordGroups)
    ? { ...emptyKeywordGroups(), Negative: keywordGroups }
    : (keywordGroups ? { ...emptyKeywordGroups(), ...keywordGroups } : emptyKeywordGroups());
}

async function loadStaticKeywordGroups(timeoutMs = 4000) {
  const controller = new AbortController();
  const timeoutHandle = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(SENTIMENT_KEYWORD_FALLBACK_URL, {
      method: "GET",
      cache: "no-store",
      signal: controller.signal
    });
    if (!response.ok) return null;
    const payload = await response.json();
    const groups = normalizeKeywordGroups(payload?.keywords_by_sentiment || payload);
    return hasKeywordGroups(groups) ? groups : null;
  } catch (error) {
    return null;
  } finally {
    window.clearTimeout(timeoutHandle);
  }
}

function renderKeywords(keywordGroups = state.keywordGroups) {
  const host = $("#keywordList");
  if (!host) return;
  const groups = normalizeKeywordGroups(keywordGroups);
  const hasKeywords = hasKeywordGroups(groups);
  if (!hasKeywords) {
    const errorMessage = String(state.dashboardKeywordsError || "").trim();
    host.innerHTML = state.dashboardKeywordsLoading
      ? '<div class="keyword-caption">Loading sentiment keyword groups...</div>'
      : errorMessage
        ? '<div class="keyword-caption">' + escapeHtml(errorMessage) + "</div>"
        : '<div class="keyword-caption">Sentiment keyword groups will appear after analytics load.</div>';
    return;
  }
  host.innerHTML = KEYWORD_SENTIMENTS.map((sentiment) => {
    const tone = sentiment.toLowerCase();
    const rows = Array.isArray(groups[sentiment]) ? groups[sentiment].slice(0, 4) : [];
    const maxCount = Math.max(1, ...rows.map((item) => Number(item.count || 0)), 1);
    const content = rows.length
      ? rows.map((item) => {
        const width = clamp((Number(item.count || 0) / maxCount) * 100, 0, 100);
        return [
          '<div class="keyword-row">',
          "<strong>" + escapeHtml(String(item.word || "")) + "</strong>",
          '<div class="keyword-bar"><span class="keyword-bar__fill keyword-bar__fill--' + tone + '" style="width:' + width.toFixed(2) + '%;"></span></div>',
          "<span>" + Number(item.count || 0).toLocaleString() + "</span>",
          "</div>"
        ].join("");
      }).join("")
      : '<div class="keyword-group__empty">No ' + tone + ' keywords in the current snapshot.</div>';
    return [
      '<section class="keyword-group" data-tone="' + sentiment + '">',
      '<div class="keyword-group__head">',
      '<strong class="keyword-group__title">' + sentiment + " keywords</strong>",
      '<span class="keyword-group__meta">' + Number(rows.length || 0) + " visible</span>",
      "</div>",
      '<div class="keyword-group__rows">' + content + "</div>",
      "</section>"
    ].join("");
  }).join("");
}

async function refreshDashboardKeywordGroups(options = {}) {
  const sessionRevision = Number.isFinite(Number(options.sessionRevision)) ? Number(options.sessionRevision) : state.sessionRevision;
  const requestSeq = Number.isFinite(Number(options.requestSeq)) ? Number(options.requestSeq) : ++state.dashboardKeywordRequestSeq;
  const timeoutMs = Number.isFinite(Number(options.timeoutMs)) ? Number(options.timeoutMs) : 90000;
  const hadKeywords = hasKeywordGroups(state.keywordGroups);
  const staticFallbackPromise = !hadKeywords
    ? loadStaticKeywordGroups(4000).then((groups) => {
      if (!groups) return false;
      if (!sameSessionRevision(sessionRevision) || requestSeq !== state.dashboardKeywordRequestSeq) return false;
      if (hasKeywordGroups(state.keywordGroups)) return true;
      state.keywordGroups = groups;
      state.keywords = groups.Negative.slice();
      state.dashboardKeywordsError = "";
      renderDashboardAnalyticsState();
      renderRoleDashboardPanel();
      return true;
    })
    : Promise.resolve(false);
  state.dashboardKeywordsLoading = true;
  state.dashboardKeywordsError = "";
  renderDashboardAnalyticsState();
  renderRoleDashboardPanel();
  try {
    const groupedKeywordsPayload = await callApi("/dashboard/keywords?group_by=sentiment", { timeoutMs });
    if (!sameSessionRevision(sessionRevision) || requestSeq !== state.dashboardKeywordRequestSeq) return false;
    const nextKeywordGroups = normalizeKeywordGroups(groupedKeywordsPayload?.keywords_by_sentiment || {});
    if (!hasKeywordGroups(nextKeywordGroups)) {
      throw new Error("Sentiment keyword groups are still being prepared.");
    }
    state.keywordGroups = nextKeywordGroups;
    state.keywords = nextKeywordGroups.Negative.slice();
    state.dashboardKeywordsError = "";
    return true;
  } catch (error) {
    if (!sameSessionRevision(sessionRevision) || requestSeq !== state.dashboardKeywordRequestSeq) return false;
    if (handleAuthError(error)) return false;
    await staticFallbackPromise;
    if (hasKeywordGroups(state.keywordGroups)) {
      state.dashboardKeywordsError = "";
      return true;
    }
    if (!hadKeywords) {
      state.keywords = [];
      state.keywordGroups = emptyKeywordGroups();
    }
    const message = String(error && error.message ? error.message : "").trim();
    state.dashboardKeywordsError = message || "Unable to load sentiment keyword groups.";
    return false;
  } finally {
    if (!sameSessionRevision(sessionRevision) || requestSeq !== state.dashboardKeywordRequestSeq) return;
    state.dashboardKeywordsLoading = false;
    renderDashboardAnalyticsState();
    renderRoleDashboardPanel();
  }
}
