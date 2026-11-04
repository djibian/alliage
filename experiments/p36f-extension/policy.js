// SPDX-License-Identifier: AGPL-3.0-or-later
"use strict";
// P3.6F1: pure, synchronous deny-by-default policy. FICTIONAL HTTP ONLY.
// No browser APIs, filesystem, network, storage, or external dependencies.
var P36FPolicy = (() => {
  const PATH = "/p36f-fiction/lesson.html";

  function fixtureURL(port) {
    if (!Number.isInteger(port) || port < 1024 || port > 65535) {
      throw new TypeError("Port de laboratoire invalide.");
    }
    return "http://127.0.0.1:" + port + PATH;
  }

  function validFixtureURL(url) {
    if (typeof url !== "string") return false;
    try {
      const u = new URL(url);
      return u.protocol === "http:" && u.hostname === "127.0.0.1" &&
        Number(u.port) >= 1024 && Number(u.port) <= 65535 &&
        u.pathname === PATH && u.search === "" && u.hash === "" &&
        u.username === "" && u.password === "" && u.href === url;
    } catch (_) { return false; }
  }

  function createPolicy() {
    // Initialized CLOSED on EVERY background event-page generation.
    let grant = null;
    let generation = null;
    let allowed = 0;
    let denied = 0;
    return Object.freeze({
      newGeneration(id) {
        grant = null;
        if (typeof id !== "string" || id.length < 16) {
          generation = null;
          throw new TypeError("Génération invalide.");
        }
        generation = id;
      },
      arm({tabId, url, generation: id, permissionConfirmed}) {
        grant = null;
        if (permissionConfirmed !== true || generation === null ||
            id !== generation || !Number.isSafeInteger(tabId) ||
            tabId < 0 || !validFixtureURL(url)) {
          return false;
        }
        grant = {tabId, url, generation};
        return true;
      },
      close() { grant = null; },
      decide(request) {
        // Do not log URL or content, NEVER call network from this callback.
        let ok = false;
        try {
          ok = grant !== null && grant.generation === generation &&
            request !== null && typeof request === "object" &&
            request.type === "main_frame" && request.method === "GET" &&
            request.frameId === 0 &&
            request.tabId === grant.tabId &&
            request.url === grant.url;
        } catch (_) {
          ok = false;
        }
        if (ok) {
          // One-time authorization is consumed BEFORE returning ALLOW.
          grant = null;
          allowed += 1;
          return {cancel: false};
        }
        denied += 1;
        return {cancel: true};
      },
      status() { return Object.freeze({armed: grant !== null, allowed, denied}); },
    });
  }

  return Object.freeze({createPolicy, fixtureURL, validFixtureURL});
})();
if (typeof module !== "undefined" && module.exports) {
  module.exports = P36FPolicy;
}
