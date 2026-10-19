/* Pont privilégié Firefox/Chrome MV3 : aucune requête locale depuis la page HTML. */
const ext = typeof browser !== "undefined" ? browser : chrome;
const PAGE = "https://djibian.github.io/pedagogie/enseignements/tim/4e-3e/activites/3e/02-nommer-classer/activite.html";
const API = "http://127.0.0.1:8765";
ext.runtime.onMessage.addListener((message, sender) => {
  if (sender.tab?.url !== PAGE || !message || !["experiment", "decision"].includes(message.action)) {
    return Promise.resolve({status: "REFUSED", detail: "Page ou action non autorisée."});
  }
  const payload = message.payload;
  if (!payload || typeof payload !== "object" || typeof message.token !== "string") {
    return Promise.resolve({status: "REFUSED", detail: "Entrée manquante."});
  }
  const url = message.action === "experiment" ? "/api/experiment" : "/api/decision";
  return fetch(API + url, {
    method: "POST",
    headers: {"Content-Type": "application/json", "X-Pedagolab-Token": message.token},
    body: JSON.stringify(payload),
    cache: "no-store"
  }).then(async res => {
    const result = await res.json();
    return res.ok ? result : {status: "REFUSED", detail: result.detail || result.error || `HTTP ${res.status}`};
  }).catch(err => ({status: "REFUSED", detail: `Pont local inaccessible : ${String(err)}`}));
});
