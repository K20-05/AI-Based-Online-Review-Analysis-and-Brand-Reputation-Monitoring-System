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
  const candidates = [
    payload.final_confidence,
    payload.prediction_confidence,
    payload.decision_confidence,
    payload.confidence
  ];
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

function sentimentTagClass(value) {
  const normalized = (value || "").toLowerCase();
  if (normalized === "positive") return "positive";
  if (normalized === "negative") return "negative";
  if (normalized === "neutral") return "neutral";
  return "unknown";
}

function renderSingleAspectResult(payload) {
  const panel = $("#singleAspectPanel");
  const title = $("#singleAspectTitle");
  const summary = $("#singleAspectSummary");
  const primary = $("#singleAspectPrimary");
  const tags = $("#singleAspectTags");
  if (!panel || !title || !summary || !primary || !tags) return;

  const rows = Array.isArray(payload.aspect_sentiments)
    ? payload.aspect_sentiments.filter((item) => String(item?.aspect || "").trim())
    : [];
  const primaryAspect = String(payload.primary_aspect || "").trim();
  const primarySentiment = String(payload.primary_aspect_sentiment || "").trim();
  const aspectSummary = String(payload.aspect_summary || "").trim();

  panel.classList.remove("hidden");
  title.textContent = primaryAspect ? "Primary aspect: " + primaryAspect : "Aspect Analysis";
  summary.textContent = aspectSummary || "No strong aspect signal was detected for this review.";
  primary.className = "tag " + sentimentTagClass(primarySentiment || "neutral");
  primary.textContent = primarySentiment || "No strong aspect";

  if (rows.length) {
    tags.innerHTML = rows.map((row) => {
      const aspect = escapeHtml(String(row.aspect || "Aspect"));
      const sentiment = escapeHtml(String(row.sentiment || "Neutral"));
      return '<span class="tag ' + sentimentTagClass(sentiment) + '">' + aspect + ": " + sentiment + "</span>";
    }).join("");
    return;
  }

  tags.innerHTML = '<span class="tag neutral">No aspect signal detected</span>';
}

function updateSingleResult(payload, submittedRating) {
  const sentiment = extractSentiment(payload);
  const confidence = extractConfidence(payload, sentiment);
  const languageLabel = payload.source_language_label || payload.source_language || "Unknown";
  const translationNote = payload.translation_applied
    ? " Multilingual bridge applied before scoring."
    : "";
  const adjustmentNote = payload.sentiment_adjustment_reason
    ? " Multilingual sentiment guard corrected the raw model output."
    : "";
  state.latestConfidence = confidence;
  state.latestSentiment = sentiment;
  $("#singleResultShell").classList.remove("is-empty");
  $("#singleResultIntro").textContent = "Prediction complete for " + languageLabel + " input." + translationNote + adjustmentNote + " Inspect sentiment, confidence, aspect signals, and any rating mismatch below.";

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

  renderSingleAspectResult(payload);
  $("#singleTechnicalJson").textContent = JSON.stringify(payload, null, 2);
  updateConfidenceSignal(confidence, sentiment);
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
          language: item.source_language_label || item.source_language || "Unknown",
          sentiment,
          confidence
        };
      });
    }
  }

  return submittedLines.slice(0, 10).map((line, index) => ({
    review_id: index + 1,
    language: "Pending",
    sentiment: "Processed",
    confidence: null
  }));
}

function renderBatchTable(rows) {
  const tbody = $("#batchTableBody");
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="signal-note">No batch results available yet.</td></tr>';
    return;
  }

  tbody.innerHTML = rows.map((row) => {
    const confidenceText = Number.isFinite(row.confidence) ? row.confidence.toFixed(1) + "%" : "Unavailable";
    return [
      "<tr>",
      "<td>" + row.review_id + "</td>",
      "<td>" + (row.language || "Unknown") + "</td>",
      '<td><span class="tag ' + sentimentTagClass(row.sentiment) + '">' + row.sentiment + "</span></td>",
      "<td>" + confidenceText + "</td>",
      "</tr>"
    ].join("");
  }).join("");
}

async function handleSingleSubmit(event) {
  event.preventDefault();
  const sessionRevision = state.sessionRevision;
  const shell = $("#singleFormShell");
  const reviewInput = $("#singleReviewText");
  let reviewText = reviewInput.value.trim();
  if (!reviewText) {
    const requestedBrand = String($("#singleBrand").value.trim() || $("#singlePlatform").value.trim() || "").trim();
    if (requestedBrand) {
      try {
        const sample = await loadRandomBrandReview({ showToastMessage: false });
        reviewText = String(sample?.review_text || "").trim();
        if (reviewText) {
          toast("Loaded a random review for prediction.", "info");
        }
      } catch (error) {
        if (handleAuthError(error)) return;
      }
    }
  }
  if (!reviewText) {
    setSingleReviewValidationState("Review text is required before prediction.");
    shake(shell);
    reviewInput.focus();
    toast("Single review text is required.", "error");
    return;
  }
  setSingleReviewValidationState("");

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
    const data = await callApi("/predict", { method: "POST", body: payload, timeoutMs: 30000 });
    if (!sameSessionRevision(sessionRevision)) return;
    updateSingleResult(data, rating);
    storeHistory({
      title: "Single review prediction",
      time: new Date().toLocaleString(),
      summary: (data.source_language_label || data.source_language || "Unknown") + " review scored as " + extractSentiment(data) +
        (Number.isFinite(state.latestConfidence) ? " with " + state.latestConfidence.toFixed(1) + "% confidence." : ".") +
        (data.translation_applied ? " Multilingual normalization applied." : "")
    });
    toast("Single review prediction completed.", "success");
  } catch (error) {
    if (!sameSessionRevision(sessionRevision)) return;
    if (handleAuthError(error)) return;
    const message = error.message || "Request failed";
    $("#singleTechnicalJson").textContent = JSON.stringify({ error: message }, null, 2);
    $("#singleResultShell").classList.remove("is-empty");
    $("#singleResultIntro").textContent = "Prediction failed: " + message;
    $("#singleSentimentBadge").className = "sentiment-badge sentiment-negative";
    $("#singleSentimentBadge").textContent = "Error";
    $("#singleConfidenceBar").style.width = "0%";
    $("#singleConfidenceText").textContent = "Unavailable";
    $("#ratingWarning").classList.remove("is-visible");
    $("#ratingWarning").textContent = "";
    resetSingleAspectResult();
    toast(error.message || "Prediction failed.", "error");
  } finally {
    setButtonLoading(button, false, "Predict Sentiment");
  }
}

