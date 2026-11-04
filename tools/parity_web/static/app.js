/* Oarumi Parity SPA. No build step.
 *
 * Public surface:
 *   window.Oarumi.api.{health,listRuns,getRun,createRun,getDiff,getGold}
 *   window.Oarumi.views.{overview,runDetail,runsList,diff,failover}
 *   window.Oarumi.router.navigate(hash)
 */

(function () {
  "use strict";

  const NS = (window.Oarumi = window.Oarumi || {});

  // ---------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function fmtDate(iso) { return iso ? iso.replace("T", " ").replace("Z", "") : "—"; }
  function badge(status) {
    const known = ["pending", "running", "done", "failed", "partial"];
    const s = known.includes(status) ? status : "pending";
    return `<span class="badge badge-${s}">${esc(status || "?")}</span>`;
  }
  function setFooter(msg) {
    const el = $("footer-status");
    if (el) el.textContent = msg;
  }

  // ---------------------------------------------------------------------
  // API client
  // ---------------------------------------------------------------------

  async function _json(res) {
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`HTTP ${res.status}: ${text.slice(0, 200)}`);
    }
    return res.json();
  }

  const api = {
    async health() { return _json(await fetch("/api/health")); },
    async listRuns(limit) {
      const url = limit ? `/api/runs?limit=${limit}` : "/api/runs";
      return _json(await fetch(url));
    },
    async getRun(id) { return _json(await fetch(`/api/runs/${id}`)); },
    async createRun(corpus, targets) {
      return _json(await fetch("/api/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ corpus, targets }),
      }));
    },
    async getDiff(id) { return _json(await fetch(`/api/diff/${id}`)); },
    async getGold(runId, caseId) {
      return _json(await fetch(`/api/gold/${runId}/${caseId}`));
    },
  };

  NS.api = api;

  // ---------------------------------------------------------------------
  // Views
  // ---------------------------------------------------------------------

  const views = {};

  /** Overview: health + last runs + quick-run form. */
  views.overview = async function (root) {
    root.innerHTML = `
      <section class="section">
        <h2 class="section-title">Run parity</h2>
        <div class="card">
          <div class="card-row">
            <div class="form-row" style="flex:1;">
              <div>
                <label for="corpus">Corpus</label>
                <select id="corpus">
                  <option value="parity-basic">parity-basic</option>
                  <option value="parity-complex">parity-complex</option>
                </select>
              </div>
              <div>
                <label for="targets">Targets</label>
                <select id="targets" multiple size="2">
                  <option value="python" selected>python</option>
                  <option value="kotlin">kotlin</option>
                </select>
              </div>
              <button id="run-btn">Run</button>
            </div>
          </div>
        </div>
      </section>
      <section class="section">
        <h2 class="section-title">Recent runs</h2>
        <div id="runs-list"><div class="placeholder">Loading…</div></div>
      </section>
    `;

    $("run-btn").addEventListener("click", async () => {
      const corpus = $("corpus").value;
      const targets = Array.from($("targets").selectedOptions).map((o) => o.value);
      if (targets.length === 0) {
        alert("Select at least one target.");
        return;
      }
      setFooter(`Creating run: ${corpus} → ${targets.join(", ")}`);
      try {
        const r = await api.createRun(corpus, targets);
        setFooter(`Run created: ${r.run_id}`);
        window.location.hash = `#/runs/${r.run_id}`;
      } catch (e) {
        setFooter(`Failed: ${e.message}`);
      }
    });

    await refreshRunsList($("runs-list"));
  };

  async function refreshRunsList(container) {
    try {
      const runs = await api.listRuns(20);
      if (!runs.length) {
        container.innerHTML = `<div class="empty">No runs yet. Trigger one above.</div>`;
        return;
      }
      const rows = runs.map((r) => `
        <tr onclick="window.location.hash='#/runs/${esc(r.id)}'">
          <td class="mono">${esc(r.id.slice(0, 8))}</td>
          <td>${esc(r.corpus)}</td>
          <td class="mono">${esc(r.targets.join(", "))}</td>
          <td>${badge(r.status)}</td>
          <td class="mono">${esc(fmtDate(r.created_at))}</td>
        </tr>
      `).join("");
      container.innerHTML = `
        <table class="data">
          <thead>
            <tr>
              <th>Run</th><th>Corpus</th><th>Targets</th>
              <th>Status</th><th>Created</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      `;
    } catch (e) {
      container.innerHTML = `<div class="error-banner">${esc(e.message)}</div>`;
    }
  }

  /** Run detail: live progress + per-target summary + per-case table. */
  views.runDetail = async function (root, runId) {
    root.innerHTML = `<div class="placeholder">Loading run…</div>`;
    let pollHandle = null;
    let disposed = false;

    const render = (run) => {
      if (disposed) return;
      const terminal = ["done", "failed", "partial"].includes(run.status);
      const targetEntries = Object.entries(run.target_results || {});
      const summaryRows = targetEntries.map(([name, t]) => `
        <tr>
          <td>${esc(name)}</td>
          <td>${badge(t.status)}</td>
          <td class="mono">${esc(fmtDate(t.started_at))}</td>
          <td class="mono">${esc(fmtDate(t.finished_at))}</td>
          <td class="mono">${t.error ? esc(t.error) : (t.payload ? `${t.payload.passed}/${t.payload.total}` : "—")}</td>
        </tr>
      `).join("");

      // Flatten per-case rows from every target's payload.
      const caseRows = [];
      const byTarget = {};
      for (const [name, t] of targetEntries) {
        const cases = (t.payload && t.payload.cases) || [];
        for (const c of cases) {
          (byTarget[c.case_id] = byTarget[c.case_id] || {})[name] = c;
        }
      }
      for (const caseId of Object.keys(byTarget).sort()) {
        const row = byTarget[caseId];
        const targetsHere = Object.keys(row);
        const allMatch = targetsHere.every((t) => row[t].match !== false && !row[t].error);
        const cls = allMatch ? "row-pass" : "row-fail";
        const status = allMatch ? "pass" : "fail";
        caseRows.push(`
          <tr class="${cls}" onclick="window.location.hash='#/diff/${esc(run.id)}'">
            <td class="mono">${esc(caseId)}</td>
            <td>${targetsHere.map((t) => `${esc(t)}: ${badge(row[t].match === false ? "failed" : "done")}`).join(" ")}</td>
            <td class="status">${esc(status)}</td>
          </tr>
        `);
      }

      root.innerHTML = `
        <section class="section">
          <h2 class="section-title">
            Run ${esc(run.id.slice(0, 8))}
            ${badge(run.status)}
            <button class="btn btn-secondary" id="diff-btn" style="float:right;">View diff</button>
            <button class="btn btn-secondary" id="failover-btn" style="float:right;margin-right:8px;">View failovers</button>
          </h2>
          <div class="card">
            <div class="card-row">
              <div>
                <div class="card-title">${esc(run.corpus)}</div>
                <div class="card-subtitle">targets: ${esc(run.targets.join(", "))}</div>
              </div>
              <div>
                <div class="card-subtitle">created: ${esc(fmtDate(run.created_at))}</div>
                <div class="card-subtitle">finished: ${esc(fmtDate(run.finished_at))}</div>
              </div>
            </div>
          </div>
          <table class="data">
            <thead>
              <tr><th>Target</th><th>Status</th><th>Started</th><th>Finished</th><th>Result</th></tr>
            </thead>
            <tbody>${summaryRows}</tbody>
          </table>
          ${run.error ? `<div class="error-banner">${esc(run.error)}</div>` : ""}
        </section>
        <section class="section">
          <h2 class="section-title">Cases</h2>
          ${caseRows.length
            ? `<table class="data"><thead><tr><th>Case</th><th>Targets</th><th>Status</th></tr></thead><tbody>${caseRows.join("")}</tbody></table>`
            : `<div class="empty">No cases yet.</div>`}
        </section>
      `;

      $("diff-btn").addEventListener("click", () => {
        window.location.hash = `#/diff/${run.id}`;
      });
      $("failover-btn").addEventListener("click", () => {
        window.location.hash = `#/failover/${run.id}`;
      });

      setFooter(`Run ${run.status}: ${run.id.slice(0, 8)}`);

      if (terminal && pollHandle) {
        clearInterval(pollHandle);
        pollHandle = null;
      }
    };

    const load = async () => {
      try {
        const run = await api.getRun(runId);
        render(run);
      } catch (e) {
        if (disposed) return;
        root.innerHTML = `<div class="error-banner">${esc(e.message)}</div>`;
      }
    };

    await load();
    pollHandle = setInterval(load, 2000);

    return () => {
      disposed = true;
      if (pollHandle) clearInterval(pollHandle);
    };
  };

  /** Runs list. */
  views.runsList = async function (root) {
    root.innerHTML = `
      <section class="section">
        <h2 class="section-title">All runs</h2>
        <div id="runs-container"><div class="placeholder">Loading…</div></div>
      </section>
    `;
    await refreshRunsList($("runs-container"));
  };

  /** Diff view: python-vs-gold, android-vs-gold, python-vs-android. */
  views.diff = async function (root, runId) {
    root.innerHTML = `<div class="placeholder">Loading diff…</div>`;
    let data;
    try {
      data = await api.getDiff(runId);
    } catch (e) {
      root.innerHTML = `<div class="error-banner">${esc(e.message)}</div>`;
      return;
    }

    const sections = [];

    sections.push(`
      <section class="section">
        <h2 class="section-title">Python vs gold (${data.python_vs_gold.length} diff${data.python_vs_gold.length === 1 ? "" : "s"})</h2>
        <div id="diff-py-gold"></div>
      </section>
    `);
    sections.push(`
      <section class="section">
        <h2 class="section-title">Android vs gold (${data.android_vs_gold.length} diff${data.android_vs_gold.length === 1 ? "" : "s"})</h2>
        <div id="diff-android-gold"></div>
      </section>
    `);
    sections.push(`
      <section class="section">
        <h2 class="section-title">Python vs Android (${data.python_vs_android.length} diff${data.python_vs_android.length === 1 ? "" : "s"})</h2>
        <div id="diff-py-android"></div>
      </section>
    `);

    root.innerHTML = sections.join("");

    const pyGold = $("diff-py-gold");
    if (data.python_vs_gold.length === 0) {
      pyGold.innerHTML = `<div class="empty">No differences. The deterministic path matches gold.</div>`;
    } else {
      const caseId = data.python_vs_gold[0].case_id;
      NS.diff.render(pyGold, data.python_vs_gold[0].expected, data.python_vs_gold[0].got, {
        titleA: "Gold", titleB: "Python",
      });
      if (data.python_vs_gold.length > 1) {
        const list = data.python_vs_gold.map((d) => `<li class="mono">${esc(d.case_id)}</li>`).join("");
        pyGold.insertAdjacentHTML("beforeend",
          `<div class="card"><div class="card-title">Other cases with diffs</div><ul>${list}</ul></div>`);
      }
      // Unused var guard.
      void caseId;
    }

    const androidGold = $("diff-android-gold");
    if (data.android_vs_gold.length === 0) {
      androidGold.innerHTML = `<div class="empty">No differences (or Android target not run).</div>`;
    } else {
      NS.diff.render(androidGold, data.android_vs_gold[0].expected, data.android_vs_gold[0].got, {
        titleA: "Gold", titleB: "Android",
      });
    }

    const pyAndroid = $("diff-py-android");
    if (data.python_vs_android.length === 0) {
      pyAndroid.innerHTML = `<div class="empty">No differences. ADR-0007 holds.</div>`;
    } else {
      NS.diff.render(pyAndroid, data.python_vs_android[0].python, data.python_vs_android[0].android, {
        titleA: "Python", titleB: "Android",
      });
    }

    setFooter(`Diff for ${data.corpus}: ${data.python_vs_gold.length + data.android_vs_gold.length + data.python_vs_android.length} total diffs`);
  };

  /** Failover view: timeline of trace + failover events per case. */
  views.failover = async function (root, runId) {
    root.innerHTML = `<div class="placeholder">Loading failovers…</div>`;
    let run;
    try {
      run = await api.getRun(runId);
    } catch (e) {
      root.innerHTML = `<div class="error-banner">${esc(e.message)}</div>`;
      return;
    }

    // Gather every case with a trace or failover event.
    const rows = [];
    for (const [targetName, target] of Object.entries(run.target_results || {})) {
      const cases = (target.payload && target.payload.cases) || [];
      for (const c of cases) {
        const got = c.got || {};
        const trace = got.trace || [];
        const failovers = got.failover_events || [];
        if (trace.length === 0 && failovers.length === 0) continue;
        rows.push({ targetName, caseId: c.case_id, trace, failovers });
      }
    }

    if (rows.length === 0) {
      root.innerHTML = `<section class="section">
        <h2 class="section-title">Failovers</h2>
        <div class="empty">No trace or failover events in this run.</div>
      </section>`;
      return;
    }

    const blocks = rows.map((r, i) => `
      <section class="section">
        <h2 class="section-title">
          ${esc(r.caseId)}
          <span class="card-subtitle">(${esc(r.targetName)})</span>
        </h2>
        <div id="failover-${i}"></div>
      </section>
    `).join("");

    root.innerHTML = blocks;
    rows.forEach((r, i) => {
      NS.failover.render($(`failover-${i}`), r.trace, r.failovers, {});
    });

    const totalFailovers = rows.reduce((n, r) => n + r.failovers.length, 0);
    setFooter(`${rows.length} case${rows.length === 1 ? "" : "s"} with trace, ${totalFailovers} failover event${totalFailovers === 1 ? "" : "s"}`);
  };

  NS.views = views;

  // ---------------------------------------------------------------------
  // Health badge
  // ---------------------------------------------------------------------

  async function refreshHealth() {
    const el = $("health");
    if (!el) return;
    try {
      const h = await api.health();
      el.innerHTML = `
        <span class="dot dot-ok"></span>
        <span class="health-label">API ${esc(h.python)}</span>
      `;
    } catch (e) {
      el.innerHTML = `
        <span class="dot dot-failed"></span>
        <span class="health-label">offline</span>
      `;
    }
  }

  // ---------------------------------------------------------------------
  // Router
  // ---------------------------------------------------------------------

  let currentCleanup = null;

  async function route() {
    const hash = window.location.hash || "#/";
    const parts = hash.replace(/^#/, "").split("/").filter(Boolean);
    const root = $("app");

    // Highlight nav.
    const navOverview = document.querySelector('[data-route="overview"]');
    const navRuns = document.querySelector('[data-route="runs"]');
    navOverview.classList.remove("active");
    navRuns.classList.remove("active");

    // Cleanup previous view.
    if (typeof currentCleanup === "function") {
      try { currentCleanup(); } catch (e) { void e; }
      currentCleanup = null;
    }

    // Dispatch.
    if (parts.length === 0) {
      navOverview.classList.add("active");
      await views.overview(root);
    } else if (parts[0] === "runs" && parts.length === 1) {
      navRuns.classList.add("active");
      await views.runsList(root);
    } else if (parts[0] === "runs" && parts.length === 2) {
      navRuns.classList.add("active");
      currentCleanup = await views.runDetail(root, parts[1]);
    } else if (parts[0] === "diff" && parts.length === 2) {
      navRuns.classList.add("active");
      await views.diff(root, parts[1]);
    } else if (parts[0] === "failover" && parts.length === 2) {
      navRuns.classList.add("active");
      await views.failover(root, parts[1]);
    } else {
      root.innerHTML = `<div class="error-banner">Unknown route: ${esc(hash)}</div>`;
    }
  }

  NS.router = { navigate(hash) { window.location.hash = hash; } };

  // ---------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------

  function init() {
    window.addEventListener("hashchange", route);
    refreshHealth();
    setInterval(refreshHealth, 10000);
    route();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
