function getHistory() {
  const data = scopedStorageRead(HISTORY_KEY, []);
  return Array.isArray(data) ? data : [];
}

function storeHistory(entry) {
  const next = [entry, ...getHistory()].slice(0, 10);
  scopedStorageWrite(HISTORY_KEY, next);
  renderHistory();
}

function renderHistory() {
  const entries = getHistory();
  const shell = $("#historyTimeline");
  if (!entries.length) {
    shell.innerHTML = '<div class="empty-state">No local activity has been recorded yet.</div>';
    return;
  }

  shell.innerHTML = entries.map((entry) => {
    return [
      '<article class="timeline-item">',
      "<strong>" + entry.title + "</strong>",
      "<time>" + entry.time + "</time>",
      "<p>" + entry.summary + "</p>",
      "</article>"
    ].join("");
  }).join("");
}

function clearHistory() {
  scopedStorageWrite(HISTORY_KEY, []);
  renderHistory();
  toast("Local history cleared.", "info");
}
