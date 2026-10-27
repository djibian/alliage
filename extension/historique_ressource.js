// SPDX-License-Identifier: AGPL-3.0-or-later
/* Experimental resource-first P3.2 surface: local, read-only and opt-in.
 * The URL query parameter is not a signature or a live integrity proof.
 * No Git, filesystem fetch, network access, token or publication action.
 */
(() => {
  "use strict";
  if (window.top !== window.self) return;
  const filePreview = location.protocol === "file:" && !location.host;
  const httpPreview = location.protocol === "http:" &&
    location.hostname === "127.0.0.1" && location.port !== "";
  if (!filePreview && !httpPreview) return;
  const match = filePreview
    ? location.pathname.match(
        /^(.*\/alliage-experiences\/historique\/p31-final-observed-[a-zA-Z0-9_-]+)\/(V[12])\/project\/_site\/activite\.html$/
      )
    : location.pathname.match(
        /^(\/alliage-local-[0-9a-f]{32})\/(V[12])\/project\/_site\/activite\.html$/
      );
  if (!match || document.getElementById("alliage-resource-history")) return;
  // The query is intentionally separate from Quarto's #heading anchors.
  // Require one parameter exactly; do not accept additional or duplicate keys.
  if (location.search.length > 3000) return;
  let payload;
  try {
    // Firefox's content-script debugger observed an empty keys() iterator
    // even while getAll() returned the one expected value. Do not use the
    // iterator as a security gate. This URL is generated with exactly one
    // literal query key and percent-encoded JSON; reject raw extra separators.
    if (!/^[?]alliage-history-v0=[^&]+$/.test(location.search)) return;
    const query = new URLSearchParams(location.search);
    const values = query.getAll("alliage-history-v0");
    if (values.length !== 1) return;
    payload = JSON.parse(values[0]);
  } catch (_) { return; }
  if (!payload || payload.schema !== "alliage.quarto-resource-history.v0" ||
      payload.reference_id !== "V1" || payload.observed_id !== "V2" ||
      payload.verification !== "POINT_IN_TIME_ONLY" ||
      payload.deployment_verified !== false || payload.publication_performed !== false ||
      typeof payload.resource_id !== "string" ||
      !/^quarto:[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+:activite\.qmd$/.test(payload.resource_id) ||
      !Array.isArray(payload.entries) || payload.entries.length !== 2) return;
  const [first, second] = payload.entries;
  if (!first || !second || first.id !== "V1" || second.id !== "V2" ||
      typeof first.commit !== "string" || typeof second.commit !== "string" ||
      !/^[0-9a-f]{40}$/.test(first.commit) || !/^[0-9a-f]{40}$/.test(second.commit) ||
      first.commit === second.commit) return;

  // The current resource's URL determines the session. Query metadata contains
  // no URL/path and cannot direct navigation to another directory or website.
  const directory = match[1];
  const current = match[2];
  function revisionUrl(id) {
    const url = new URL(location.href);
    url.pathname = directory + "/" + id + "/project/_site/activite.html";
    url.search = location.search;
    // Keep Quarto's own #heading anchor independently of history metadata.
    url.hash = location.hash;
    return url.href;
  }
  const host = document.createElement("aside");
  host.id = "alliage-resource-history";
  host.setAttribute("aria-label", "Historique local de la ressource Quarto");
  host.style.cssText = "position:fixed;z-index:2147483647;left:50%;bottom:16px;" +
    "transform:translateX(-50%);max-width:calc(100vw - 24px);";
  const shadow = host.attachShadow({mode:"closed"});
  const style = document.createElement("style");
  style.textContent = [
    ":host{all:initial}*{box-sizing:border-box}",
    ".box{font:13px/1.4 system-ui,sans-serif;background:white;color:#182534;",
    "border:1px solid #667785;border-radius:11px;box-shadow:0 8px 28px #0004;",
    "padding:9px 13px;max-width:660px}",
    ".row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}",
    "button{font:inherit;padding:6px;border-radius:6px;border:1px solid #667785;",
    "background:#f7fafc;color:#14212a;cursor:pointer}",
    "button:disabled{opacity:.55;cursor:not-allowed}",
    "button:focus-visible{outline:3px solid #2563eb}",
    ".note{font-size:11px;color:#354a59;margin-top:5px;overflow-wrap:anywhere}"
  ].join("");
  const box = document.createElement("div");box.className="box";
  const row = document.createElement("div");row.className="row";
  const title = document.createElement("strong");
  title.textContent = "Alliage · Historique sur la ressource";
  const v1 = document.createElement("button");
  v1.type="button";v1.textContent="← V1";v1.disabled=current==="V1";
  const v2 = document.createElement("button");
  v2.type="button";v2.textContent="V2 →";v2.disabled=current==="V2";
  const note = document.createElement("div");note.className="note";
  const sha = current === "V1" ? first.commit : second.commit;
  note.textContent = current + " · SHA indiqué " + sha.slice(0,12) +
    " · révision locale de conception (non publiée). " +
    "URL et empreintes non recontrôlées par Firefox ; aucun déploiement vérifié.";
  v1.addEventListener("click", () => { if (current !== "V1") window.location.assign(revisionUrl("V1")); });
  v2.addEventListener("click", () => { if (current !== "V2") window.location.assign(revisionUrl("V2")); });
  row.append(title,v1,v2);
  box.append(row,note);
  shadow.append(style,box);
  document.documentElement.appendChild(host);
})();
