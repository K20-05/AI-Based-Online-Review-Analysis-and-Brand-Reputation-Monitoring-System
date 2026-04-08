(function () {
  function createDashboardFragmentHelpers(deps) {
    const { sentimentClass, escapeHtml } = deps;

    function reviewMetaCard(label, value) {
      return [
        '<div class="review-drilldown-meta-card">',
        '<span class="review-drilldown-meta-label">' + escapeHtml(label) + "</span>",
        '<strong class="review-drilldown-meta-value">' + escapeHtml(String(value || "N/A")) + "</strong>",
        "</div>"
      ].join("");
    }

    function reviewIdentitySubtitle(brand, platform, fallbackLabel) {
      const brandValue = String(brand || "").trim();
      const platformValue = String(platform || "").trim();
      if (platformValue && platformValue.toLowerCase() !== brandValue.toLowerCase()) {
        return platformValue;
      }
      return fallbackLabel || "Marketplace review stream";
    }

    function buildReviewDrilldownItem(options = {}) {
      const sentiment = String(options.sentiment || "Unknown").trim() || "Unknown";
      const brand = String(options.brand || "Unknown brand").trim() || "Unknown brand";
      const platform = String(options.platform || "Unknown platform").trim() || "Unknown platform";
      const preview = String(options.preview || "").trim() || "No review text available.";
      const detailSections = Array.isArray(options.detailSections) ? options.detailSections.filter(Boolean) : [];
      const metaCards = Array.isArray(options.metaCards) ? options.metaCards.filter(Boolean) : [];
      const modeBadge = String(options.modeBadge || "").trim();
      const sideLabel = String(options.sideLabel || "").trim();
      const detailLabel = String(options.detailLabel || "Expand").trim();
      const identitySubtitle = reviewIdentitySubtitle(brand, platform, options.identitySubtitle);

      return [
        '<details class="review-drilldown-item" data-tone="' + escapeHtml(sentiment) + '"' + (options.open ? " open" : "") + ">",
        "<summary>",
        '<div class="review-drilldown-topline">',
        '<div class="review-drilldown-topline-group">',
        '<span class="score-chip ' + sentimentClass(sentiment) + '">' + escapeHtml(sentiment) + "</span>",
        modeBadge ? '<span class="review-drilldown-mode">' + escapeHtml(modeBadge) + "</span>" : "",
        "</div>",
        '<span class="review-drilldown-toggle">' + escapeHtml(detailLabel) + "</span>",
        "</div>",
        '<div class="review-drilldown-titlebar">',
        '<div class="review-drilldown-identity">',
        "<strong>" + escapeHtml(brand) + "</strong>",
        "<span>" + escapeHtml(identitySubtitle) + "</span>",
        "</div>",
        sideLabel ? '<span class="review-drilldown-side-note">' + escapeHtml(sideLabel) + "</span>" : "",
        "</div>",
        metaCards.length ? '<div class="review-drilldown-meta-grid">' + metaCards.join("") + "</div>" : "",
        '<div class="review-drilldown-preview"><p>' + escapeHtml(preview) + "</p></div>",
        "</summary>",
        '<div class="review-drilldown-body">' + detailSections.join("") + "</div>",
        "</details>"
      ].join("");
    }

    return {
      reviewMetaCard,
      buildReviewDrilldownItem
    };
  }

  window.BrandPulseDashboardFragments = { createDashboardFragmentHelpers };
}());
