// SPDX-License-Identifier: AGPL-3.0-or-later
"use strict";
const out = document.getElementById("result");
async function send(action) {
  try {
    const response = await browser.runtime.sendMessage({
      action,
      port:Number(document.getElementById("port").value),
      decoyPort:Number(document.getElementById("decoy-port").value)
    });
    out.textContent = JSON.stringify(response, null, 2);
  } catch (_) {
    out.textContent = "NO_GO : extension de laboratoire indisponible.";
  }
}
for (const [id,action] of [
  ["open","OPEN_FICTION"],["close","CLOSE"],["status","STATUS"]
]) {
  document.getElementById(id).addEventListener("click",() => send(action));
}
