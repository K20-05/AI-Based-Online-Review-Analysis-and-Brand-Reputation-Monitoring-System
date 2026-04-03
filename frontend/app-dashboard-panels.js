(function () {
  function createDashboardPanelsModule(deps) {
    const {
      state,
      $,
      $$,
      normalizeAccessRole,
      normalizeBrandScore,
      formatRealtimeTimestamp,
      riskMeta,
      renderPillList,
      customerVoiceWindowLabel,
      activeTrendBrandLabel,
      getScoreExtremes,
      getWindowedTrends,
      escapeHtml,
      callApi,
      sameSessionRevision,
      handleAuthError,
      viewRouter,
      renderBrandInsights,
      toast,
      reviewMetaCard,
      buildReviewDrilldownItem
    } = deps;

    function renderComplaintTopics(hostId = "analystComplaintTopicsList", noteId = "analystComplaintTopicsNote") {
      const host = $("#" + hostId);
      const note = $("#" + noteId);
      if (!host || !note) return;
      const analystView = hostId === "analystComplaintTopicsList";
      const scopedKeywords = analystView && Array.isArray(state.customerVoiceKeywords) ? state.customerVoiceKeywords : [];
      const portfolioKeywords = Array.isArray(state.keywords) ? state.keywords : [];
      const usingPortfolioFallback = analystView && !scopedKeywords.length && portfolioKeywords.length > 0;
      const sourceKeywords = analystView
        ? (scopedKeywords.length ? scopedKeywords : (usingPortfolioFallback ? portfolioKeywords : []))
        : portfolioKeywords;
      if (analystView && state.customerVoiceKeywordsLoading) {
        host.innerHTML = "<span>Loading complaint themes</span>";
        note.textContent = "Updating complaint themes for the current brand and time window.";
        return;
      }
      if (analystView && state.customerVoiceKeywordsError && (!Array.isArray(sourceKeywords) || !sourceKeywords.length)) {
        host.innerHTML = "<span>Complaint themes unavailable</span>";
        note.textContent = state.customerVoiceKeywordsError;
        return;
      }
      if (!Array.isArray(sourceKeywords) || !sourceKeywords.length) {
        host.innerHTML = "<span>Waiting for keyword analytics</span>";
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
      if (analystView && usingPortfolioFallback) {
        note.textContent = state.customerVoiceBrand
          ? "Showing portfolio complaint topics while " + state.customerVoiceBrand + " themes load."
          : "Showing overall complaint themes for the current dashboard snapshot.";
        return;
      }
      if (analystView && state.customerVoiceKeywordsFallback && state.customerVoiceKeywordsError) {
        note.textContent = state.customerVoiceKeywordsError;
        return;
      }
      note.textContent = analystView
        ? ((state.customerVoiceBrand ? state.customerVoiceBrand + " selected. " : "All brands selected. ") + "Complaint themes shown for " + customerVoiceWindowLabel().toLowerCase() + ".")
        : "Current negative share: " + Number(state.brandScore?.negative_pct || 0).toFixed(1) + "%. Topics shown from highest-frequency keywords.";
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
      host.innerHTML = samples.map((item, index) => {
        const brandLabel = String(item.brand || "Unknown brand").trim() || "Unknown brand";
        const platformLabel = String(item.platform || "Unknown platform").trim() || "Unknown platform";
        const reviewDate = String(item.review_date || "Unknown date").trim() || "Unknown date";
        const ratingSummary = item.rating ? String(item.rating).trim() + "/5" : "Not rated";
        const preview = String(item.review_text || "");
        const shortPreview = preview.length > 88 ? preview.slice(0, 88).trim() + "..." : preview;
        const detailSections = [
          '<div class="review-drilldown-pillrow"><span>Trend window sample</span><span>Scope ' + escapeHtml(scope) + "</span></div>",
          '<p class="review-drilldown-text">"' + escapeHtml(preview) + '"</p>'
        ];
        return buildReviewDrilldownItem({
          sentiment,
          brand: brandLabel,
          platform: platformLabel,
          identitySubtitle: "Review source",
          sideLabel: scope,
          modeBadge: "Sample",
          detailLabel: "Expand",
          metaCards: [
            reviewMetaCard("Brand", brandLabel),
            reviewMetaCard("Platform", platformLabel),
            reviewMetaCard("Date", reviewDate),
            reviewMetaCard("Rating", ratingSummary)
          ],
          preview: '"' + shortPreview + '"',
          detailSections,
          open: index === 0
        });
      }).join("");
    }

    function trendReviewSampleCacheKey(sentiment, brand = state.trendBrand || "", months = state.trendWindow || "all") {
      return [String(sentiment || "").trim(), String(brand || "").trim(), String(months || "all").trim()].join("::");
    }

    function fetchTrendDrilldownSamples(sentiment, options = {}) {
      const chosen = String(sentiment || "").trim();
      if (!chosen) return Promise.resolve([]);
      const brand = state.trendBrand || "";
      const months = String(state.trendWindow || "all");
      const cacheKey = trendReviewSampleCacheKey(chosen, brand, months);
      const cached = state.trendReviewSamplesCache[cacheKey];
      if (cached && cached.status === "fulfilled") {
        return Promise.resolve(cached.samples);
      }
      if (cached && cached.promise) {
        return cached.promise;
      }

      const params = new URLSearchParams({
        sentiment: chosen,
        months,
        limit: "5"
      });
      if (brand) params.set("brand", brand);

      const promise = callApi("/dashboard/reviews?" + params.toString(), {
        timeoutMs: Number.isFinite(options.timeoutMs) ? Number(options.timeoutMs) : 60000
      }).then((payload) => {
        const samples = Array.isArray(payload.samples) ? payload.samples : [];
        state.trendReviewSamplesCache[cacheKey] = { status: "fulfilled", samples };
        return samples;
      }).catch((error) => {
        delete state.trendReviewSamplesCache[cacheKey];
        throw error;
      });

      state.trendReviewSamplesCache[cacheKey] = { status: "pending", promise };
      return promise;
    }

    function prefetchTrendDrilldownSamples() {
      const role = normalizeAccessRole(state.userRole);
      if (role !== "analyst" && role !== "admin") return;
      if (!Array.isArray(state.trends) || !state.trends.length) return;
      const brandSnapshot = state.trendBrand || "";
      const monthsSnapshot = String(state.trendWindow || "all");

      window.setTimeout(async () => {
        for (const sentiment of ["Positive", "Neutral", "Negative"]) {
          if (brandSnapshot !== (state.trendBrand || "") || monthsSnapshot !== String(state.trendWindow || "all")) return;
          try {
            await fetchTrendDrilldownSamples(sentiment, { timeoutMs: 60000 });
          } catch (error) {
            return;
          }
        }
      }, 0);
    }

    async function loadTrendDrilldown(sentiment) {
      const role = normalizeAccessRole(state.userRole);
      if (role !== "analyst" && role !== "admin") return;
      const sessionRevision = state.sessionRevision;
      const title = $("#trendDrilldownTitle");
      const copy = $("#trendDrilldownCopy");
      const host = $("#trendReviewDrilldown");
      if (!title || !copy || !host) return;
      const chosen = String(sentiment || "").trim();
      if (!chosen) return;
      setTrendDrilldownActive(chosen);
      const cacheKey = trendReviewSampleCacheKey(chosen);
      const cached = state.trendReviewSamplesCache[cacheKey];
      if (cached && cached.status === "fulfilled") {
        renderTrendDrilldownSamples(cached.samples, chosen);
        return;
      }
      title.textContent = chosen + " Review Samples";
      copy.textContent = "Loading real review samples...";
      host.innerHTML = '<div class="mini-note">Fetching matching reviews from the prediction dataset.</div>';
      try {
        const samples = await fetchTrendDrilldownSamples(chosen, { timeoutMs: 60000 });
        if (!sameSessionRevision(sessionRevision)) return;
        renderTrendDrilldownSamples(samples, chosen);
      } catch (error) {
        if (!sameSessionRevision(sessionRevision)) return;
        if (handleAuthError(error)) return;
        copy.textContent = "Unable to load review samples: " + (error.message || "request failed") + ".";
        host.innerHTML = '<div class="mini-note">Review drill-down is unavailable right now.</div>';
      }
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

    function formatRoleCards(items) {
      return (items || []).map((item) => {
        const className = item.view ? "role-mini-card is-link" : "role-mini-card";
        const safeLabel = escapeHtml(String(item.label || ""));
        const safeValue = escapeHtml(String(item.value || ""));
        const safeCopy = escapeHtml(String(item.copy || ""));
        const scrollTargetAttr = item.scrollTarget ? ' data-scroll-target="' + escapeHtml(item.scrollTarget) + '"' : "";
        const compareAAttr = item.compareA ? ' data-compare-a="' + escapeHtml(item.compareA) + '"' : "";
        const compareBAttr = item.compareB ? ' data-compare-b="' + escapeHtml(item.compareB) + '"' : "";
        const attrs = item.view
          ? ' data-view="' + escapeHtml(item.view) + '"' + scrollTargetAttr + compareAAttr + compareBAttr + ' role="button" tabindex="0"'
          : "";
        return [
          '<article class="' + className + '"' + attrs + '>',
          '<span class="role-mini-label">' + safeLabel + "</span>",
          '<strong class="role-mini-value">' + safeValue + "</strong>",
          '<p class="role-mini-copy">' + safeCopy + "</p>",
          item.view ? '<span class="role-mini-action">Open</span>' : "",
          "</article>"
        ].join("");
      }).join("");
    }

    function renderRoleDashboardPanel() {
      const role = normalizeAccessRole(state.userRole);
      const score = state.brandScore || normalizeBrandScore({});
      const realtimeSummary = state.realtimeSummary || {};
      const realtimeStamp = formatRealtimeTimestamp(realtimeSummary.latest_ingested_at);
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
        eyebrow = "Brand Coverage";
        title = "Tracked Brands";
        copy = "Select a monitored brand to open its intelligence workspace.";
        const brands = (Array.isArray(state.brands) ? state.brands : [])
          .map((item) => String(item.brand || "").trim())
          .filter(Boolean)
          .sort((a, b) => a.localeCompare(b));
        $("#roleDashboardEyebrow").textContent = eyebrow;
        $("#roleDashboardTitle").textContent = title;
        $("#roleDashboardCopy").textContent = copy;
        $("#roleDashboardCards").innerHTML = brands.length
          ? brands.map((brand) => {
            const safeBrand = escapeHtml(brand);
            return '<button class="brand-quick-btn" type="button" data-brand="' + safeBrand + '">' + safeBrand + "<b>OPEN</b></button>";
          }).join("")
          : '<div class="mini-note">Tracked brands will appear here after analytics data loads.</div>';
        return;
      }

      if (role === "marketing_staff") {
        eyebrow = "Brand Monitoring";
        title = "Marketing Snapshot";
        copy = "Score, leaders, and live movement.";
        const comparePair = extremes.leader && extremes.lagger
          ? extremes.leader.brand + " vs " + extremes.lagger.brand
          : (extremes.leader ? extremes.leader.brand + " lead" : "Waiting");
        cards = [
          {
            label: "Score",
            value: Number(score.brand_reputation_score || 0).toFixed(1),
            copy: "Current reputation",
            view: "brand-insights"
          },
          {
            label: "Leader",
            value: extremes.leader ? extremes.leader.brand : "Waiting",
            copy: extremes.leader ? "Top ranked" : "Waiting",
            view: "analytics-summary"
          },
          {
            label: "Compare",
            value: comparePair,
            copy: extremes.leader && extremes.lagger ? "Open side-by-side comparison" : "Select brands to compare",
            view: "brand-insights",
            compareA: extremes.leader ? extremes.leader.brand : "",
            compareB: extremes.lagger ? extremes.lagger.brand : "",
            scrollTarget: "compareSummary"
          },
          {
            label: "Last Sync",
            value: realtimeStamp,
            copy: "Live review intake",
            view: "dashboard",
            scrollTarget: "dashboardRealtimeReviewList"
          }
        ];
      } else {
        eyebrow = "Analysis";
        title = "Analyst Snapshot";
        copy = "Trends, complaints, and review volume.";
        const trendCount = Array.isArray(state.trends) ? state.trends.length : 0;
        const trendValue = trendCount
          ? String(trendCount) + " months"
          : (state.trendDataLoading ? "Loading" : "0 months");
        const keywordValue = Array.isArray(state.keywords) && state.keywords[0]
          ? String(state.keywords[0].word || "").replace(/^#/, "").replace(/^\w/, (char) => char.toUpperCase())
          : (state.dashboardKeywordsLoading ? "Loading" : "Waiting");
        const complaintTopic = Array.isArray(state.customerVoiceKeywords) && state.customerVoiceKeywords[0]
          ? "#" + state.customerVoiceKeywords[0].word
          : (Array.isArray(state.keywords) && state.keywords[0]
            ? "#" + state.keywords[0].word
            : (state.customerVoiceKeywordsLoading ? "Loading" : "Waiting"));
        const reviewValue = Number(score.total_reviews || 0) > 0
          ? Number(score.total_reviews || 0).toLocaleString()
          : (state.latestSource !== "No endpoint call yet" ? "0" : "Loading");
        const complaintLabel = complaintTopic && complaintTopic !== "Waiting" && complaintTopic !== "Loading"
          ? complaintTopic.replace(/^#/, "").replace(/^\w/, (char) => char.toUpperCase())
          : complaintTopic;
        cards = [
          {
            label: "Trend Desk",
            value: "Review Trends",
            copy: trendCount
              ? trendValue + " loaded for monthly analysis."
              : (state.trendDataLoading ? "Loading trend history for analysis." : "Open monthly sentiment movement."),
            view: "review-trends"
          },
          {
            label: "Keyword Map",
            value: "Sentiment Insights",
            copy: keywordValue !== "Waiting" && keywordValue !== "Loading"
              ? "Primary signal: " + keywordValue + "."
              : (state.dashboardKeywordsLoading ? "Loading grouped keyword signals." : "Open grouped positive and negative keywords."),
            view: "sentiment-distribution"
          },
          {
            label: "Voice Board",
            value: "Customer Voice",
            copy: complaintLabel !== "Waiting" && complaintLabel !== "Loading"
              ? "Top theme: " + complaintLabel + "."
              : (state.customerVoiceKeywordsLoading ? "Loading complaint themes." : "Open brand-level complaint themes."),
            view: "customer-intelligence"
          },
          {
            label: "Review Queue",
            value: "Evidence Feed",
            copy: reviewValue !== "Loading"
              ? reviewValue + " reviews in the active snapshot."
              : "Waiting for synced review volume.",
            view: "dashboard",
            scrollTarget: "dashboardRealtimeReviewList"
          }
        ];

        if (!cards.length && negativeDelta > 0 && risk.label) {
          cards = [{
            label: "Risk",
            value: risk.label,
            copy: "Negative drift +" + negativeDelta.toFixed(1),
            view: "review-trends"
          }];
        }
      }

      $("#roleDashboardEyebrow").textContent = eyebrow;
      $("#roleDashboardTitle").textContent = title;
      $("#roleDashboardCopy").textContent = copy;
      $("#roleDashboardCards").innerHTML = formatRoleCards(cards);
    }

    function openBrandFromRoleDashboard(button) {
      const brand = button?.dataset?.brand || "";
      if (!brand) return;
      $("#brandInsightSelect").value = brand;
      viewRouter("brand-insights");
      renderBrandInsights();
      toast("Showing insights for " + brand + ".", "success");
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
        ? "Top negative keyword from the current analyst keyword view."
        : "Top keyword signal will appear here.";

      complaintTitle.textContent = topComplaint ? topComplaint.replace(/^\w/, (char) => char.toUpperCase()) : "Waiting";
      complaintCopy.textContent = topComplaint
        ? "Top complaint theme from customer voice."
        : "Top complaint theme will appear here.";
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
        copy.textContent = "Keyword #" + keywords[0].word + " is the strongest negative review signal in the current dataset. Use it to guide deeper analysis.";
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

    function pathFromPoints(points) {
      if (!points.length) return "";
      return points.map((point, index) => (index ? "L" : "M") + point.x + " " + point.y).join(" ");
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

    return {
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

  window.BrandPulseDashboardPanels = { createDashboardPanelsModule };
}());
