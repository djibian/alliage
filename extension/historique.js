// SPDX-License-Identifier: AGPL-3.0-or-later
/* P3.2: commandes d'historique pour une page de session locale vérifiée.
 * Aucun fetch, jeton, appel réseau, écriture Git ni publication.
 */
(() => {
  "use strict";
  if (location.protocol !== "file:" ||
      !/^\/.+\/alliage-experiences\/historique\/p31-final-[^/]+\/navigation\.html$/.test(location.pathname)) return;
  if (document.getElementById("alliage-history-panel")) return;
  const blob = document.getElementById("alliage-history-data");
  const frame = document.getElementById("alliage-preview-frame");
  if (!blob || !frame || blob.type !== "application/json") return;

  function acceptPayload(payload) {
    if (!payload || payload.schema !== "alliage.quarto-navigation.v0" ||
        payload.deployment_verified !== false || payload.reference_is_working_tree !== false ||
        payload.verification !== "POINT_IN_TIME_ONLY" ||
        !Array.isArray(payload.entries) || payload.entries.length < 2 || payload.entries.length > 20) return null;
    const sessionRoot = location.pathname.slice(0, location.pathname.lastIndexOf("/") + 1);
    const seen = new Set();
    const commits = new Set();
    const entries = [];
    for (const item of payload.entries) {
      if (!item || typeof item.id !== "string" || !/^V[1-9][0-9]?$/.test(item.id) ||
          typeof item.commit !== "string" || !/^[0-9a-f]{40}$/.test(item.commit) ||
          typeof item.html !== "string" || item.publication_status !== "NOT_INITIATED_BY_ALLIAGE" ||
          typeof item.quarto_version !== "string" || !item.quarto_version ||
          seen.has(item.id) || commits.has(item.commit)) return null;
      let url;
      try { url = new URL(item.html, location.href); } catch (_) { return null; }
      // This is not a file integrity check; it is a strict frame-navigation allowlist.
      const prefix = sessionRoot + item.id + "/project/";
      if (url.protocol !== "file:" || url.host || url.search || url.hash ||
          !url.pathname.startsWith(prefix) ||
          !/\/activite\.html$/.test(url.pathname) ||
          url.pathname.includes("/../") || url.pathname.includes("/./")) return null;
      seen.add(item.id);
      commits.add(item.commit);
      entries.push({id:item.id, commit:item.commit, url:url.href});
    }
    if (!seen.has(payload.reference_id)) return null;
    return {entries, reference:payload.reference_id};
  }

  let data;
  try { data = acceptPayload(JSON.parse(blob.textContent)); } catch (_) { return; }
  if (!data) return;

  const host = document.createElement("aside");
  host.id = "alliage-history-panel";
  host.setAttribute("aria-label", "Navigation historique Alliage");
  host.style.cssText = "position:fixed;left:50%;bottom:16px;transform:translateX(-50%);" +
    "z-index:2147483647;max-width:calc(100vw - 24px);";
  const shadow = host.attachShadow({mode:"closed"});
  const style = document.createElement("style");
  style.textContent = [
    ":host{all:initial}*{box-sizing:border-box}",
    ".nav{font:13px/1.4 system-ui,sans-serif;color:#182534;background:#fff;",
    "border:1px solid #6d7d89;box-shadow:0 8px 28px #0004;border-radius:11px;",
    "padding:9px 13px;max-width:650px}",
    ".row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}",
    ".title{font-weight:700;margin-right:7px}",
    "button,select{font:inherit;border:1px solid #667785;border-radius:6px;",
    "background:#f7fafc;color:#14212a;padding:6px;cursor:pointer}",
    "button:disabled{opacity:.5;cursor:not-allowed}",
    "button:focus-visible,select:focus-visible{outline:3px solid #2563eb}",
    ".small{font-size:11px;color:#354a59;margin-top:5px;overflow-wrap:anywhere}"
  ].join("");
  const nav = document.createElement("div");
  nav.className = "nav";
  const row = document.createElement("div");
  row.className = "row";
  const title = document.createElement("span");
  title.className = "title";
  title.textContent = "Alliage · Historique";
  const previous = document.createElement("button");
  previous.type = "button";
  previous.textContent = "← Précédente";
  previous.setAttribute("aria-label", "Version précédente");
  const select = document.createElement("select");
  select.setAttribute("aria-label", "Révision de conception");
  for (const entry of data.entries) {
    const opt = document.createElement("option");
    opt.value = entry.id;
    opt.textContent = entry.id + " · " + entry.commit.slice(0, 8);
    select.appendChild(opt);
  }
  const next = document.createElement("button");
  next.type = "button";
  next.textContent = "Suivante →";
  next.setAttribute("aria-label", "Version suivante");
  const back = document.createElement("button");
  back.type = "button";
  back.textContent = "Retour à la référence (" + data.reference + ")";
  const details = document.createElement("div");
  details.className = "small";
  details.setAttribute("role", "status");
  row.append(title, previous, select, next, back);
  nav.append(row, details);
  shadow.append(style, nav);
  document.documentElement.appendChild(host);

  // Explicit reference: never claim that it is the Git HEAD, deployment or
  // actual teacher working tree. A visible rendering is not a publication.
  let index = data.entries.findIndex(x => x.id === data.reference);
  function move(to) {
    if (!Number.isInteger(to) || to < 0 || to >= data.entries.length) return;
    index = to;
    const current = data.entries[index];
    select.value = current.id;
    previous.disabled = index === 0;
    next.disabled = index === data.entries.length - 1;
    back.disabled = current.id === data.reference;
    frame.src = current.url;
    details.textContent = current.id + " · commit " + current.commit.slice(0, 12) +
      " · Aperçu local vérifié à la création (non recontrôlé en temps réel)." +
      " Référence choisie ≠ branche Git. Aucun déploiement vérifié.";
  }
  previous.addEventListener("click", () => move(index - 1));
  next.addEventListener("click", () => move(index + 1));
  select.addEventListener("change", () => {
    const target = data.entries.findIndex(e => e.id === select.value);
    move(target);
  });
  back.addEventListener("click", () => move(data.entries.findIndex(e => e.id === data.reference)));
  const fallback = document.getElementById("alliage-fallback");
  if (fallback) fallback.hidden = true;
  move(index);
})();
