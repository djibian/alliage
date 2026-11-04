// SPDX-License-Identifier: AGPL-3.0-or-later
"use strict";
/* Firefox MV3 laboratory ONLY. Do not copy these privileges to extension/. */
const f1 = P36FPolicy.createPolicy();
const generation = crypto.randomUUID();
f1.newGeneration(generation);

// Every OPEN captures an epoch. CLOSE, another OPEN, a removed tab,
// a permission revocation or an unexpected commit invalidates ALL older
// asynchronous continuations, even across tabs.create/tabs.update.
let epoch = 0;
let tabForObservation = -1;
let allowedURL = null;
let probeURL = null; // Synthetic B /probe only: NEVER logged or exported.
let deniedHTTPB = 0;
// Attribution requires an observed target CREATED from the active A tab.
let deniedHTTPBLinkedTarget = 0;
let pendingCreateTicket = null;
const linkedTargets = new Set();
// Tombstones: a removed tab MUST NOT be relinked by a late navigation
// event in the same OPEN epoch. Cleared ONLY when the epoch changes.
const removedTargets = new Set();
let unexpectedCommits = 0;
let permissionFailure = false;

function revoke() {
  epoch += 1; // synchronous cancellation: the linearization point
  f1.close();
  pendingCreateTicket = null;
  linkedTargets.clear();
  removedTargets.clear();
  tabForObservation = -1;
  allowedURL = null;
  // Keep the fictitious B endpoint for counting denials AFTER CLOSE.
  // It is only a public loopback test URL and never returned by STATUS.
}
function current(ticket) { return ticket === epoch; }

// Register SYNCHRONOUSLY at event-page top-level, even when CLOSED.
// No tabId restriction: ALL intercepted requests from this profile are
// rejected except the one synthetic main_frame GET grant.
function veto(details) {
  try {
    const decision = f1.decide(details);
    // This is a *target-specific simulated-browser event* counter,
// NOT proof of Firefox interception. Never expose request URLs or IDs.
    if (decision.cancel === true && probeURL !== null && details &&
        details.url === probeURL && details.method === "GET") {
      deniedHTTPB += 1;
      // Do not mistake a pre-existing/stale tabId for a target created
      // by A in this attempt. A specific onCreatedNavigationTarget event
      // must link source A -> destination B in the current epoch.
      if (details.type === "main_frame" &&
          linkedTargets.has(details.tabId)) {
        linkedTargets.delete(details.tabId); // count once per observed target
        deniedHTTPBLinkedTarget += 1;
      }
    }
    return decision;
  } catch (_) {
    revoke();
    return {cancel: true};
  }
}
browser.webRequest.onBeforeRequest.addListener(
  veto, {urls: ["<all_urls>"]}, ["blocking"]
);

// Observation ONLY. This event can correlate a new target to A; it
// cannot block it, and may arrive too late for a particular request.
browser.webNavigation.onCreatedNavigationTarget.addListener(details => {
  if (details && probeURL !== null && tabForObservation >= 0 &&
      details.sourceTabId === tabForObservation &&
      details.sourceFrameId === 0 &&
      Number.isSafeInteger(details.tabId) && details.tabId >= 0 &&
      details.tabId !== tabForObservation && details.url === probeURL &&
      !removedTargets.has(details.tabId)) {
    linkedTargets.add(details.tabId);
  }
});
// Detection ONLY; webNavigation cannot veto a committed navigation.
browser.webNavigation.onCommitted.addListener(details => {
  if (details && Number.isInteger(details.tabId) &&
      /^https?:/i.test(details.url || "") &&
      (details.tabId !== tabForObservation || details.url !== allowedURL)) {
    unexpectedCommits += 1;
    revoke(); // cancels any suspended OPEN, not only an existing grant
  }
});
browser.tabs.onRemoved.addListener(tabId => {
  // During tabs.create(), the new tab's id is not yet known. A removal
  // event MAY be for that tab. Conservatively revoke *any* pending OPEN
  // rather than accept a closed tab after the Promise resolves.
  if (pendingCreateTicket !== null || tabId === tabForObservation) {
    revoke();
  } else if (Number.isSafeInteger(tabId) && tabId >= 0 &&
             tabForObservation >= 0) {
    // Record even a tab NOT YET linked: onRemoved may precede a late
    // onCreatedNavigationTarget. Never treat that event as a live target.
    removedTargets.add(tabId);
    linkedTargets.delete(tabId);
  }
});
browser.permissions.onRemoved.addListener(() => {
  permissionFailure = true;
  revoke();
});

