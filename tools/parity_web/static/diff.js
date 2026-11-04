/* Side-by-side JSON diff renderer. No dependencies.
 *
 * Public surface:
 *   window.Oarumi.diff.render(el, objA, objB, opts)
 *   window.Oarumi.diff.flatten(obj) -> array of {path, value}
 *   window.Oarumi.diff.compare(a, b) -> {same, onlyA, onlyB, changed}
 */

(function () {
  "use strict";

  const NS = (window.Oarumi = window.Oarumi || {});

  /** Flatten a JSON value into [{path, value}] entries. Arrays use [i]. */
  function flatten(obj, prefix, out) {
    out = out || [];
    prefix = prefix || "";

    if (obj === null || obj === undefined) {
      out.push({ path: prefix || "$", value: obj });
      return out;
    }

    if (Array.isArray(obj)) {
      if (obj.length === 0) {
        out.push({ path: prefix || "$", value: [] });
        return out;
      }
      for (let i = 0; i < obj.length; i++) {
        flatten(obj[i], `${prefix}[${i}]`, out);
      }
      return out;
    }

    if (typeof obj === "object") {
      const keys = Object.keys(obj);
      if (keys.length === 0) {
        out.push({ path: prefix || "$", value: {} });
        return out;
      }
      for (const key of keys) {
        const path = prefix ? `${prefix}.${key}` : key;
        flatten(obj[key], path, out);
      }
      return out;
    }

    out.push({ path: prefix || "$", value: obj });
    return out;
  }

  /** Compare two flattened entries into categories. */
  function compare(a, b) {
    const fa = flatten(a).reduce((acc, e) => (acc[e.path] = e.value, acc), {});
    const fb = flatten(b).reduce((acc, e) => (acc[e.path] = e.value, acc), {});

    const same = [];
    const onlyA = [];
    const onlyB = [];
    const changed = [];

    const keys = new Set([...Object.keys(fa), ...Object.keys(fb)]);
    for (const path of [...keys].sort()) {
      const inA = Object.prototype.hasOwnProperty.call(fa, path);
      const inB = Object.prototype.hasOwnProperty.call(fb, path);
      if (inA && !inB) { onlyA.push({ path, value: fa[path] }); continue; }
      if (!inA && inB) { onlyB.push({ path, value: fb[path] }); continue; }
      if (JSON.stringify(fa[path]) === JSON.stringify(fb[path])) {
        same.push({ path, value: fa[path] });
      } else {
        changed.push({ path, a: fa[path], b: fb[path] });
      }
    }
    return { same, onlyA, onlyB, changed };
  }

  function _esc(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function _renderValue(v) {
    if (typeof v === "string") return `"${_esc(v)}"`;
    if (v === null) return "null";
    if (typeof v === "object") return _esc(JSON.stringify(v));
    return _esc(String(v));
  }

  function _renderPane(title, entries, style) {
    const lines = entries.map((e) => {
      const cls = `diff-line ${style || "same"}`;
      return `<div class="${cls}"><span class="diff-path">${_esc(e.path)}</span>: ${_renderValue(e.value)}</div>`;
    });
    return `
      <div class="diff-pane">
        <div class="diff-pane-title">${_esc(title)}</div>
        <div class="diff-json">${lines.join("") || "<em>(empty)</em>"}</div>
      </div>
    `;
  }

  /** Render side-by-side. objA goes left, objB goes right. */
  function render(el, objA, objB, opts) {
    opts = opts || {};
    const titleA = opts.titleA || "Python";
    const titleB = opts.titleB || "Other";
    const cmp = compare(objA, objB);

    const clean = cmp.onlyA.length === 0 && cmp.onlyB.length === 0 && cmp.changed.length === 0;
    const summary = clean
      ? `<span class="clean">No differences</span>`
      : `<span class="dirty">${cmp.changed.length + cmp.onlyA.length + cmp.onlyB.length} difference${cmp.changed.length + cmp.onlyA.length + cmp.onlyB.length === 1 ? "" : "s"}</span>`;

    // Combine into left and right "flat" lists with classification.
    const leftEntries = [];
    const rightEntries = [];
    const seen = new Set();

    for (const e of cmp.same) {
      leftEntries.push({ path: e.path, value: e.value });
      rightEntries.push({ path: e.path, value: e.value });
      seen.add(e.path);
    }
    for (const e of cmp.changed) {
      leftEntries.push({ path: e.path, value: e.a });
      rightEntries.push({ path: e.path, value: e.b });
      seen.add(e.path);
    }
    for (const e of cmp.onlyA) {
      leftEntries.push({ path: e.path, value: e.value });
      seen.add(e.path);
    }
    for (const e of cmp.onlyB) {
      rightEntries.push({ path: e.path, value: e.value });
      seen.add(e.path);
    }

    const leftLines = leftEntries.map((e) => {
      const isDiff = cmp.changed.some((c) => c.path === e.path) || cmp.onlyA.some((c) => c.path === e.path);
      const cls = isDiff ? "removed" : "same";
      return `<div class="diff-line ${cls}"><span class="diff-path">${_esc(e.path)}</span>: ${_renderValue(e.value)}</div>`;
    });
    const rightLines = rightEntries.map((e) => {
      const isDiff = cmp.changed.some((c) => c.path === e.path) || cmp.onlyB.some((c) => c.path === e.path);
      const cls = isDiff ? "added" : "same";
      return `<div class="diff-line ${cls}"><span class="diff-path">${_esc(e.path)}</span>: ${_renderValue(e.value)}</div>`;
    });

    el.innerHTML = `
      <div class="diff-summary">${summary}</div>
      <div class="diff-container">
        <div class="diff-pane">
          <div class="diff-pane-title">${_esc(titleA)}</div>
          <div class="diff-json">${leftLines.join("") || "<em>(empty)</em>"}</div>
        </div>
        <div class="diff-pane">
          <div class="diff-pane-title">${_esc(titleB)}</div>
          <div class="diff-json">${rightLines.join("") || "<em>(empty)</em>"}</div>
        </div>
      </div>
    `;
    return { clean, cmp };
  }

  NS.diff = { render, flatten, compare };
})();
