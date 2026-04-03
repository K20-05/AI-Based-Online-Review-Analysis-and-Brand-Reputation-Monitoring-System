(function () {
  function createBrandWorkspaceModule(deps) {
    const {
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
    } = deps;

    function normalizedBrands(brands) {
      return (Array.isArray(brands) ? brands : [])
        .map((item) => normalizeBrandRow(item))
        .filter((item) => String(item.brand || "").trim());
    }

    function riskChipClass(risk) {
      if (risk && risk.level) return "risk-" + risk.level;
      if (risk && risk.className) return risk.className;
      return "risk-medium";
    }

    function canAccessBrandWorkspace(role = state.userRole) {
      const resolved = normalizeAccessRole(role);
      return resolved === "admin" || resolved === "marketing_staff";
    }

    function renderBrandQuickList(brands) {
      const host = $("#brandQuickList");
      const eyebrow = $("#dashboardBrandEyebrow");
      const title = $("#dashboardBrandTitle");
      const note = $("#dashboardBrandNote");
      if (!host) return;

      const role = normalizeAccessRole(state.userRole);
      const brandRows = normalizedBrands(brands);
      if (!brandRows.length) {
        if (eyebrow) eyebrow.textContent = role === "admin" ? "Portfolio Directory" : "Portfolio Leaderboard";
        if (title) title.textContent = role === "admin" ? "Available brands" : "Top brand reputation performers";
        const emptyCopy = role === "admin"
          ? "Brand directory will appear after analytics data loads."
          : "Portfolio leaderboard will appear after analytics data loads.";
        if (note) note.textContent = emptyCopy;
        host.innerHTML = '<div class="mini-note">' + emptyCopy + "</div>";
        return;
      }

      if (role === "admin") {
        if (eyebrow) eyebrow.textContent = "Portfolio Directory";
        if (title) title.textContent = "Available brands";
        if (note) note.textContent = "Open any brand to inspect details.";
        host.innerHTML = brandRows
          .slice()
          .sort((a, b) => String(a.brand || "").localeCompare(String(b.brand || "")))
          .map((brand) => {
            const safeBrand = escapeHtml(brand.brand);
            return '<button class="brand-quick-btn" type="button" data-brand="' + safeBrand + '"><span>' + safeBrand + "</span></button>";
          })
          .join("");
        return;
      }

      if (eyebrow) eyebrow.textContent = "Portfolio Leaderboard";
      if (title) title.textContent = "Top brand reputation performers";
      if (note) note.textContent = "Current top-ranked brands.";
      host.innerHTML = brandRows
        .slice()
        .sort((a, b) => Number(b.brand_reputation_score || 0) - Number(a.brand_reputation_score || 0))
        .slice(0, 6)
        .map((brand) => {
          const safeBrand = escapeHtml(brand.brand);
          return '<button class="brand-quick-btn" type="button" data-brand="' + safeBrand + '"><span>' + safeBrand + '</span><b>' + Number(brand.brand_reputation_score || 0).toFixed(1) + "</b></button>";
        })
        .join("");
    }

    function renderBrandSideLists(brands) {
      const hosts = [$("#brandInsightQuickList"), $("#brandCompareQuickList")].filter(Boolean);
      if (!hosts.length) return;

      const brandNames = normalizedBrands(brands)
        .map((item) => String(item.brand || "").trim())
        .filter(Boolean)
        .sort((a, b) => a.localeCompare(b));

      if (!brandNames.length) {
        hosts.forEach((host) => {
          host.innerHTML = '<div class="mini-note">Brand list will appear after analytics data loads.</div>';
        });
        return;
      }

      const markup = brandNames.map((brand) => {
        const safeBrand = escapeHtml(brand);
        return '<button class="brand-quick-btn" type="button" data-brand="' + safeBrand + '">' + safeBrand + "</button>";
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
        host.innerHTML = "<span>No watched brands yet</span>";
        note.textContent = "Use this watchlist to keep high-priority brands one click away.";
        return;
      }

      host.innerHTML = watchlist.map((brand) => {
        const safeBrand = escapeHtml(brand);
        return '<button class="ghost-btn" type="button" data-watch-brand="' + safeBrand + '">' + safeBrand + "</button>";
      }).join("");
      note.textContent = "Watchlist active for " + watchlist.length + " brand" + (watchlist.length === 1 ? "" : "s") + ".";
    }

    function saveWatchlist(nextWatchlist) {
      state.watchlist = Array.from(
        new Set((nextWatchlist || []).map((item) => String(item || "").trim()).filter(Boolean))
      ).slice(0, 8);
      scopedStorageWrite(WATCHLIST_KEY, state.watchlist);
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

    function selectInsightBrand(brand, options = {}) {
      const select = $("#brandInsightSelect");
      if (!select || !brand) return;
      select.value = brand;
      if (options.openView) viewRouter("brand-insights");
      renderBrandInsights();
      if (options.toastMessage) toast(options.toastMessage, options.toastType || "success");
    }

    function handleWatchlistPick(event) {
      const button = event.target.closest("button[data-watch-brand]");
      if (!button) return;
      const brand = button.dataset.watchBrand || "";
      if (!brand) return;
      selectInsightBrand(brand, { toastMessage: "Loaded watchlist brand " + brand + "." });
    }

    function handleBrandQuickPick(event) {
      const button = event.target.closest("button[data-brand]");
      if (!button) return;
      const brand = button.dataset.brand || "";
      if (!brand) return;
      selectInsightBrand(brand, {
        openView: true,
        toastMessage: "Showing insights for " + brand + "."
      });
    }

    function handleInsightQuickPick(event) {
      const button = event.target.closest("button[data-brand]");
      if (!button) return;
      const brand = button.dataset.brand || "";
      if (!brand) return;
      selectInsightBrand(brand, { toastMessage: "Loaded brand insight for " + brand + "." });
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

    function populateTrendBrandSelect(brands) {
      const select = $("#trendBrandSelect");
      if (!select) return;

      const brandRows = normalizedBrands(brands);
      const trendReadyBrands = brandRows.filter((item) => item.has_trend_data !== false);
      const sourceBrands = trendReadyBrands.length ? trendReadyBrands : brandRows;
      const previous = state.trendBrand || select.value || "";
      const options = sourceBrands.map((item) => {
        const safeBrand = escapeHtml(item.brand);
        return '<option value="' + safeBrand + '">' + safeBrand + "</option>";
      }).join("");

      select.innerHTML = '<option value="">All brands</option>' + options;
      const available = new Set(sourceBrands.map((item) => item.brand));
      const next = available.has(previous) ? previous : "";
      select.value = next;
      state.trendBrand = next;
    }

    function renderBrandSelectors(brands) {
      const insightSelect = $("#brandInsightSelect");
      const compareASelect = $("#compareBrandA");
      const compareBSelect = $("#compareBrandB");
      if (!insightSelect || !compareASelect || !compareBSelect) return;

      const sorted = normalizedBrands(brands)
        .slice()
        .sort((a, b) => Number(b.brand_reputation_score || 0) - Number(a.brand_reputation_score || 0));

      const previousInsight = insightSelect.value;
      const previousCompareA = compareASelect.value;
      const previousCompareB = compareBSelect.value;

      const brandOptions = sorted.map((item) => {
        const safeBrand = escapeHtml(item.brand);
        return '<option value="' + safeBrand + '">' + safeBrand + "</option>";
      }).join("");

      insightSelect.innerHTML = '<option value="">Select a brand</option>' + brandOptions;
      compareASelect.innerHTML = '<option value="">Select brand A</option>' + brandOptions;
      compareBSelect.innerHTML = '<option value="">Select brand B</option>' + brandOptions;

      const available = new Set(sorted.map((item) => item.brand));
      insightSelect.value = available.has(previousInsight) ? previousInsight : "";
      compareASelect.value = available.has(previousCompareA) ? previousCompareA : "";
      compareBSelect.value = available.has(previousCompareB) ? previousCompareB : "";
      populateTrendBrandSelect(sorted);
      populateCustomerVoiceBrandSelect(sorted);
    }

    function getBrandByName(name) {
      return normalizedBrands(state.brands).find((item) => item.brand === name) || null;
    }

    function renderSimilarBrands(items) {
      const host = $("#similarBrandList");
      if (!host) return;

      if (!Array.isArray(items) || !items.length) {
        host.innerHTML = '<div class="mini-note">No similar brands available.</div>';
        return;
      }

      host.innerHTML = items.map((item) => {
        const metrics = normalizeBrandRow(item.metrics || item);
        const risk = item.risk || riskMeta(metrics.brand_reputation_score, metrics.negative_pct);
        const brandLabel = escapeHtml(String(item.brand || metrics.brand || "Unknown"));
        const riskLabel = escapeHtml(String(risk.label || "Medium Risk"));
        return [
          '<div class="similar-item">',
          '<div><strong>' + brandLabel + '</strong><span>Score ' + Number(metrics.brand_reputation_score || 0).toFixed(1) + " | Positive " + Number(metrics.positive_pct || 0).toFixed(1) + '%</span></div>',
          '<span class="score-chip ' + riskChipClass(risk) + '">' + riskLabel + "</span>",
          "</div>"
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
      if (!canAccessBrandWorkspace()) {
        clearBrandInsights("Brand intelligence is available in the marketing workspace.");
        return;
      }
      const select = $("#brandInsightSelect");
      const selectedBrand = select ? select.value : "";
      const row = getBrandByName(selectedBrand);
      const requestSeq = ++state.insightRequestSeq;

      if (!row) {
        clearBrandInsights(
          Array.isArray(state.brands) && state.brands.length
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
        $("#insightRiskChip").className = "score-chip " + riskChipClass(risk);
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
        $("#insightRiskChip").className = "score-chip " + riskChipClass(risk);
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

    function applyComparisonState(left, right, summary) {
      $("#compareScoreA").style.width = clamp(left.brand_reputation_score, 0, 100) + "%";
      $("#compareScoreB").style.width = clamp(right.brand_reputation_score, 0, 100) + "%";
      $("#comparePositiveA").style.width = clamp(left.positive_pct, 0, 100) + "%";
      $("#comparePositiveB").style.width = clamp(right.positive_pct, 0, 100) + "%";
      $("#compareNegativeA").style.width = clamp(left.negative_pct, 0, 100) + "%";
      $("#compareNegativeB").style.width = clamp(right.negative_pct, 0, 100) + "%";
      $("#compareScoreText").textContent = left.brand_reputation_score.toFixed(1) + " vs " + right.brand_reputation_score.toFixed(1);
      $("#comparePositiveText").textContent = left.positive_pct.toFixed(1) + "% vs " + right.positive_pct.toFixed(1) + "%";
      $("#compareNegativeText").textContent = left.negative_pct.toFixed(1) + "% vs " + right.negative_pct.toFixed(1) + "%";
      $("#compareSummary").textContent = summary;
    }

    async function renderBrandComparison() {
      if (!canAccessBrandWorkspace()) {
        clearBrandComparison("Brand comparison is available in the marketing workspace.");
        return;
      }
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
        applyComparisonState(left, right, payload.summary || "Comparison loaded.");
        return;
      } catch (error) {
        if (requestSeq !== state.compareRequestSeq) return;
        if (handleAuthError(error)) return;
      }

      const leader = brandA.brand_reputation_score >= brandB.brand_reputation_score ? brandA : brandB;
      const lagger = leader.brand === brandA.brand ? brandB : brandA;
      applyComparisonState(
        brandA,
        brandB,
        leader.brand + " leads on brand reputation score, while " + lagger.brand + " needs more work on negative sentiment control and trust recovery."
      );
    }

    function renderDashboardAnalyticsState() {
      const canOpenBrandWorkspace = canAccessBrandWorkspace();
      renderKeywords(state.keywordGroups);
      renderBrandSelectors(state.brands);
      renderBrandQuickList(state.brands);
      renderBrandSideLists(state.brands);
      renderBrandWatchlist();
      if (canOpenBrandWorkspace) {
        renderBrandInsights();
        renderBrandComparison();
      } else {
        clearBrandInsights("Brand intelligence is available in the marketing workspace.");
        clearBrandComparison("Brand comparison is available in the marketing workspace.");
      }
      renderAnalystCustomerVoice();
      renderAnalystFocusPanel();
      renderSmartInsight();
      renderAnalyticsSummaryContext();
      renderRoleDashboardPanel();
    }

    return {
      renderBrandComparison,
      renderBrandInsights,
      renderDashboardAnalyticsState,
      addSelectedBrandToWatchlist,
      clearBrandWatchlist,
      handleWatchlistPick,
      handleBrandQuickPick,
      handleInsightQuickPick,
      handleCompareQuickPick
    };
  }

  window.BrandPulseBrandWorkspace = { createBrandWorkspaceModule };
}());
