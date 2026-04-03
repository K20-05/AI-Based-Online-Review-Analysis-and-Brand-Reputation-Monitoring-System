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
  const selectedBrand = String(state.customerVoiceBrand || "").trim();
  const brands = titleId === "analystCsatTitle"
    ? getCustomerVoiceBrands()
    : (Array.isArray(state.brands) ? state.brands.slice() : []);
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
    .slice(0, titleId === "analystCsatTitle" && selectedBrand ? 1 : 4);
  title.textContent = "Customer Satisfaction Score";
  host.className = "csat-list";
  host.innerHTML = ranked.map((item) => {
    return [
      '<article class="csat-row">',
      '<div class="csat-main"><span class="csat-brand">' + item.brand + '</span><strong class="csat-score">' + item.csat.toFixed(0) + '/100</strong></div>',
      '<div class="csat-meta"><span class="csat-tag">CSAT</span><span class="csat-positive">Positive ' + Number(item.positive_pct || 0).toFixed(1) + '%</span></div>',
      "</article>"
    ].join("");
  }).join("");
  note.textContent = titleId === "analystCsatTitle"
    ? (selectedBrand
      ? "Showing the CSAT proxy for " + selectedBrand + " from the current sentiment snapshot."
      : "Satisfaction proxy based on sentiment mix.")
    : "CSAT is calculated as Positive % + 0.5 x Neutral %, shown as a 100-point satisfaction proxy.";
}

function customerVoiceScopeKey(brand = state.customerVoiceBrand, windowValue = state.customerVoiceWindow) {
  return [
    String(brand || "").trim().toLowerCase(),
    String(windowValue || "all").trim().toLowerCase() || "all"
  ].join("|");
}

function syncCustomerVoiceSelectionState() {
  const brandSelect = $("#customerVoiceBrandSelect");
  const windowSelect = $("#customerVoiceWindowSelect");
  const validBrands = new Set(
    (Array.isArray(state.brands) ? state.brands : [])
      .map((item) => String(item?.brand || "").trim())
      .filter(Boolean)
  );

  let nextBrand = String((brandSelect ? brandSelect.value : state.customerVoiceBrand) || state.customerVoiceBrand || "").trim();
  if (nextBrand && validBrands.size && !validBrands.has(nextBrand)) nextBrand = "";
  if (brandSelect && brandSelect.value !== nextBrand) brandSelect.value = nextBrand;
  state.customerVoiceBrand = nextBrand;

  let nextWindow = String((windowSelect ? windowSelect.value : state.customerVoiceWindow) || state.customerVoiceWindow || "all").trim() || "all";
  const hasWindowOption = !windowSelect || Array.from(windowSelect.options || []).some((option) => option.value === nextWindow);
  if (!hasWindowOption) nextWindow = "all";
  if (windowSelect && windowSelect.value !== nextWindow) windowSelect.value = nextWindow;
  state.customerVoiceWindow = nextWindow;

  return customerVoiceScopeKey(nextBrand, nextWindow);
}

function renderAnalystCustomerVoice() {
  syncCustomerVoiceSelectionState();
  renderCsatList("analystCsatTitle", "analystCsatList", "analystCsatNote");
  renderComplaintTopics("analystComplaintTopicsList", "analystComplaintTopicsNote");
  renderCustomerVoiceInsight();
}

function canLoadCustomerVoiceKeywords() {
  return Boolean(
    state.isAuthenticated
    && allowedViewsForRole(state.userRole).includes("customer-intelligence")
  );
}

function extractKeywordRows(payload) {
  if (Array.isArray(payload)) return payload;
  if (payload && Array.isArray(payload.keywords)) return payload.keywords;
  return [];
}

async function fetchKeywordRows(params, timeoutMs = 65000) {
  const payload = await callApi("/dashboard/keywords?" + params.toString(), { timeoutMs });
  return extractKeywordRows(payload);
}

