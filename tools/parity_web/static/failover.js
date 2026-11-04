/* Failover and trace timeline renderer. No dependencies.
 *
 * Public surface:
 *   window.Oarumi.failover.render(el, trace, failoverEvents, opts)
 *   window.Oarumi.failover.summarise(trace, failoverEvents) -> {neural, deterministic, failovers}
 */

(function () {
  "use strict";

  const NS = (window.Oarumi = window.Oarumi || {});

  function _esc(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function _icon(kind) {
    if (kind === "neural") return "N";
    if (kind === "deterministic") return "D";
    return "!";
  }

  function _class(kind) {
    return `timeline-entry ${kind}`;
  }

  function summarise(trace, failoverEvents) {
    trace = trace || [];
    failoverEvents = failoverEvents || [];
    const counts = { neural: 0, deterministic: 0, failovers: failoverEvents.length };
    for (const t of trace) {
      if (t.path === "neural") counts.neural += 1;
      else counts.deterministic += 1;
    }
    return counts;
  }

  /**
   * Render a timeline of trace entries and failover events.
   *
   *   trace:            [{step, path, reason}, ...]
   *   failoverEvents:   [{component, trigger, t}, ...]
   */
  function render(el, trace, failoverEvents, opts) {
    opts = opts || {};
    trace = trace || [];
    failoverEvents = failoverEvents || [];

    if (trace.length === 0 && failoverEvents.length === 0) {
      el.innerHTML = `<div class="empty">No trace or failover events for this case.</div>`;
      return summarise(trace, failoverEvents);
    }

    const rows = [];

    for (const t of trace) {
      const kind = t.path === "neural" ? "neural" : "deterministic";
      rows.push(`
        <div class="${_class(kind)}">
          <div class="timeline-icon ${kind}">${_icon(kind)}</div>
          <div class="timeline-body">
            <div class="component">${_esc(t.step || "?")}</div>
            <div class="reason">${_esc(t.reason || "")}</div>
          </div>
          <div class="timeline-time">${_esc(kind)}</div>
        </div>
      `);
    }

    for (const f of failoverEvents) {
      rows.push(`
        <div class="${_class("failover")}">
          <div class="timeline-icon failover">${_icon("failover")}</div>
          <div class="timeline-body">
            <div class="component">${_esc(f.component || "?")}</div>
            <div class="reason">${_esc(f.trigger || "")}</div>
          </div>
          <div class="timeline-time">${_esc(f.t || "")}</div>
        </div>
      `);
    }

    const counts = summarise(trace, failoverEvents);
    el.innerHTML = `
      <div class="diff-summary">
        <span>${counts.deterministic} deterministic</span>
        <span>${counts.neural} neural</span>
        <span class="${counts.failovers > 0 ? "dirty" : "clean"}">${counts.failovers} failover${counts.failovers === 1 ? "" : "s"}</span>
      </div>
      <div class="timeline">${rows.join("")}</div>
    `;
    return counts;
  }

  NS.failover = { render, summarise };
})();
