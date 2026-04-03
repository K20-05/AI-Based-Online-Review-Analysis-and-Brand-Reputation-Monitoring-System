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
    const safeBrand = escapeHtml(String(item.brand || "Unknown brand"));
    return [
      '<article class="similar-item">',
      '<div><strong>#' + String(index + 1) + " " + safeBrand + '</strong><span>Positive ' + Number(item.positive_pct || 0).toFixed(1) + '%</span></div>',
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
  const topKeyword = Array.isArray(state.keywords) && state.keywords[0]
    ? String(state.keywords[0].word || "").trim().replace(/^#/, "")
    : "";
  if (Number(warningBrand.negative_pct || 0) >= 40) {
    const topicCopy = topKeyword
      ? escapeHtml(topKeyword.replace(/^\w/, (char) => char.toUpperCase()) + " complaints increasing.")
      : "Delivery complaints increasing.";
    warningTitle.textContent = warningBrand.brand + " negative sentiment rising";
    warningCopy.innerHTML = [
      '<div class="marketing-warning">',
      '<span class="marketing-warning-chip warning-critical">High Warning</span>',
      '<div class="marketing-warning-lines">',
      '<div><strong>Signal</strong> Negative share at ' + Number(warningBrand.negative_pct || 0).toFixed(1) + '%.</div>',
      '<div><strong>Topic</strong> ' + topicCopy + "</div>",
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

function getTrendLabel(value, positiveDirection = true) {
  if (value >= 60) return positiveDirection ? "Rising" : "High";
  if (value >= 35) return "Stable";
  return positiveDirection ? "Low" : "Contained";
}

function formatRealtimeTimestamp(value) {
  if (!value) return "Waiting";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Waiting";
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function setTrendIcon(icon, direction) {
  const stroke = direction === "up" ? "var(--positive)" : direction === "down" ? "var(--negative)" : "var(--neutral)";
  if (icon) icon.setAttribute("stroke", stroke);
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
    const heading = section && section.heading ? '<h2>' + escapeHtml(section.heading) + "</h2>" : "";
    const body = Array.isArray(section?.rows)
      ? section.rows.map((row) => "<li>" + escapeHtml(row) + "</li>").join("")
      : "";
    return '<section class="report-section">' + heading + "<ul>" + body + "</ul></section>";
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
  const signalConfidenceGauge = $("#signalConfidenceGauge");
  const signalConfidenceNote = $("#signalConfidenceNote");
  if (!signalConfidenceGauge && !signalConfidenceNote) return;
  const numeric = Number.isFinite(confidence) ? clamp(confidence, 0, 100) : 0;
  const color = sentimentClass(sentiment) === "sentiment-positive"
    ? "var(--positive)"
    : sentimentClass(sentiment) === "sentiment-negative"
      ? "var(--negative)"
      : "var(--neutral)";

  renderGauge(signalConfidenceGauge, numeric, {
    displayValue: numeric ? numeric.toFixed(0) : "0",
    label: "Latest Signal",
    suffix: "%",
    caption: numeric ? "Confidence from the most recent prediction event." : "Confidence updates after prediction events.",
    color
  });

  if (signalConfidenceNote) {
    signalConfidenceNote.textContent = numeric
      ? sentiment + " classification detected with " + numeric.toFixed(1) + "% confidence."
      : "No recent prediction event.";
  }
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
  state.trendReviewSamplesCache = {};
  state.trendDataLoading = true;
  renderRoleDashboardPanel();
  $("#trendCaption").textContent = "Loading trend data...";
  try {
    const payload = await callApi(trendsEndpoint(selectedBrand), { timeoutMs: 30000 });
    if (requestSeq !== state.trendRequestSeq) return;
    state.trends = Array.isArray(payload.trends) ? payload.trends : [];
    renderTrendChart(getWindowedTrends());
    renderTrendMomentum();
    renderTrendMonthlyComparison();
    renderTrendReviewVolume();
    prefetchTrendDrilldownSamples();
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
  } finally {
    if (requestSeq !== state.trendRequestSeq) return;
    state.trendDataLoading = false;
    renderRoleDashboardPanel();
  }
}