async function refreshCustomerVoiceKeywords() {
  const scopeKey = syncCustomerVoiceSelectionState();
  if (!canLoadCustomerVoiceKeywords()) {
    state.customerVoiceKeywordsLoading = false;
    state.customerVoiceKeywords = [];
    state.customerVoiceKeywordsError = "";
    state.customerVoiceKeywordsFallback = false;
    state.customerVoiceLastScopeKey = "";
    return;
  }
  const host = $("#analystComplaintTopicsList");
  const note = $("#analystComplaintTopicsNote");
  const requestSeq = ++state.customerVoiceRequestSeq;
  const previousKeywords = Array.isArray(state.customerVoiceKeywords) ? state.customerVoiceKeywords.slice() : [];
  const cacheKey = scopeKey + "|negative";
  state.customerVoiceLastScopeKey = scopeKey;
  if (state.customerVoiceKeywordCache && Array.isArray(state.customerVoiceKeywordCache[cacheKey])) {
    state.customerVoiceKeywords = state.customerVoiceKeywordCache[cacheKey].slice();
    state.customerVoiceKeywordsLoading = false;
    state.customerVoiceKeywordsError = "";
    state.customerVoiceKeywordsFallback = false;
    state.customerVoiceLastLoadedScopeKey = scopeKey;
    renderComplaintTopics("analystComplaintTopicsList", "analystComplaintTopicsNote");
    renderCustomerVoiceInsight();
    renderRoleDashboardPanel();
    return;
  }
  state.customerVoiceKeywordsLoading = true;
  if (!previousKeywords.length) state.customerVoiceKeywords = [];
  state.customerVoiceKeywordsError = "";
  state.customerVoiceKeywordsFallback = false;
  if (host) host.innerHTML = '<span>Loading complaint themes</span>';
  if (note) note.textContent = "Updating complaint themes for the current brand and time window.";
  renderCustomerVoiceInsight();

  const params = new URLSearchParams();
  if (state.customerVoiceBrand) params.set("brand", state.customerVoiceBrand);
  params.set("months", state.customerVoiceWindow || "all");
  params.set("sentiment", "Negative");

  try {
    let nextKeywords = await fetchKeywordRows(params);
    if (requestSeq !== state.customerVoiceRequestSeq) return;
    let fallbackUsed = false;
    let fallbackMessage = "";
    if (!nextKeywords.length) {
      const fallbackRequests = [];
      if (state.customerVoiceBrand) {
        const brandAllSentimentParams = new URLSearchParams();
        brandAllSentimentParams.set("brand", state.customerVoiceBrand);
        brandAllSentimentParams.set("months", state.customerVoiceWindow || "all");
        fallbackRequests.push({
          params: brandAllSentimentParams,
          message: "No negative complaint themes were found, so top recurring topics for " + state.customerVoiceBrand + " are shown."
        });
      }
      const portfolioNegativeParams = new URLSearchParams();
      portfolioNegativeParams.set("months", state.customerVoiceWindow || "all");
      portfolioNegativeParams.set("sentiment", "Negative");
      fallbackRequests.push({
        params: portfolioNegativeParams,
        message: "No brand-specific complaint themes were returned, so overall complaint topics are shown."
      });
      const portfolioAllSentimentParams = new URLSearchParams();
      portfolioAllSentimentParams.set("months", state.customerVoiceWindow || "all");
      fallbackRequests.push({
        params: portfolioAllSentimentParams,
        message: "No brand-specific complaint themes were returned, so overall recurring topics are shown."
      });

      for (const fallbackRequest of fallbackRequests) {
        const fallbackKeywords = await fetchKeywordRows(fallbackRequest.params);
        if (requestSeq !== state.customerVoiceRequestSeq) return;
        if (fallbackKeywords.length) {
          nextKeywords = fallbackKeywords;
          fallbackUsed = true;
          fallbackMessage = fallbackRequest.message;
          break;
        }
      }
    }
    state.customerVoiceKeywords = nextKeywords;
    state.customerVoiceKeywordsFallback = fallbackUsed;
    state.customerVoiceKeywordsError = fallbackUsed
      ? fallbackMessage
      : "";
    state.customerVoiceLastLoadedScopeKey = scopeKey;
    if (nextKeywords.length && !fallbackUsed) {
      state.customerVoiceKeywordCache[cacheKey] = nextKeywords.slice();
    }
  } catch (error) {
    if (requestSeq !== state.customerVoiceRequestSeq) return;
    if (handleAuthError(error)) {
      state.customerVoiceKeywords = [];
      state.customerVoiceKeywordsFallback = false;
      state.customerVoiceKeywordsError = "Sign in again to load complaint themes.";
      return;
    }
    state.customerVoiceKeywords = previousKeywords;
    state.customerVoiceKeywordsFallback = Boolean(previousKeywords.length);
    state.customerVoiceKeywordsError = error.message || "Unable to load complaint themes for the current selection.";
    if (!previousKeywords.length && host) host.innerHTML = '<span>Complaint themes unavailable</span>';
    if (note) {
      note.textContent = previousKeywords.length
        ? "Showing the last available complaint themes while the latest request failed."
        : state.customerVoiceKeywordsError;
    }
  } finally {
    if (requestSeq !== state.customerVoiceRequestSeq) return;
    state.customerVoiceKeywordsLoading = false;
    renderComplaintTopics("analystComplaintTopicsList", "analystComplaintTopicsNote");
    renderCustomerVoiceInsight();
    renderRoleDashboardPanel();
  }
}

