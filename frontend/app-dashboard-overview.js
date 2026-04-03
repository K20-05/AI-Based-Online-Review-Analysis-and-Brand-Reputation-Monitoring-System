(function () {
  function createDashboardOverviewModule(deps) {
    const {
      state,
      $,
      normalizeAccessRole,
      normalizeBrandScore,
      formatRealtimeTimestamp,
      riskMeta,
      escapeHtml,
      getScoreExtremes,
      reviewMetaCard,
      buildReviewDrilldownItem
    } = deps;

    const SUPPORTED_LANGUAGE_LABELS = [
      "English",
      "Hindi",
      "Tamil",
      "Telugu",
      "Malayalam",
      "Kannada",
      "Bengali",
      "Marathi",
      "Gujarati",
      "Punjabi",
      "Urdu"
    ];

    function scoreNarrative(score) {
      if (score >= 70) return ["Reputation surge", "Audience response is strongly favorable across the active review stream."];
      if (score >= 40) return ["Healthy trajectory", "Brand sentiment remains positive with manageable negative drag."];
      if (score >= 15) return ["Mixed field conditions", "Positive and negative signals are close enough to require attention."];
      if (score >= 0) return ["Fragile balance", "Negative pressure is near parity and could flip the score quickly."];
      return ["Critical drift", "Negative sentiment is overpowering the positive stream. Escalation recommended."];
    }

    function dashboardSourceLabel(value) {
      const text = String(value || "").trim();
      if (!text || text === "No endpoint call yet") return "Awaiting sync";
      const firstSpace = text.indexOf(" ");
      const method = firstSpace === -1 ? "GET" : text.slice(0, firstSpace);
      const rawTarget = firstSpace === -1 ? text : text.slice(firstSpace + 1).trim();
      try {
        const parsed = new URL(rawTarget);
        return method + " " + (parsed.pathname || parsed.host || rawTarget);
      } catch (error) {
        return text.length > 36 ? text.slice(0, 33) + "..." : text;
      }
    }

    function dashboardRoleContent(role) {
      const resolved = normalizeAccessRole(role);
      if (resolved === "admin") {
        return {
          label: "Admin Control",
          meta: "Platform health and access.",
          mode: "Operations"
        };
      }
      if (resolved === "marketing_staff") {
        return {
          label: "Marketing Monitor",
          meta: "Brand watch and early risk.",
          mode: "Campaign"
        };
      }
      return {
        label: "Analyst Mode",
        meta: "Sentiment and live review watch.",
        mode: "Analysis"
      };
    }

    function dashboardLeadKeyword() {
      const raw = Array.isArray(state.keywords) && state.keywords[0]
        ? String(state.keywords[0].word || "").trim()
        : "";
      if (raw) return raw.replace(/^#/, "").replace(/^\w/, (char) => char.toUpperCase());
      return state.dashboardKeywordsLoading ? "Loading" : "Waiting";
    }

    function dashboardComplaintTheme() {
      const raw = Array.isArray(state.customerVoiceKeywords) && state.customerVoiceKeywords[0]
        ? String(state.customerVoiceKeywords[0].word || "").trim()
        : (Array.isArray(state.keywords) && state.keywords[0]
          ? String(state.keywords[0].word || "").trim()
          : "");
      if (raw) return raw.replace(/^#/, "").replace(/^\w/, (char) => char.toUpperCase());
      return state.customerVoiceKeywordsLoading ? "Loading" : "Waiting";
    }

    function dashboardStatusPillModel(context = {}) {
      const resolved = normalizeAccessRole(state.userRole);
      const liveCount = Number(context.realtimeCount || 0);
      const liveCountLabel = liveCount.toLocaleString() + (liveCount === 1 ? " live review" : " live reviews");
      const pipelineStatus = String(context.pipelineStatus || "Standby");
      const activeAlerts = Number(context.activeAlerts || 0);
      const leaderName = context.leader ? String(context.leader.brand || "").trim() : "";
      const keywordSignal = dashboardLeadKeyword();

      if (resolved === "marketing_staff") {
        return {
          label: "Portfolio Leader",
          value: leaderName || "Waiting",
          meta: leaderName
            ? leaderName + " currently leads the portfolio on reputation score."
            : "Leader will appear after analytics data loads.",
          tone: leaderName ? "live" : "waiting"
        };
      }

      if (resolved === "analyst") {
        return {
          label: "Signal Focus",
          value: keywordSignal,
          meta: keywordSignal !== "Waiting" && keywordSignal !== "Loading"
            ? keywordSignal + " is the strongest recurring keyword signal right now."
            : state.dashboardKeywordsLoading
              ? "Loading the strongest recurring keyword signal."
              : "Signal focus will appear after analytics data loads.",
          tone: keywordSignal === "Waiting" ? "waiting" : "ready"
        };
      }

      return {
        label: "System Status",
        value: activeAlerts > 0
          ? activeAlerts + (activeAlerts === 1 ? " Alert" : " Alerts")
          : pipelineStatus,
        meta: activeAlerts > 0
          ? activeAlerts + (activeAlerts === 1 ? " operational alert needs review." : " operational alerts need review.")
          : context.hasLiveIngest && liveCount > 0
            ? liveCountLabel + " buffered. Last ingest " + (context.realtimeStamp || "Waiting") + "."
            : (context.hasSynced
              ? "Data is synced and waiting for new live reviews."
              : "Waiting for first sync."),
        tone: activeAlerts > 0
          ? "alert"
          : pipelineStatus === "Live"
            ? "live"
            : context.hasSynced
              ? "ready"
              : "waiting"
      };
    }

    function dashboardStatusPillClassName(tone) {
      const resolvedTone = String(tone || "").trim().toLowerCase();
      return "dashboard-status-pill dashboard-status-pill--spotlight is-" + (resolvedTone || "waiting");
    }

    function dashboardOverviewModel(score, context = {}) {
      const resolved = normalizeAccessRole(state.userRole);
      const narrative = scoreNarrative(score.brand_reputation_score);
      const totalReviews = Number(score.total_reviews || 0);
      const negativePct = Number(score.negative_pct || 0);
      const liveCount = Number(context.realtimeCount || 0);
      const liveCountLabel = liveCount.toLocaleString() + (liveCount === 1 ? " live review" : " live reviews");
      const trendCount = Array.isArray(state.trends) ? state.trends.length : 0;
      const trendWindow = trendCount ? String(trendCount) + " months" : (state.trendDataLoading ? "Loading" : "0 months");
      const keywordSignal = dashboardLeadKeyword();
      const complaintTheme = dashboardComplaintTheme();
      const leaderName = context.leader ? String(context.leader.brand || "").trim() : "";
      const laggerName = context.lagger ? String(context.lagger.brand || "").trim() : "";
      const syncStatusCopy = context.hasSynced ? "Source synced successfully." : "Waiting for first sync.";

      if (resolved === "marketing_staff") {
        const compareReady = leaderName && laggerName ? leaderName + " vs " + laggerName : "Waiting";
        return {
          narrativeLabel: "Market Position",
          narrativeTitle: leaderName ? leaderName + " is leading" : narrative[0],
          narrativeCopy: leaderName && laggerName
            ? leaderName + " currently leads the portfolio. Compare it with " + laggerName + " before making campaign calls."
            : "Track portfolio leadership, brand risk, and comparison readiness from one market-facing view.",
          gaugeLabel: "Brand Reputation",
          gaugeCaption: "Current score for the active portfolio in marketing monitor mode.",
          quickStats: [
            {
              label: "Risk Window",
              value: context.risk?.label || "Standby",
              meta: negativePct.toFixed(1) + "% negative across " + totalReviews.toLocaleString() + " reviews."
            },
            {
              label: "Portfolio Reach",
              value: totalReviews.toLocaleString(),
              meta: syncStatusCopy
            },
            {
              label: "Brand Leader",
              value: leaderName || "Waiting",
              meta: leaderName
                ? "Highest reputation brand in the current portfolio."
                : "Leader will appear after analytics data loads."
            },
            {
              label: "Compare Ready",
              value: compareReady,
              meta: leaderName && laggerName
                ? "Open a side-by-side view to compare leading and lagging brands."
                : "At least two brands are needed for comparison."
            }
          ]
        };
      }

      if (resolved === "analyst") {
        const analystTitle = Number(context.negativeDelta || 0) > 0.5
          ? "Negative pressure is rising"
          : keywordSignal !== "Waiting" && keywordSignal !== "Loading"
            ? "Keyword focus: " + keywordSignal
            : narrative[0];
        return {
          narrativeLabel: "Signal Watch",
          narrativeTitle: analystTitle,
          narrativeCopy: liveCount
            ? liveCountLabel + " ready for review. Validate the shift with trends, complaints, and recent evidence."
            : "Use trend windows, complaint themes, and synced evidence to validate the signal before drawing conclusions.",
          gaugeLabel: "Sentiment Balance",
          gaugeCaption: "Current score framed as an analyst-facing signal snapshot.",
          quickStats: [
            {
              label: "Negative Share",
              value: negativePct.toFixed(1) + "%",
              meta: totalReviews.toLocaleString() + " reviews in the current analysis window."
            },
            {
              label: "Trend Window",
              value: trendWindow,
              meta: trendCount ? "Historical span loaded for trend analysis." : "Trend data will appear after loading."
            },
            {
              label: "Live Evidence",
              value: liveCount
                ? liveCount.toLocaleString()
                : (context.hasLiveIngest ? "Live" : (context.hasSynced ? "Synced only" : "Standby")),
              meta: liveCount
                ? liveCountLabel + " available in the evidence queue."
                : (context.hasSynced
                  ? "Using synced data until new live reviews arrive."
                  : "Evidence queue is waiting for data.")
            },
            {
              label: "Complaint Watch",
              value: complaintTheme,
              meta: complaintTheme !== "Waiting" && complaintTheme !== "Loading"
                ? complaintTheme + " is the dominant complaint signal."
                : "Complaint themes will appear after analytics data loads."
            }
          ]
        };
      }

      return {
        narrativeLabel: "Executive Insight",
        narrativeTitle: narrative[0],
        narrativeCopy: narrative[1],
        gaugeLabel: "Brand Reputation",
        gaugeCaption: "Current score from the latest `/dashboard/summary` response.",
        quickStats: [
          {
            label: "Risk",
            value: context.risk?.label || "Standby",
            meta: negativePct.toFixed(1) + "% negative across " + totalReviews.toLocaleString() + " reviews."
          },
          {
            label: "Total Reviews",
            value: totalReviews.toLocaleString(),
            meta: syncStatusCopy
          },
          {
            label: "Pipeline",
            value: context.pipelineStatus || "Standby",
            meta: context.hasLiveIngest && liveCount > 0
              ? liveCountLabel + " buffered. Last ingest " + (context.realtimeStamp || "Waiting") + "."
              : (context.hasSynced
                ? "Synced. Waiting for new live reviews."
                : "No ingest activity yet.")
          },
          {
            label: "Alerts",
            value: context.activeAlerts > 0
              ? context.activeAlerts + (context.activeAlerts === 1 ? " Alert" : " Alerts")
              : "Clear",
            meta: context.activeAlerts > 0 ? "Attention needed in the current snapshot." : "No active alerts."
          }
        ]
      };
    }

    function activeAdminAlertCount(score = state.brandScore || normalizeBrandScore({})) {
      const notifications = Array.isArray(state.adminNotifications) ? state.adminNotifications : [];
      if (notifications.length) {
        return notifications.filter((item) => item.level !== "success").length;
      }

      let count = 0;
      const modelAccuracy = Number(state.modelMetrics?.test_accuracy || 0);
      const validationAccuracy = Number(state.modelMetrics?.validation_accuracy || 0);
      const negativePct = Number(score?.negative_pct || 0);

      if (!state.modelMetrics) {
        count += 1;
      } else {
        if (modelAccuracy > 0 && modelAccuracy < 0.8) count += 1;
        if (validationAccuracy > 0 && modelAccuracy > 0 && Math.abs(validationAccuracy - modelAccuracy) > 0.08) count += 1;
      }

      if (negativePct >= 40) count += 1;
      if (state.usersLoaded && (state.users || []).length <= 1) count += 1;
      return count;
    }

    function renderDashboardOverview(score) {
      const roleContent = dashboardRoleContent(state.userRole);
      const risk = riskMeta(score.brand_reputation_score, score.negative_pct);
      const realtimeCount = Number(state.realtimeSummary?.total_reviews || 0);
      const realtimeStamp = formatRealtimeTimestamp(state.realtimeSummary?.latest_ingested_at);
      const activeAlerts = activeAdminAlertCount(score);
      const portfolioTotal = Number(score.total_reviews || 0);
      const hasLiveIngest = Boolean(state.realtimeSummary?.latest_ingested_at);
      const pipelineStatus = hasLiveIngest && realtimeCount > 0
        ? "Live"
        : state.latestSource !== "No endpoint call yet"
          ? "Synced"
          : "Standby";
      const extremes = getScoreExtremes();
      const currentTrend = Array.isArray(state.trends) && state.trends.length ? state.trends[state.trends.length - 1] : null;
      const previousTrend = Array.isArray(state.trends) && state.trends.length > 1 ? state.trends[state.trends.length - 2] : null;
      const negativeDelta = currentTrend && previousTrend
        ? Number(currentTrend.Negative || 0) - Number(previousTrend.Negative || 0)
        : 0;
      const overviewModel = dashboardOverviewModel(score, {
        risk,
        realtimeCount,
        realtimeStamp,
        activeAlerts,
        pipelineStatus,
        hasLiveIngest,
        hasSynced: state.latestSource !== "No endpoint call yet",
        leader: extremes.leader,
        lagger: extremes.lagger,
        negativeDelta
      });

      const roleLabel = $("#dashboardRoleLabel");
      const roleMeta = $("#dashboardRoleMeta");
      const sourceBadge = $("#dashboardSourceBadge");
      const sourceMeta = $("#dashboardSourceMeta");
      const liveBadge = $("#dashboardLiveBadge");
      const liveMeta = $("#dashboardLiveMeta");
      const riskPill = $("#dashboardRiskPill");
      const riskLabel = $("#dashboardRiskLabel");
      const riskBadge = $("#dashboardRiskBadge");
      const riskMetaCopy = $("#dashboardRiskMeta");
      const quickRisk = $("#dashboardQuickRisk");
      const quickRiskMeta = $("#dashboardQuickRiskMeta");
      const quickTotalReviews = $("#dashboardQuickTotalReviews");
      const quickTotalReviewsMeta = $("#dashboardQuickTotalReviewsMeta");
      const quickPipeline = $("#dashboardQuickPipeline");
      const quickPipelineMeta = $("#dashboardQuickPipelineMeta");
      const quickAlerts = $("#dashboardQuickAlerts");
      const quickAlertsMeta = $("#dashboardQuickAlertsMeta");
      const modeLabel = $("#dashboardModeLabel");
      const sourceText = $("#dashboardSource");
      const liveUpdate = $("#dashboardLiveUpdate");
      const riskChip = $("#dashboardRiskChip");
      const narrativeLabel = $("#dashboardNarrativeLabel");
      const narrativeTitle = $("#dashboardNarrative");
      const narrativeCopy = $("#dashboardNarrativeCopy");
      const quickRiskLabel = $("#dashboardQuickRiskLabel");
      const quickTotalReviewsLabel = $("#dashboardQuickTotalReviewsLabel");
      const quickPipelineLabel = $("#dashboardQuickPipelineLabel");
      const quickAlertsLabel = $("#dashboardQuickAlertsLabel");
      const supportedLanguageCount = SUPPORTED_LANGUAGE_LABELS.length;
      const supportedLanguageSummary = SUPPORTED_LANGUAGE_LABELS.join(", ");
      const quickStats = Array.isArray(overviewModel.quickStats) ? overviewModel.quickStats : [];
      const statusPill = dashboardStatusPillModel({
        realtimeCount,
        realtimeStamp,
        activeAlerts,
        pipelineStatus,
        hasLiveIngest,
        hasSynced: state.latestSource !== "No endpoint call yet",
        leader: extremes.leader
      });

      if (roleLabel) roleLabel.textContent = roleContent.label;
      if (roleMeta) roleMeta.textContent = roleContent.meta;
      if (sourceBadge) sourceBadge.textContent = supportedLanguageCount + " Languages";
      if (sourceMeta) sourceMeta.textContent = supportedLanguageSummary + ".";
      if (liveBadge) liveBadge.textContent = realtimeCount.toLocaleString() + (realtimeCount === 1 ? " review" : " reviews");
      if (liveMeta) {
        liveMeta.textContent = realtimeCount
          ? (hasLiveIngest
            ? "Live review buffer is active for the current snapshot."
            : "Live review buffer is active.")
          : state.latestSource !== "No endpoint call yet"
            ? "Synced. Waiting for new live reviews."
            : "No live activity yet.";
      }
      if (riskPill) riskPill.className = dashboardStatusPillClassName(statusPill.tone);
      if (riskLabel) riskLabel.textContent = statusPill.label;
      if (riskBadge) riskBadge.textContent = statusPill.value;
      if (riskMetaCopy) riskMetaCopy.textContent = statusPill.meta;
      if (narrativeLabel) narrativeLabel.textContent = overviewModel.narrativeLabel;
      if (narrativeTitle) narrativeTitle.textContent = overviewModel.narrativeTitle;
      if (narrativeCopy) narrativeCopy.textContent = overviewModel.narrativeCopy;
      if (quickRiskLabel) quickRiskLabel.textContent = quickStats[0]?.label || "Risk";
      if (quickRisk) quickRisk.textContent = String(quickStats[0]?.value || "Standby");
      if (quickRiskMeta) quickRiskMeta.textContent = quickStats[0]?.meta || "";
      if (quickTotalReviewsLabel) quickTotalReviewsLabel.textContent = quickStats[1]?.label || "Total Reviews";
      if (quickTotalReviews) quickTotalReviews.textContent = String(quickStats[1]?.value || portfolioTotal.toLocaleString());
      if (quickTotalReviewsMeta) quickTotalReviewsMeta.textContent = quickStats[1]?.meta || "";
      if (quickPipelineLabel) quickPipelineLabel.textContent = quickStats[2]?.label || "Pipeline";
      if (quickPipeline) quickPipeline.textContent = String(quickStats[2]?.value || pipelineStatus);
      if (quickPipelineMeta) quickPipelineMeta.textContent = quickStats[2]?.meta || "";
      if (quickAlertsLabel) quickAlertsLabel.textContent = quickStats[3]?.label || "Alerts";
      if (quickAlerts) quickAlerts.textContent = String(quickStats[3]?.value || "Clear");
      if (quickAlertsMeta) quickAlertsMeta.textContent = quickStats[3]?.meta || "";
      if (modeLabel) modeLabel.textContent = roleContent.mode;
      if (sourceText) sourceText.textContent = dashboardSourceLabel(state.latestSource);
      if (liveUpdate) liveUpdate.textContent = realtimeStamp;
      if (riskChip) {
        riskChip.textContent = risk.label;
        riskChip.className = "score-chip " + risk.className;
      }
      return overviewModel;
    }

    function renderDashboardRealtimeReviews() {
      const eyebrow = $("#dashboardActivityEyebrow");
      const title = $("#dashboardActivityTitle");
      const host = $("#dashboardRealtimeReviewList");
      if (!host) return;
      const role = normalizeAccessRole(state.userRole);
      const sourceMode = String(state.latestRealtimeReviewsMode || "").trim().toLowerCase() || "empty";
      const usingDatasetFallback = sourceMode === "dataset";
      const activityContent = role === "marketing_staff"
        ? {
          eyebrow: "Market Activity",
          liveTitle: "Latest brand mentions",
          syncedTitle: "Latest synced mentions",
          liveEmpty: "Brand mentions will appear here after the first live ingest.",
          syncedEmpty: "Recent synced brand mentions will appear here after analytics data loads.",
          liveIdentity: "Live brand mention stream",
          syncedIdentity: "Synced market review"
        }
        : role === "admin"
          ? {
            eyebrow: "Recent Activity",
            liveTitle: "Latest live reviews",
            syncedTitle: "Latest synced reviews",
            liveEmpty: "Realtime reviews will appear here after the first live ingest.",
            syncedEmpty: "Recent synced reviews will appear here after analytics data loads.",
            liveIdentity: "Realtime review stream",
            syncedIdentity: "Synced dataset review"
          }
          : {
            eyebrow: "Evidence Feed",
            liveTitle: "Latest review evidence",
            syncedTitle: "Latest synced evidence",
            liveEmpty: "Review evidence will appear here after the first live ingest.",
            syncedEmpty: "Recent synced review evidence will appear here after analytics data loads.",
            liveIdentity: "Live evidence stream",
            syncedIdentity: "Synced evidence review"
          };
      if (eyebrow) eyebrow.textContent = activityContent.eyebrow;
      if (title) title.textContent = usingDatasetFallback ? activityContent.syncedTitle : activityContent.liveTitle;
      const rows = Array.isArray(state.latestRealtimeReviews) ? state.latestRealtimeReviews : [];
      if (!rows.length) {
        host.innerHTML = usingDatasetFallback
          ? '<div class="mini-note">' + escapeHtml(activityContent.syncedEmpty) + "</div>"
          : '<div class="mini-note">' + escapeHtml(activityContent.liveEmpty) + "</div>";
        return;
      }

      const languageLabelForRow = (row) => {
        const rowMode = String(row.activity_mode || sourceMode || "").trim().toLowerCase();
        if (rowMode === "dataset") {
          const reviewDate = String(row.review_date || row.activity_label || "").trim();
          return reviewDate && reviewDate.toLowerCase() !== "unknown" ? "Review date: " + reviewDate : "Synced dataset review";
        }
        const label = String(row.source_language_label || row.source_language || "").trim();
        if (!label || label.toLowerCase() === "unknown") return "Language not detected";
        return "Language: " + label;
      };

      const activityStampForRow = (row) => {
        const rowMode = String(row.activity_mode || sourceMode || "").trim().toLowerCase();
        if (rowMode === "dataset") {
          const label = String(row.activity_label || row.review_date || "").trim();
          return label || "Synced review";
        }
        return formatRealtimeTimestamp(row.ingested_at || row.activity_at);
      };

      host.innerHTML = rows.map((row) => {
        const rowMode = String(row.activity_mode || sourceMode || "").trim().toLowerCase();
        const sentiment = String(row.predicted_sentiment || "Unknown");
        const reviewText = String(row.review_text || row.normalized_review || "").trim() || "No review text available.";
        const preview = reviewText.length > 140 ? reviewText.slice(0, 137) + "..." : reviewText;
        const normalized = String(row.normalized_review || "").trim();
        const languageLabel = languageLabelForRow(row);
        const timeLabel = activityStampForRow(row);
        const translationApplied = row.translation_applied === true || String(row.translation_applied).toLowerCase() === "true";
        const hasNormalizedDetail = translationApplied && normalized && normalized.toLowerCase() !== reviewText.toLowerCase();
        const hasFullReviewDetail = reviewText.length > 140;
        const detailLabel = hasNormalizedDetail
          ? (hasFullReviewDetail ? "View review details" : "View normalized text")
          : (hasFullReviewDetail ? "View full review" : "View details");
        const ratingValue = row.rating === null || row.rating === undefined || String(row.rating).trim() === ""
          ? ""
          : "Rating " + escapeHtml(row.rating);
        const confidenceValue = Number(row.prediction_confidence);
        const confidenceLabel = Number.isFinite(confidenceValue) && confidenceValue > 0
          ? "Confidence " + (confidenceValue * 100).toFixed(1) + "%"
          : "";
        const sourceTypeLabel = String(row.source_type || "").trim()
          ? "Source " + escapeHtml(String(row.source_type).replace(/^connector:/, "").replace(/_/g, " "))
          : "";
        const reviewIdLabel = String(row.review_id || "").trim() ? "ID " + escapeHtml(row.review_id) : "";
        const strategyLabel = hasNormalizedDetail && String(row.multilingual_strategy || "").trim()
          ? "Mode " + escapeHtml(row.multilingual_strategy)
          : "";
        const brandLabel = String(row.brand || row.platform || "Unknown brand").trim() || "Unknown brand";
        const platformLabel = String(row.platform || row.brand || "Unknown platform").trim() || "Unknown platform";
        const ratingSummary = row.rating === null || row.rating === undefined || String(row.rating).trim() === ""
          ? "Not rated"
          : String(row.rating).trim() + "/5";
        const metaCards = [
          reviewMetaCard("Brand", brandLabel),
          reviewMetaCard("Platform", platformLabel),
          reviewMetaCard(rowMode === "dataset" ? "Review Date" : "Updated", timeLabel || "Unknown"),
          reviewMetaCard("Rating", ratingSummary)
        ];
        const detailPills = [ratingValue, confidenceLabel, sourceTypeLabel, reviewIdLabel, strategyLabel]
          .concat(languageLabel ? [escapeHtml(languageLabel)] : [])
          .filter(Boolean)
          .map((value) => "<span>" + value + "</span>")
          .join("");
        const detailSections = [];

        if (detailPills) {
          detailSections.push('<div class="review-drilldown-pillrow">' + detailPills + "</div>");
        }
        if (hasFullReviewDetail) {
          detailSections.push('<p class="review-drilldown-text">' + escapeHtml(reviewText) + "</p>");
        }
        if (hasNormalizedDetail) {
          detailSections.push('<p class="review-drilldown-text"><strong>Normalized:</strong> ' + escapeHtml(normalized) + "</p>");
        }
        if (!detailSections.length) {
          detailSections.push('<p class="review-drilldown-text">This live record is short, so the preview already shows the full review. Use this panel for record metadata.</p>');
        }

        return buildReviewDrilldownItem({
          sentiment,
          brand: brandLabel,
          platform: platformLabel,
          identitySubtitle: rowMode === "dataset" ? activityContent.syncedIdentity : activityContent.liveIdentity,
          sideLabel: languageLabel,
          modeBadge: rowMode === "dataset" ? "Synced" : "Live",
          detailLabel,
          metaCards,
          preview,
          detailSections
        });
      }).join("");
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
      copy.textContent = "Current review intelligence score is " + reputation.toFixed(1) + ". Use trend vectors to validate directional movement.";
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

    return {
      activeAdminAlertCount,
      renderDashboardOverview,
      renderDashboardRealtimeReviews,
      renderSignalRadar,
      updateDashboardAlerts
    };
  }

  window.BrandPulseDashboardOverview = { createDashboardOverviewModule };
}());