// Extension pages only, not content scripts or arbitrary web pages.
function trustedControl(sender) {
  return sender && sender.id === browser.runtime.id &&
    sender.url === browser.runtime.getURL("control.html");
}
function snapshot() {
  const s = f1.status();
  return {status:"F1_UNIT_POLICY_ONLY",armed:s.armed,allowed:s.allowed,
    denied:s.denied,deniedHTTPB,deniedHTTPBLinkedTarget,
    unexpectedCommits,permissionFailure};
}
async function labPermissions() {
  try {
    return (await browser.permissions.contains({
      origins:["<all_urls>"],
      permissions:["webRequest","webRequestBlocking","tabs","webNavigation"]
    })) === true;
  } catch (_) { return false; }
}
function listenerReady() {
  try { return browser.webRequest.onBeforeRequest.hasListener(veto) === true; }
  catch (_) { return false; }
}
browser.runtime.onMessage.addListener(async (message,sender) => {
  if (!trustedControl(sender) || !message || typeof message !== "object") {
    return {status:"REFUSED"};
  }
  if (message.action === "STATUS") return snapshot();
  if (message.action === "CLOSE") {
    revoke();
    return {status:"CLOSED"};
  }
  if (message.action !== "OPEN_FICTION") return {status:"REFUSED"};

  // Linearize a fresh OPEN synchronously BEFORE its first await.
  revoke();
  const ticket = epoch;
  probeURL = null;
  deniedHTTPB = 0;
  deniedHTTPBLinkedTarget = 0;

  let url, decoyURL;
  try {
    const decoyPort = message.decoyPort === undefined
      ? 18766 : message.decoyPort;
    url = P36FPolicy.fixtureURL(message.port);
    P36FPolicy.fixtureURL(decoyPort); // validate decoy port via same contract
    if (decoyPort === message.port) {
      return {status:"NO_GO_DECOY_PORT"};
    }
    decoyURL = "http://127.0.0.1:" + decoyPort + "/probe";
  } catch (_) {
    return {status:"NO_GO_INVALID_LOCAL_FIXTURE"};
  }

  const permitted = await labPermissions();
  if (!current(ticket)) return {status:"NO_GO_REVOKED"};
  if (!permitted || !listenerReady()) {
    permissionFailure = true;
    revoke();
    return {status:"NO_GO_PERMISSIONS_OR_LISTENER"};
  }

  try {
    // Until tabs.create resolves, tab ID is unknown. An onRemoved during
    // this await must revoke the operation BEFORE it may arm that tab.
    pendingCreateTicket = ticket;
    const tab = await browser.tabs.create({url:"about:blank",active:true});
    if (pendingCreateTicket === ticket) pendingCreateTicket = null;
    if (!current(ticket)) return {status:"NO_GO_REVOKED"};
    if (!tab || !Number.isSafeInteger(tab.id) || tab.id < 0) {
      revoke();
      return {status:"NO_GO_ARMING"};
    }
    tabForObservation = tab.id;
    allowedURL = url;

    // Recheck permissions AFTER tabs.create, which may have yielded while
    // CLOSE/revocation raced. No grant exists during this second await.
    const stillPermitted = await labPermissions();
    if (!current(ticket)) return {status:"NO_GO_REVOKED"};
    if (!stillPermitted || !listenerReady()) {
      permissionFailure = true;
      revoke();
      return {status:"NO_GO_PERMISSIONS_OR_LISTENER"};
    }
    if (!f1.arm({tabId:tab.id,url,generation,
                 permissionConfirmed:stillPermitted})) {
      revoke();
      return {status:"NO_GO_ARMING"};
    }
    probeURL = decoyURL; // exact B /probe, no URL stored in any public log

    // This may yield while CLOSE, another OPEN or a tab event revokes us.
    await browser.tabs.update(tab.id,{url});
    if (!current(ticket)) return {status:"NO_GO_REVOKED"};
    return {...snapshot(),status:"OPEN_ATTEMPTED_FICTION_ONLY"};
  } catch (_) {
    if (!current(ticket)) return {status:"NO_GO_REVOKED"};
    revoke();
    return {status:"NO_GO_TAB_NAVIGATION"};
  }
});