function requestCustomerVoiceKeywordsRefresh() {
  if (!canLoadCustomerVoiceKeywords()) return;
  const scopeKey = syncCustomerVoiceSelectionState();
  if (state.customerVoiceKeywordsLoading) return;
  if (
    state.customerVoiceLastLoadedScopeKey === scopeKey
    && Array.isArray(state.customerVoiceKeywords)
    && state.customerVoiceKeywords.length
    && !state.customerVoiceKeywordsFallback
  ) {
    return;
  }
  refreshCustomerVoiceKeywords().catch(() => {});
}

function customerVoiceWindowLabel() {
  syncCustomerVoiceSelectionState();
  const select = $("#customerVoiceWindowSelect");
  return (select && select.selectedOptions && select.selectedOptions[0] ? String(select.selectedOptions[0].textContent || "").trim() : "All months") || "All months";
}

function getCustomerVoiceBrands() {
  syncCustomerVoiceSelectionState();
  const selectedBrand = String(state.customerVoiceBrand || "").trim();
  const brands = Array.isArray(state.brands) ? state.brands.slice() : [];
  if (!selectedBrand) return brands;
  return brands.filter((item) => String(item.brand || "").trim() === selectedBrand);
}

function populateCustomerVoiceBrandSelect(brands) {
  const select = $("#customerVoiceBrandSelect");
  if (!select) return;
  syncCustomerVoiceSelectionState();
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
  if (state.customerVoiceBrand !== previous) {
    state.customerVoiceRequestSeq += 1;
    state.customerVoiceKeywords = [];
    state.customerVoiceKeywordsLoading = false;
    state.customerVoiceKeywordsError = "";
    state.customerVoiceKeywordsFallback = false;
    state.customerVoiceLastLoadedScopeKey = "";
  }
}

function renderCustomerVoiceInsight() {
  syncCustomerVoiceSelectionState();
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
  findingCopy.textContent = selectedBrand
    ? focus.brand + " currently shows " + Number(focus.negative_pct || 0).toFixed(1) + "% negative share and a CSAT proxy of " + calculateCsat(focus).toFixed(0) + "/100. Complaint themes are filtered for " + windowLabel.toLowerCase() + "."
    : focus.brand + " is currently carrying " + Number(focus.negative_pct || 0).toFixed(1) + "% negative share, while CSAT stands at " + calculateCsat(focus).toFixed(0) + "/100. Complaint themes are filtered for " + windowLabel.toLowerCase() + ".";
  actionTitle.textContent = "Recommended Action";
  actionCopy.textContent = selectedBrand
    ? "Investigate " + topTopic + " first for " + selectedBrand + " and address the main friction point before the next reporting cycle."
    : "Investigate " + topTopic + " first and review low-CSAT brands before the next reporting cycle.";
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
