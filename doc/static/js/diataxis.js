/**
 * Diataxis section colouring
 *
 * Classifies each page into one of the four Diataxis quadrants, then:
 *   1. Adds a `dxt-<section>` class to <body> so CSS can paint a coloured
 *      top strip on the content area.
 *   2. Inserts a small floating badge ("Tutorial", "How-to Guide", etc.)
 *      at the top of the page body.
 *   3. Adds `dxt-caption-<section>` to each sidebar caption <p> and
 *      `dxt-section-<section>` to the <ul> that follows it, so CSS can
 *      colour the sidebar navigation headers.
 */
(function () {
  "use strict";

  /* ── Page → section map ─────────────────────────────── */
  var PAGE_SECTIONS = {
    installation:   "tutorial",
    getting_started:"tutorial",
    migration:       "howto",
    troubleshooting:"howto",
    contributing:   "howto",
    manifest:       "reference",
    manual:         "reference",
    changelog:      "reference",
    legal:          "reference",
    vendoring:      "explanation",
    alternatives:   "explanation",
    internal:       "explanation",
  };

  /* ── Sidebar caption text → section key ─────────────── */
  var CAPTION_SECTIONS = {
    "Tutorials":     "tutorial",
    "How-to Guides": "howto",
    "Reference":     "reference",
    "Explanation":   "explanation",
  };

  /* ── Badge labels ───────────────────────────────────── */
  var BADGE_LABELS = {
    tutorial:    "Tutorial",
    howto:       "How-to Guide",
    reference:   "Reference",
    explanation: "Explanation",
  };

  /* ── Determine current page ─────────────────────────── */
  var page = window.location.pathname
    .replace(/\/$/, "/index")
    .replace(/.*\//, "")
    .replace(/\.html$/, "");

  var section = PAGE_SECTIONS[page] || null;

  function applyClasses() {
    /* ── 1. Body class ──────────────────────────────────── */
    if (section && document.body) {
      document.body.classList.add("dxt-" + section);
    }

    /* ── 2. Floating badge ──────────────────────────────── */
    if (section) {
      var body = document.querySelector("div.body") || document.querySelector("div.document");
      if (body) {
        var badge = document.createElement("span");
        badge.className = "dxt-badge dxt-badge-" + section;
        badge.textContent = BADGE_LABELS[section];
        body.insertBefore(badge, body.firstChild);
      }
    }

    /* ── 3. Sidebar captions ────────────────────────────── */
    var captions = document.querySelectorAll(".sphinxsidebar p.caption, .sphinxsidebarwrapper p.caption");
    captions.forEach(function (el) {
      var span = el.querySelector(".caption-text");
      if (!span) return;
      var key = CAPTION_SECTIONS[span.textContent.trim()];
      if (!key) return;
      el.classList.add("dxt-caption-" + key);
      var ul = el.nextElementSibling;
      if (ul && ul.tagName === "UL") {
        ul.classList.add("dxt-section-" + key);
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", applyClasses);
  } else {
    applyClasses();
  }
})();
