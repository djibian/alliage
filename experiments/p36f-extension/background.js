// SPDX-License-Identifier: AGPL-3.0-or-later
"use strict";
/* Firefox MV3 laboratory ONLY. Do not copy these privileges to extension/. */
const f1 = P36FPolicy.createPolicy();
const generation = crypto.randomUUID();
f1.newGeneration(generation);
let tabForObservation = -1;
let allowedURL = null;
let unexpectedCommits = 0;
let permissionFailure = false;

// Register SYNCHRONOUSLY at event-page top-level, even when CLOSED.
// No tabId restriction: ALL intercepted requests from this profile are
// rejected except the single synthetic main_frame GET grant.
function veto(details) {
  try { return f1.decide(details); }
  catch (_) { f1.close(); return {cancel: true}; }
}
browser.webRequest.onBeforeRequest.addListener(
  veto, {urls: ["<all_urls>"]}, ["blocking"]
);

// Detection ONLY; not a navigation veto and never a claim of confinement.
browser.webNavigation.onCommitted.addListener(details => {
  if (details && Number.isInteger(details.tabId) &&
      /^https?:/i.test(details.url || "") &&
      (details.tabId !== tabForObservation || details.url !== allowedURL)) {
    unexpectedCommits += 1;
    f1.close();
  }
});
browser.tabs.onRemoved.addListener(tabId => {
  if (tabId === tabForObservation) {
    f1.close();
    tabForObservation = -1;
    allowedURL = null;
  }
});
// Extension pages only, not content scripts or arbitrary web pages.
function trustedControl(sender) {
  return sender && sender.id === browser.runtime.id &&
    sender.url === browser.runtime.getURL("control.html");
}
function snapshot() {
  const s = f1.status();
  return {status:"F1_UNIT_POLICY_ONLY",armed:s.armed,allowed:s.allowed,
    denied:s.denied,unexpectedCommits,permissionFailure};
}
async function labPermissions() {
  try {
    return (await browser.permissions.contains({
      origins:["<all_urls>"],
      permissions:["webRequest","webRequestBlocking","tabs","webNavigation"]
    })) === true;
  } catch (_) { return false; }
}
browser.runtime.onMessage.addListener(async (message,sender) => {
  if (!trustedControl(sender) || !message || typeof message !== "object") {
    return {status:"REFUSED"};
  }
  if (message.action === "STATUS") {
    return snapshot();
  }
  if (message.action === "CLOSE") {
    f1.close();
    return {status:"CLOSED"};
  }
  if (message.action !== "OPEN_FICTION") return {status:"REFUSED"};
  f1.close();
  const permitted = await labPermissions();
  if (!permitted || !browser.webRequest.onBeforeRequest.hasListener(veto)) {
    permissionFailure = true;
    return {status:"NO_GO_PERMISSIONS_OR_LISTENER"};
  }
  try {
    const url = P36FPolicy.fixtureURL(message.port);
    // Neutral tab first, then its tabId binds the SINGLE-use exception.
    const tab = await browser.tabs.create({url:"about:blank",active:true});
    if (!tab || !Number.isSafeInteger(tab.id) || tab.id < 0 ||
        !f1.arm({tabId:tab.id,url,generation,permissionConfirmed:permitted})) {
      f1.close();
      return {status:"NO_GO_ARMING"};
    }
    tabForObservation = tab.id;
    allowedURL = url;
    try {
      await browser.tabs.update(tab.id,{url});
      return {...snapshot(),status:"OPEN_ATTEMPTED_FICTION_ONLY"};
    } catch (_) {
      f1.close();
      return {status:"NO_GO_TAB_NAVIGATION"};
    }
  } catch (_) {
    f1.close();
    return {status:"NO_GO_INVALID_LOCAL_FIXTURE"};
  }
});