async function loadRandomBrandReview(options = {}) {
  const isEvent = Boolean(options && typeof options.preventDefault === "function");
  if (isEvent) {
    options.preventDefault();
    if (typeof options.stopPropagation === "function") options.stopPropagation();
  }
  const config = isEvent ? {} : (options || {});
  const showToastMessage = config.showToastMessage !== false;
  const allowFallback = config.allowFallback !== false;
  const sessionRevision = state.sessionRevision;
  const button = $("#singleRandomReviewButton");
  const brandInput = $("#singleBrand");
  const platformInput = $("#singlePlatform");
  const requestedBrand = String((brandInput?.value || platformInput?.value || "")).trim();
  if (!$("#singleReviewText")) return null;
  if (button) setButtonLoading(button, true, "Load Random Review", "Loading sample...");
  try {
    const query = requestedBrand ? "?brand=" + encodeURIComponent(requestedBrand) : "";
    const payload = await callApi("/dashboard/random-review" + query);
    if (!sameSessionRevision(sessionRevision)) return;
    const sample = fillSingleReviewSample(payload.sample || {});
    if (!sample) throw new Error("No review sample found for the selected brand");
    if (showToastMessage) {
      toast("Loaded a random review" + (sample.brand ? " for " + sample.brand : "") + ".", "success");
    }
    return sample;
  } catch (error) {
    if (!sameSessionRevision(sessionRevision)) return;
    if (handleAuthError(error)) return;
    const fallbackSample = allowFallback ? fallbackRandomReviewSample(requestedBrand) : null;
    if (fallbackSample) {
      const sample = fillSingleReviewSample(fallbackSample);
      if (showToastMessage && sample) {
        toast("Loaded a sample review" + (sample.brand ? " for " + sample.brand : "") + ".", "info");
      }
      return sample;
    }
    if (showToastMessage) {
      toast(error.message || "Unable to load a random review.", "error");
    }
    if (!isEvent) throw error;
    return null;
  } finally {
    if (button) setButtonLoading(button, false, "Load Random Review");
  }
}

async function handleBatchSubmit(event) {
  event.preventDefault();
  const sessionRevision = state.sessionRevision;
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
    const data = await callApi("/predict/batch", { method: "POST", body: payload, timeoutMs: 60000 });
    if (!sameSessionRevision(sessionRevision)) return;
    $("#batchTechnicalJson").textContent = JSON.stringify(data, null, 2);
    const score = normalizeBrandScore(data);
    const results = Array.isArray(data.results) ? data.results : [];
    const confidenceValues = results
      .map((item) => Number(item.prediction_confidence))
      .filter((value) => Number.isFinite(value));
    const averageConfidence = confidenceValues.length
      ? confidenceValues.reduce((sum, value) => sum + value, 0) / confidenceValues.length
      : null;
    if (score.total_reviews || score.brand_reputation_score || data.brand_score) {
      state.brandScore = score;
      updateDashboard(score);
      updateSignalPanel(score);
      refreshDashboardAnalytics();
    }
    renderGauge($("#batchGauge"), Number.isFinite(averageConfidence) ? averageConfidence * 100 : 0, {
      displayValue: Number.isFinite(averageConfidence) ? (averageConfidence * 100).toFixed(1) : "0.0",
      label: "Batch Confidence",
      suffix: "%",
      caption: Number.isFinite(averageConfidence)
        ? "Mean confidence across processed reviews."
        : "Confidence is unavailable for this batch response.",
      color: Number.isFinite(averageConfidence)
        ? averageConfidence >= 0.8
          ? "var(--positive)"
          : averageConfidence >= 0.6
            ? "var(--neutral)"
            : "var(--negative)"
        : "var(--accent)"
    });

    $("#batchProcessedCount").textContent = Number(data.rows || score.total_reviews || lines.length).toLocaleString();
    setBatchSummaryVisibility(true);
    renderBatchTable(buildBatchPreview(data, lines));
    storeHistory({
      title: "Batch run",
      time: new Date().toLocaleString(),
      summary: "Processed " + Number(data.rows || lines.length).toLocaleString() + " reviews with Indian-language detection." +
        (Number.isFinite(averageConfidence) ? " Average confidence: " + (averageConfidence * 100).toFixed(1) + "%." : "")
    });
    toast("Batch prediction completed.", "success");
  } catch (error) {
    if (!sameSessionRevision(sessionRevision)) return;
    if (handleAuthError(error)) return;
    resetBatchResultView();
    $("#batchTechnicalJson").textContent = JSON.stringify({ error: error.message || "Request failed" }, null, 2);
    toast(error.message || "Batch prediction failed.", "error");
  } finally {
    setButtonLoading(button, false, "Run Batch");
  }
}
