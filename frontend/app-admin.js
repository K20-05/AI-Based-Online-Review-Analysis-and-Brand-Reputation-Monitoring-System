function formatAdminTimestamp(value) {
  const parsed = value ? new Date(value) : null;
  if (!parsed || Number.isNaN(parsed.getTime())) return "Waiting";
  return parsed.toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

function renderAdminControlHub() {
  if (normalizeAccessRole(state.userRole) !== "admin") return;
  $("#adminUsersCount").textContent = Number((state.users || []).length || 0).toLocaleString();
  $("#adminBrandsCount").textContent = Number((state.brands || []).length || 0).toLocaleString();
  $("#adminRoleSupportCount").textContent = "3";
  $("#adminModelAccuracy").textContent = state.modelMetrics && Number.isFinite(Number(state.modelMetrics.test_accuracy))
    ? (Number(state.modelMetrics.test_accuracy) * 100).toFixed(1) + "%"
    : "Waiting";
  $("#adminModelName").textContent = state.modelMetrics && state.modelMetrics.model
    ? String(state.modelMetrics.model)
    : "Latest model metrics will appear after admin data loads.";
  $("#adminTrainingTime").textContent = formatAdminTimestamp(state.modelTrainingAt);
  const pipelineReady = Boolean(state.modelMetrics && Number.isFinite(Number(state.modelMetrics.test_accuracy)));
  $("#adminPipelineStatus").textContent = pipelineReady ? "Healthy" : "Pending";
  $("#adminPipelineCopy").textContent = pipelineReady
    ? "Model metrics are available and the admin control pipeline looks healthy."
    : "Model metrics have not been loaded yet. Refresh model status to verify pipeline health.";
}

function renderAdminOps() {
  if (normalizeAccessRole(state.userRole) !== "admin") return;
  const title = $("#adminAlertsTitle");
  const copy = $("#adminAlertsCopy");
  const status = $("#pipelineActionStatus");
  const reviewCount = Number(state.brandScore?.total_reviews || 0);
  const modelAccuracy = Number(state.modelMetrics?.test_accuracy || 0);
  if (title) {
    if (modelAccuracy > 0 && modelAccuracy < 0.8) {
      title.textContent = "Model accuracy warning";
    } else if (Number(state.brandScore?.negative_pct || 0) >= 40) {
      title.textContent = "Complaint spike detected";
    } else {
      title.textContent = "System Status: Stable";
    }
  }
  if (copy) {
    if (modelAccuracy > 0 && modelAccuracy < 0.8) {
      copy.textContent = "Latest model accuracy is below the 80% checkpoint. Review training quality before depending on new outputs.";
    } else if (Number(state.brandScore?.negative_pct || 0) >= 40) {
      copy.textContent = "Negative sentiment is elevated across " + reviewCount.toLocaleString() + " reviews. Keep brand monitoring teams on alert.";
    } else {
      copy.textContent = "Users, model artifacts, and monitored brand coverage are currently in a stable operating range.";
    }
  }
  if (status) {
    status.textContent = state.modelMetrics
      ? "Pipeline status is ready. Last model training: " + formatAdminTimestamp(state.modelTrainingAt) + "."
      : "Model metrics are not available yet. Run preprocessing, features, and training to restore pipeline visibility.";
  }
  buildAdminNotifications();
  renderAdminSidePanel();
}

function buildAdminNotifications() {
  const notifications = [];
  const modelAccuracy = Number(state.modelMetrics?.test_accuracy || 0);
  const validationAccuracy = Number(state.modelMetrics?.validation_accuracy || 0);
  const negativePct = Number(state.brandScore?.negative_pct || 0);
  const reviewCount = Number(state.brandScore?.total_reviews || 0);

  if (!state.modelMetrics) {
    notifications.push({
      title: "Model metrics unavailable",
      level: "info",
      summary: "No model metrics are loaded. Refresh model status or run training to restore visibility."
    });
  } else {
    if (modelAccuracy > 0 && modelAccuracy < 0.8) {
      notifications.push({
        title: "Model accuracy warning",
        level: "warning",
        summary: "Latest test accuracy is " + (modelAccuracy * 100).toFixed(1) + "%. Review training quality before trusting new outputs."
      });
    }
    if (validationAccuracy > 0 && modelAccuracy > 0 && Math.abs(validationAccuracy - modelAccuracy) > 0.08) {
      notifications.push({
        title: "Validation gap detected",
        level: "warning",
        summary: "Validation and test accuracy differ noticeably. Check overfitting or dataset drift."
      });
    }
  }

  if (negativePct >= 40) {
    notifications.push({
      title: "Complaint spike detected",
      level: "critical",
      summary: "Negative sentiment reached " + negativePct.toFixed(1) + "% across " + reviewCount.toLocaleString() + " reviews."
    });
  }

  if (state.usersLoaded && (state.users || []).length <= 1) {
    notifications.push({
      title: "Low user coverage",
      level: "info",
      summary: "Only " + Number((state.users || []).length || 0).toLocaleString() + " account" + ((state.users || []).length === 1 ? " is" : "s are") + " active. Add backup operator access if needed."
    });
  }

  if (!notifications.length) {
    notifications.push({
      title: "System stable",
      level: "success",
      summary: "No critical warnings detected. Users, model metrics, and monitored dataset are in a healthy state."
    });
  }

  state.adminNotifications = notifications;
  renderAdminNotifications();
  updateAdminNotificationBadge();
}

function updateAdminNotificationBadge() {
  const badge = $("#adminNotificationBadge");
  if (!badge) return;
  const activeCount = (state.adminNotifications || []).filter((item) => item.level !== "success").length;
  badge.textContent = String(activeCount);
  badge.classList.toggle("hidden", activeCount <= 0 || normalizeAccessRole(state.userRole) !== "admin");
}

function renderAdminNotifications() {
  const host = $("#adminNotificationsList");
  const headline = $("#notificationsHeadline");
  if (!host || !headline) return;
  const items = Array.isArray(state.adminNotifications) ? state.adminNotifications : [];
  const activeCount = items.filter((item) => item.level !== "success").length;
  headline.textContent = activeCount > 0
    ? activeCount + " active alert" + (activeCount === 1 ? "" : "s")
    : "No active alerts";
  host.innerHTML = items.map((item) => {
    const level = item.level || "info";
    const label = level === "critical"
      ? "Critical"
      : level === "warning"
        ? "Warning"
        : level === "success"
          ? "Stable"
          : "Info";
    const action = level === "critical"
      ? "Immediate review required"
      : level === "warning"
        ? "Review recommended"
        : level === "success"
          ? "No action needed"
          : "Check system state";
    return [
      '<article class="timeline-item admin-alert-card admin-alert-card--' + level + '">',
      '<div class="admin-alert-head">',
      '<span class="score-chip admin-alert-chip admin-alert-chip--' + level + '">' + label + "</span>",
      '<time>' + new Date().toLocaleString() + "</time>",
      "</div>",
      '<strong>' + item.title + "</strong>",
      '<p>' + item.summary + "</p>",
      '<div class="admin-alert-action">Action: ' + action + "</div>",
      "</article>"
    ].join("");
  }).join("");
}

function renderAdminSidePanel() {
  if (normalizeAccessRole(state.userRole) !== "admin") return;
  const alertCount = (state.adminNotifications || []).filter((item) => item.level !== "success").length;
  const userCount = Number((state.users || []).length || 0);
  const brandCount = Number((state.brands || []).length || 0);
  const reviewCount = Number(state.brandScore?.total_reviews || 0);
  const modelAccuracy = Number(state.modelMetrics?.test_accuracy || 0);
  const alertEl = $("#adminSideAlertCount");
  const userEl = $("#adminSideUserCount");
  const brandEl = $("#adminSideBrandCount");
  const copyEl = $("#adminSideSummaryCopy");
  const panelStatus = $("#panelStatusText");
  if (alertEl) alertEl.textContent = alertCount + (alertCount === 1 ? " alert" : " alerts");
  if (userEl) userEl.textContent = userCount.toLocaleString() + (userCount === 1 ? " user" : " users");
  if (brandEl) brandEl.textContent = brandCount.toLocaleString() + (brandCount === 1 ? " brand" : " brands");
  if (copyEl) {
    copyEl.textContent = alertCount > 0
      ? "Operational attention required. Review " + alertCount + " active alert" + (alertCount === 1 ? "" : "s") + ", validate model health, and confirm brand coverage before the next sync."
      : "System monitoring is stable across " + userCount.toLocaleString() + " users, " + brandCount.toLocaleString() + " brands, and " + reviewCount.toLocaleString() + " tracked reviews" + (modelAccuracy > 0 ? " with " + (modelAccuracy * 100).toFixed(1) + "% model accuracy." : ".");
  }
  if (panelStatus) panelStatus.textContent = alertCount > 0 ? "Admin Alerts" : "Admin Stable";
}

function renderAdminModelPerformance() {
  const metrics = state.modelMetrics || {};
  $("#modelPageName").textContent = metrics.model || "Waiting";
  $("#modelPageAccuracy").textContent = Number.isFinite(Number(metrics.test_accuracy))
    ? (Number(metrics.test_accuracy) * 100).toFixed(1) + "%"
    : "0%";
  $("#modelPageF1").textContent = Number.isFinite(Number(metrics.test_f1_macro))
    ? (Number(metrics.test_f1_macro) * 100).toFixed(1) + "%"
    : "0%";
  $("#modelPageValidation").textContent = Number.isFinite(Number(metrics.validation_accuracy))
    ? (Number(metrics.validation_accuracy) * 100).toFixed(1) + "%"
    : "0%";
  $("#modelPageLoss").textContent = Number.isFinite(Number(metrics.test_log_loss))
    ? Number(metrics.test_log_loss).toFixed(3)
    : "0.000";
  $("#modelPageTrainedAt").textContent = formatAdminTimestamp(state.modelTrainingAt);
}

async function loadAdminModelPerformance() {
  if (normalizeAccessRole(state.userRole) !== "admin") return;
  const sessionRevision = state.sessionRevision;
  try {
    const payload = await callApi("/admin/model-performance");
    if (!sameSessionRevision(sessionRevision) || normalizeAccessRole(state.userRole) !== "admin") return;
    state.modelMetrics = payload.metrics || null;
    state.modelTrainingAt = payload.last_training_at || "";
    renderAdminModelPerformance();
    renderAdminControlHub();
    renderAdminOps();
    renderRoleDashboardPanel();
  } catch (error) {
    if (!sameSessionRevision(sessionRevision)) return;
    if (handleAuthError(error)) return;
    state.modelMetrics = null;
    state.modelTrainingAt = "";
  }
}

async function runAdminPipelineAction(endpoint, button, idleLabel, workingLabel, successMessage) {
  if (normalizeAccessRole(state.userRole) !== "admin") return;
  const sessionRevision = state.sessionRevision;
  setButtonLoading(button, true, idleLabel, workingLabel);
  $("#pipelineActionStatus").textContent = workingLabel;
  try {
    await callApi(endpoint, { method: "POST", timeoutMs: endpoint === "/train" ? 120000 : 30000 });
    if (!sameSessionRevision(sessionRevision) || normalizeAccessRole(state.userRole) !== "admin") return;
    $("#pipelineActionStatus").textContent = successMessage;
    toast(successMessage, "success");
    if (endpoint === "/train") {
      await loadAdminModelPerformance();
    }
  } catch (error) {
    if (!sameSessionRevision(sessionRevision)) return;
    if (handleAuthError(error)) return;
    $("#pipelineActionStatus").textContent = error.message || "Pipeline action failed.";
    toast(error.message || "Pipeline action failed.", "error");
  } finally {
    setButtonLoading(button, false, idleLabel);
  }
}

function userRoleTagClass(role) {
  const normalized = normalizeAccessRole(role);
  if (normalized === "admin") return "admin";
  if (normalized === "marketing_staff") return "marketing";
  return "analyst";
}

function getRoleTransitionAction(role) {
  const normalized = normalizeAccessRole(role);
  if (normalized === "marketing_staff") {
    return {
      nextRole: "analyst",
      label: "Promote to Analyst",
      toneClass: "user-promote-btn"
    };
  }
  if (normalized === "analyst") {
    return {
      nextRole: "marketing_staff",
      label: "Demote to Marketing Staff",
      toneClass: "user-demote-btn"
    };
  }
  return null;
}

function userRoleActions(row) {
  if (row.is_protected) return '<span class="users-note">Protected admin account</span>';
  if (row.is_self) return '<span class="users-note">Your account</span>';

  const transition = getRoleTransitionAction(row.role);
  const roleAction = transition
    ? '<button class="ghost-btn user-action-btn ' + transition.toneClass + '" type="button" data-action="set-role" data-email="' + row.email + '" data-role="' + transition.nextRole + '">' + transition.label + "</button>"
    : "";
  return [
    '<div class="users-actions">',
    roleAction,
    '<button class="ghost-btn user-action-btn user-delete-btn" type="button" data-action="delete-user" data-email="' + row.email + '">Delete</button>',
    '</div>'
  ].join("");
}

function renderUsersTable(users) {
  const tbody = $("#usersTableBody");
  if (!Array.isArray(users) || !users.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="users-note">No users available.</td></tr>';
    return;
  }
  tbody.innerHTML = users.map((row) => {
    const roleLabel = humanizeRole(row.role);
    return [
      "<tr>",
      "<td>" + (row.name || "Unknown") + "</td>",
      "<td>" + (row.email || "") + "</td>",
      '<td><span class="tag ' + userRoleTagClass(row.role) + '">' + roleLabel + "</span></td>",
      "<td>" + userRoleActions(row) + "</td>",
      "</tr>"
    ].join("");
  }).join("");
}

async function loadUsersManagement() {
  if (state.usersLoading) return;
  const sessionRevision = state.sessionRevision;
  state.usersLoading = true;
  const button = $("#refreshUsersButton");
  if (button) setButtonLoading(button, true, "Refresh Users");
  try {
    const payload = await callApi("/admin/users");
    if (!sameSessionRevision(sessionRevision) || normalizeAccessRole(state.userRole) !== "admin") return;
    const users = Array.isArray(payload.users) ? payload.users : [];
    state.users = users;
    state.usersLoaded = true;
    renderUsersTable(users);
    renderAdminControlHub();
    buildAdminNotifications();
    renderRoleDashboardPanel();
  } catch (error) {
    if (!sameSessionRevision(sessionRevision)) return;
    if (handleAuthError(error)) return;
    state.usersLoaded = false;
    renderUsersTable([]);
    toast(error.message || "Failed to load users.", "error");
  } finally {
    state.usersLoading = false;
    if (button) setButtonLoading(button, false, "Refresh Users");
  }
}

async function handleUsersTableAction(event) {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const sessionRevision = state.sessionRevision;
  const action = button.dataset.action || "";
  const email = button.dataset.email || "";
  const role = button.dataset.role || "";
  if (!email) return;

  if (action === "delete-user") {
    const confirmed = window.confirm("Delete user " + email + "? This action cannot be undone.");
    if (!confirmed) return;
  }

  const workingText = action === "delete-user" ? "Deleting..." : "Updating...";
  setButtonLoading(button, true, button.textContent.trim(), workingText);
  try {
    if (action === "delete-user") {
      await callApi("/admin/users/delete", {
        method: "POST",
        body: { email }
      });
      if (!sameSessionRevision(sessionRevision) || normalizeAccessRole(state.userRole) !== "admin") return;
      toast("User deleted.", "success");
    } else if (action === "set-role") {
      if (!role) return;
      await callApi("/admin/users/role", {
        method: "POST",
        body: { email, role }
      });
      if (!sameSessionRevision(sessionRevision) || normalizeAccessRole(state.userRole) !== "admin") return;
      toast("User role updated to " + humanizeRole(role) + ".", "success");
    } else {
      return;
    }
    await loadUsersManagement();
  } catch (error) {
    if (!sameSessionRevision(sessionRevision)) return;
    if (handleAuthError(error)) return;
    toast(error.message || "User update failed.", "error");
  } finally {
    setButtonLoading(button, false, button.dataset.label || button.textContent.trim());
  }
}
