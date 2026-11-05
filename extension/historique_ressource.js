// SPDX-License-Identifier: AGPL-3.0-or-later
/* Experimental resource-first P3.2 surface with opt-in public-demo refresh.
 * The URL query parameter is not a signature or a live integrity proof.
 * Git+Quarto refresh requires separate launcher opt-in and a conscious click;
 * no AI API, source write, merge or publication is initiated here.
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
    "button:focus-visible,textarea:focus-visible{outline:3px solid #2563eb}",
    "textarea{display:block;width:100%;min-height:120px;margin-top:6px;font:12px/1.5 monospace;resize:vertical}",
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
  // Pareto P4: a context HANDOFF to Firefox's existing native chatbot,
  // never a chatbot API, clipboard read, conversation scraping or Git write.
  const ai = document.createElement("button");
  ai.type="button";ai.textContent="Préparer demande IA";
  const keep = document.createElement("button");
  keep.type="button";keep.textContent="Retenir V2 (local)";
  const reject = document.createElement("button");
  reject.type="button";reject.textContent="Écarter V2 (local)";
  // Visible only on the one explicitly public/fictional Quarto demo.
  // The local HTTP server independently checks launcher opt-in, ref,
  // one-use token and the browser's same-origin POST; URL claims alone
  // cannot enable Git operations.
  const demoRefresh = httpPreview &&
    payload.resource_id === "quarto:djibian/alliage:activite.qmd";
  const refresh = document.createElement("button");
  refresh.type="button";refresh.textContent="Actualiser les révisions";
  const refreshConsentLabel = document.createElement("label");
  refreshConsentLabel.style.cssText="display:block;font:12px system-ui,sans-serif;margin-top:7px";
  const refreshConsent = document.createElement("input");
  refreshConsent.type="checkbox";refreshConsent.checked=false;
  refreshConsentLabel.append(refreshConsent,document.createTextNode(
    " Je demande explicitement un fetch Git et un rendu Quarto de la seule activité PUBLIQUE/FICTIVE de confiance."));
  const refreshStatus = document.createElement("div");refreshStatus.className="note";
  refreshStatus.textContent="Actualisation désactivée par défaut ; lancer avec --browser-refresh pour l'autoriser.";
  const decision = document.createElement("div");decision.className="note";
  decision.textContent="Décision non prise ; aucun enregistrement Git ni publication.";
  const consentLabel = document.createElement("label");
  consentLabel.style.cssText="display:block;font:12px system-ui,sans-serif;margin-top:7px";
  const consent = document.createElement("input");
  consent.type="checkbox";consent.checked=false;
  consentLabel.append(consent,document.createTextNode(
    " Je confirme que ce contexte est public ou fictif et peut être partagé avec l’IA."));
  const promptBox = document.createElement("textarea");
  promptBox.readOnly=true;promptBox.hidden=true;
  promptBox.setAttribute("aria-label","Demande à copier manuellement dans le panneau latéral Firefox");
  const aiStatus = document.createElement("div");aiStatus.className="note";
  aiStatus.textContent="Aucun contenu envoyé. Après préparation, copier le texte dans le chatbot latéral.";
  const note = document.createElement("div");note.className="note";
  const sha = current === "V1" ? first.commit : second.commit;
  note.textContent = current + " · SHA indiqué " + sha.slice(0,12) +
    " · révision locale de conception (non publiée). " +
    "URL et empreintes non recontrôlées par Firefox ; aucun déploiement vérifié.";
  v1.addEventListener("click", () => { if (current !== "V1") window.location.assign(revisionUrl("V1")); });
  v2.addEventListener("click", () => { if (current !== "V2") window.location.assign(revisionUrl("V2")); });
  // A click on the button may collapse the page selection in Firefox;
  // snapshot it at pointerdown, then support keyboard activation at click.
  let selectedAtPointerDown = "";
  function pageSelection() {
    try {
      return String(window.getSelection()?.toString() || "");
    } catch (_) { return ""; }
  }
  ai.addEventListener("pointerdown", () => {
    selectedAtPointerDown = pageSelection();
  });
  ai.addEventListener("click", () => {
    promptBox.hidden=true;
    promptBox.value="";
    if (!consent.checked) {
      aiStatus.textContent="Confirmer d'abord que la ressource est publique ou fictive.";
      return;
    }
    const selected = (selectedAtPointerDown || pageSelection()).trim();
    selectedAtPointerDown="";
    if (selected.length > 2400 || selected.includes("\u0000")) {
      aiStatus.textContent="Sélection refusée (max. 2 400 caractères, sans NUL). Réduire la sélection.";
      return;
    }
    // This is DECLARED provenance carried by an untrusted URL parameter,
    // not an authenticated GitHub repository, current ref or deployment.
    const selectedContext = selected ?
      "Passage sélectionné (citation non vérifiée) :\n<<<PASSAGE\n" +
      selected + "\nPASSAGE>>>" :
      "Portée : ressource entière (aucun contenu HTML transmis).";
    // Only the publicly documented fictional demo has a proposed branch.
    // The URL cannot prove that ref exists, is current or is writable.
    const branchHint = payload.resource_id === "quarto:djibian/alliage:activite.qmd"
      ? "Branche de démonstration À VÉRIFIER : experiment/pareto-quarto-demo ; fichier activite.qmd."
      : "Branche de travail NON IDENTIFIÉE : la demander avant toute écriture.";
    promptBox.value = [
      "Alliage — demande pédagogique, ressource PUBLIQUE ou FICTIVE.",
      "Identité Git déclarée : " + payload.resource_id,
      branchHint,
      "Révision affichée : " + current + ", SHA Git indiqué : " + sha,
      "Ancienne révision indiquée : " + first.commit,
      "Nouvelle révision indiquée : " + second.commit,
      "Attention : ces informations d'URL ne sont pas authentifiées dans Firefox.",
      selectedContext,
      "Tu es le chatbot IA déjà ouvert dans le panneau latéral Firefox.",
      "Discute de la modification souhaitée. Avant toute écriture, demande",
      "une autorisation explicite de dépôt et de branche, vérifie ton accès réel",
      "à GitHub dans CETTE interface et respecte les règles du dépôt cible.",
      "Si tu ne peux pas écrire depuis cette interface, produis un patch",
      "ou une procédure GitHub explicite et n'annonce aucune modification faite.",
      "N'autorise aucune fusion, validation de publication ni modification élève.",
      "L'enseignant doit ensuite faire vérifier le rendu Quarto et choisir."
    ].join("\n");
    promptBox.hidden=false;
    aiStatus.textContent="Demande préparée localement. Sélectionner/copier le texte puis le coller dans le chatbot latéral. Aucun envoi automatique.";
    if (typeof promptBox.focus === "function") promptBox.focus();
    if (typeof promptBox.select === "function") promptBox.select();
  });
  // This is a reversible, browser-local preference only, NOT the Git
  // approval, edit, or publication of an educational resource.
  const decisionKey = "alliage.local-review.v0:" + first.commit + ":" + second.commit;
  function displayDecision(value) {
    decision.textContent = value === "KEEP"
      ? "V2 retenue dans ce navigateur, sans écriture Git ni publication."
      : value === "REJECT"
        ? "V2 écartée dans ce navigateur, sans écriture Git ni publication."
        : "Décision non prise ; aucun enregistrement Git ni publication.";
  }
  function markDecision(value) {
    try { window.sessionStorage?.setItem(decisionKey,value); } catch (_) { /* file: may forbid storage */ }
    displayDecision(value);
  }
  try { displayDecision(window.sessionStorage?.getItem(decisionKey)); } catch (_) { /* non persistent */ }
  keep.addEventListener("click", () => markDecision("KEEP"));
  reject.addEventListener("click", () => markDecision("REJECT"));
  row.append(title,v1,v2,ai,keep,reject);
  if (demoRefresh) {
    row.append(refresh);
    // The browser's page origin can access only this loopback port, not
    // arbitrary Git endpoints. No network request until a deliberate click.
    refresh.addEventListener("click", async () => {
      if (!refreshConsent.checked) {
        refreshStatus.textContent="Confirmer d’abord le fetch et le rendu de la ressource fictive.";
        return;
      }
      if (refresh.disabled) return;
      refresh.disabled=true;
      refreshStatus.textContent="Récupération Git volontaire et rendus Quarto en cours…";
      try {
        const endpoint = directory + "/_alliage/";
        const headers = {"X-Alliage-Intent":"user-click"};
        const options = {method:"GET",headers,cache:"no-store",
                         credentials:"omit",redirect:"error"};
        const capability = await window.fetch(endpoint+"refresh-capability",options);
        if (!capability.ok) throw new Error("Contrôle d'actualisation indisponible.");
        const ticket = await capability.json();
        if (!ticket || typeof ticket.token !== "string" ||
            !/^[A-Za-z0-9_-]{32,100}$/.test(ticket.token))
          throw new Error("Capacité locale invalide.");
        const resultResponse = await window.fetch(endpoint+"refresh",{
          method:"POST",cache:"no-store",credentials:"omit",redirect:"error",
          headers:{"X-Alliage-Intent":"user-click",
                   "X-Alliage-Refresh-Token":ticket.token}
        });
        if (!resultResponse.ok) throw new Error("Git/Quarto refusé, ancien aperçu conservé.");
        const result = await resultResponse.json();
        if (result.state === "unchanged") {
          refreshStatus.textContent="Aucune nouvelle révision : comparaison conservée.";
        } else if (result.state === "updated" && typeof result.url === "string") {
          const target = new URL(result.url);
          if (target.origin !== location.origin ||
              !/^\/alliage-local-[0-9a-f]{32}\/V2\/project\/_site\/activite\.html$/.test(target.pathname) ||
              !/^[?]alliage-history-v0=[^&]+$/.test(target.search))
            throw new Error("Nouvelle URL non autorisée.");
          refreshStatus.textContent="Deux rendus réels vérifiés : ouverture de V2…";
          window.location.assign(target.href);
        } else {
          throw new Error("Réponse d'actualisation inconnue.");
        }
      } catch (_) {
        refreshStatus.textContent="Actualisation indisponible ou refusée ; comparaison précédente conservée.";
      } finally {
        refresh.disabled=false;
        // The consent is explicit for each individual refresh.
        refreshConsent.checked=false;
      }
    });
  }
  box.append(row,decision,consentLabel,promptBox,aiStatus);
  if (demoRefresh) box.append(refreshConsentLabel,refreshStatus);
  box.append(note);
  shadow.append(style,box);
  document.documentElement.appendChild(host);
})();
