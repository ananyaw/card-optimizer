// Onboarding steps 1-2: welcome, then pick cards from a static searchable list.
// Stores card IDs only (never card numbers). Uses chrome.storage.local inside the
// extension; falls back to localStorage when the page is opened as a plain file.
(function () {
  "use strict";

  var CARDS = JSON.parse(document.getElementById("card-data").textContent);
  var KEY_SELECTED = "selectedCardIds";
  var KEY_REQUESTS = "requestedCards";

  var el = function (id) { return document.getElementById(id); };
  var screens = { welcome: el("welcome"), picker: el("picker"), done: el("done") };

  // ---- storage -------------------------------------------------------------
  var hasChrome = typeof chrome !== "undefined" && chrome.storage && chrome.storage.local;

  function storeGet(key, fallback) {
    if (hasChrome) {
      return chrome.storage.local.get(key).then(function (r) {
        return r[key] === undefined ? fallback : r[key];
      }).catch(function () { return fallback; });
    }
    try {
      var v = localStorage.getItem(key);
      return Promise.resolve(v ? JSON.parse(v) : fallback);
    } catch (e) { return Promise.resolve(fallback); }
  }

  function storeSet(key, value) {
    if (hasChrome) {
      var o = {}; o[key] = value;
      return chrome.storage.local.set(o).catch(function () {});
    }
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) {}
    return Promise.resolve();
  }

  // ---- search --------------------------------------------------------------
  function norm(s) { return String(s).toLowerCase().replace(/[^a-z0-9]/g, ""); }

  CARDS.forEach(function (c) {
    c._hay = norm([c.name, c.issuer].concat(c.aliases || []).join(" "));
  });

  // Every typed word must appear somewhere in the card's name, issuer or aliases.
  function matches(card, query) {
    var tokens = query.toLowerCase().split(/\s+/).map(norm).filter(Boolean);
    return tokens.every(function (t) { return card._hay.indexOf(t) !== -1; });
  }

  // ---- state & rendering ---------------------------------------------------
  var selected = new Set();
  var query = "";

  function show(name) {
    Object.keys(screens).forEach(function (k) { screens[k].hidden = k !== name; });
    window.scrollTo(0, 0);
  }

  function renderChips() {
    var box = el("chips");
    box.textContent = "";
    CARDS.filter(function (c) { return selected.has(c.id); }).forEach(function (c) {
      var chip = document.createElement("span");
      chip.className = "chip";
      chip.appendChild(document.createTextNode(c.name));
      var x = document.createElement("button");
      x.type = "button";
      x.setAttribute("aria-label", "Remove " + c.name);
      x.dataset.remove = c.id;
      x.textContent = "×";
      chip.appendChild(x);
      box.appendChild(chip);
    });
  }

  function renderList() {
    var list = el("list");
    list.textContent = "";
    var shown = CARDS.filter(function (c) { return matches(c, query); });

    shown.forEach(function (c) {
      var li = document.createElement("li");
      var label = document.createElement("label");
      label.className = "row";
      var cb = document.createElement("input");
      cb.type = "checkbox";
      cb.value = c.id;
      cb.checked = selected.has(c.id);
      var text = document.createElement("span");
      var name = document.createElement("span");
      name.className = "name"; name.textContent = c.name;
      var issuer = document.createElement("span");
      issuer.className = "issuer"; issuer.textContent = c.issuer;
      text.appendChild(name); text.appendChild(issuer);
      label.appendChild(cb); label.appendChild(text);
      li.appendChild(label);
      list.appendChild(li);
    });

    var none = shown.length === 0;
    el("empty").hidden = !none;
    list.hidden = none;
    if (none) {
      el("empty-query").textContent = "“" + query.trim() + "”";
      el("request-thanks").hidden = true;
      el("request").hidden = false;
    }
  }

  function renderFooter() {
    var n = selected.size;
    el("count").textContent = n + " selected";
    el("continue").disabled = n === 0;
  }

  function renderAll() { renderChips(); renderList(); renderFooter(); }

  function persist() { return storeSet(KEY_SELECTED, Array.from(selected)); }

  // ---- events --------------------------------------------------------------
  el("start").addEventListener("click", function () { show("picker"); el("search").focus(); });

  el("search").addEventListener("input", function (e) {
    query = e.target.value;
    renderList();
  });

  el("list").addEventListener("change", function (e) {
    var id = e.target.value;
    if (e.target.checked) selected.add(id); else selected.delete(id);
    persist(); renderChips(); renderFooter();
  });

  el("chips").addEventListener("click", function (e) {
    var id = e.target.dataset && e.target.dataset.remove;
    if (!id) return;
    selected.delete(id);
    persist(); renderAll();
  });

  el("request").addEventListener("click", function () {
    var text = query.trim();
    if (!text) return;
    storeGet(KEY_REQUESTS, []).then(function (arr) {
      if (arr.indexOf(text) === -1) arr.push(text);
      return storeSet(KEY_REQUESTS, arr);
    }).then(function () {
      el("request").hidden = true;
      el("request-thanks").hidden = false;
    });
  });

  el("continue").addEventListener("click", function () {
    persist().then(function () {
      var names = CARDS.filter(function (c) { return selected.has(c.id); })
                       .map(function (c) { return c.name; });
      el("done-summary").textContent = "Saved " + names.length + " card" +
        (names.length === 1 ? "" : "s") + ": " + names.join(", ") + ".";
      show("done");
    });
  });

  el("edit").addEventListener("click", function () { show("picker"); });

  // ---- init: returning users go straight to their saved selection ----------
  storeGet(KEY_SELECTED, []).then(function (ids) {
    var valid = new Set(CARDS.map(function (c) { return c.id; }));
    selected = new Set(ids.filter(function (id) { return valid.has(id); }));
    renderAll();
    if (selected.size > 0) {
      var names = CARDS.filter(function (c) { return selected.has(c.id); })
                       .map(function (c) { return c.name; });
      el("done-summary").textContent = "Saved " + names.length + " card" +
        (names.length === 1 ? "" : "s") + ": " + names.join(", ") + ".";
      show("done");
    }
  });
})();
