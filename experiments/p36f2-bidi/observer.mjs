// SPDX-License-Identifier: AGPL-3.0-or-later
"use strict";
// P3.6F2: PASSIVE, fixture-only WebDriver BiDi observer.
// Run INSIDE an already attested offline VM. Never launch Firefox, change
// permissions, navigate, inject JavaScript or connect to a non-loopback host.
import { createInterface } from "node:readline";
import { pathToFileURL } from "node:url";

const A = "http://127.0.0.1:18765/p36f-fiction/lesson.html";
const B = "http://127.0.0.1:18766/probe";
const METHODS = new Set([
  "browsingContext.contextCreated",
  "browsingContext.contextDestroyed",
  "browsingContext.navigationStarted",
  "browsingContext.navigationCommitted",
  "browsingContext.navigationFailed",
  "browsingContext.navigationAborted"
]);

function classification(url) {
  if (url === A) return "A_FIXTURE";
  if (url === B) return "B_PROBE";
  return "OTHER_REDACTED";
}

export class FixtureNavigationEvidence {
  constructor(phase) {
    if (phase !== "G1" && phase !== "G2") throw new TypeError("phase G1/G2");
    this.phase = phase;
    this.contextIds = new Map();
    this.events = [];
    this.started = false;
    this.beforeClickBCommits = 0;
    this.sequence = 0;
    this.startedAt = 0;
  }
  contextLabel(raw) {
    if (typeof raw !== "string" || !raw) return "CONTEXT_UNKNOWN";
    if (!this.contextIds.has(raw)) {
      this.contextIds.set(raw, "CTX_" + (this.contextIds.size + 1));
    }
    return this.contextIds.get(raw);
  }
  armWindow() {
    if (this.started) throw new Error("Observation already armed");
    this.started = true;
    this.startedAt = performance.now();
  }
  observe(message) {
    if (!message || typeof message !== "object" || !METHODS.has(message.method)) {
      return null;
    }
    const p = message.params;
    if (!p || typeof p !== "object") return null;
    const destination = classification(p.url);
    const method = message.method;
    if (!this.started && destination === "B_PROBE" &&
        method === "browsingContext.navigationCommitted") {
      this.beforeClickBCommits += 1;
    }
    if (!this.started) return null;
    const event = Object.freeze({
      seq: ++this.sequence,
      elapsedMs: Math.max(0, Math.round(performance.now() - this.startedAt)),
      method: method.slice("browsingContext.".length),
      context: this.contextLabel(p.context),
      destination
    });
    this.events.push(event);
    return event;
  }
  summary({transportComplete, subscriptionConfirmed, initialFixturePresent}) {
    const bCommit = this.events.filter(e =>
      e.method === "navigationCommitted" && e.destination === "B_PROBE").length;
    const bStarted = this.events.filter(e =>
      e.method === "navigationStarted" && e.destination === "B_PROBE").length;
    return Object.freeze({
      kind: "F2_PASSIVE_NAVIGATION_OBSERVATION_ONLY",
      phase: this.phase,
      subscriptionConfirmed: subscriptionConfirmed === true,
      initialFixturePresent: initialFixturePresent === true,
      transportComplete: transportComplete === true,
      preWindowBCommits: this.beforeClickBCommits,
      observedBStarts: bStarted,
      observedBCommits: bCommit,
      eventCount: this.events.length,
      // A negative count is not proof until the G1 positive control
      // confirmed this observer is sensitive to B in the same Firefox.
      verdict: !transportComplete || !subscriptionConfirmed ||
        !initialFixturePresent || this.beforeClickBCommits !== 0
        ? "UNPROVEN_OBSERVER"
        : this.phase === "G1" && bCommit > 0
          ? "G1_B_COMMIT_OBSERVED"
          : this.phase === "G1"
            ? "G1_UNPROVEN_NO_B_COMMIT"
            : bCommit > 0 ? "G2_B_COMMIT_OBSERVED"
              : "G2_B_COMMIT_NOT_OBSERVED_UNPROVEN_WITHOUT_G1"
    });
  }
}

function parseArgs(args) {
  if (args.length !== 4 || args[0] !== "--phase" || args[2] !== "--port" ||
      !["G1", "G2"].includes(args[1]) || !/^\d{4,5}$/.test(args[3])) {
    throw new TypeError("Usage: node observer.mjs --phase G1|G2 --port 9222");
  }
  const port = Number(args[3]);
  if (!Number.isSafeInteger(port) || port < 1024 || port > 65535) {
    throw new TypeError("Invalid loopback WebDriver BiDi port");
  }
  return {phase:args[1],port};
}

export async function run(args, WebSocketImpl = globalThis.WebSocket) {
  const {phase,port} = parseArgs(args);
  if (typeof WebSocketImpl !== "function") {
    throw new Error("Node.js WebSocket unavailable; no fallback to network packages");
  }
  // Fixed host, fixed /session route; the caller cannot provide a remote URL.
  const ws = new WebSocketImpl("ws://127.0.0.1:" + port + "/session");
  const evidence = new FixtureNavigationEvidence(phase);
  const pending = new Map();
  let lastId = 0, broken = false, open = false, finished = false;
  const send = (method,params) => new Promise((resolve,reject) => {
    if (!open || broken) { reject(new Error("BiDi connection unavailable"));return; }
    const id = ++lastId;
    pending.set(id,{resolve,reject});
    ws.send(JSON.stringify({id,method,params}));
  });
  const startup = new Promise((resolve,reject) => {
    ws.addEventListener("open",() => {open=true;resolve();},{once:true});
    ws.addEventListener("error",() => {broken=true;reject(new Error("BiDi transport error"));});
  });
  ws.addEventListener("message",event => {
    try {
      const m=JSON.parse(event.data);
      if (typeof m.id === "number" && pending.has(m.id)) {
        const slot = pending.get(m.id);
        pending.delete(m.id);
        if (m.type === "error") slot.reject(new Error("BiDi command rejected"));
        else slot.resolve(m.result);
      } else if (m.type === "event") {
        const record=evidence.observe(m);
        if (record) process.stdout.write(JSON.stringify({event:record})+"\n");
      }
    } catch (_) {broken=true;}
  });
  ws.addEventListener("close",() => {
    open=false;
    if (!finished) broken=true;
    for(const job of pending.values()) job.reject(new Error("BiDi closed"));
    pending.clear();
  });
  try {
    await startup;
    await send("session.new",{});
    await send("session.subscribe",{
      events:[...METHODS]
    });
    const tree = await send("browsingContext.getTree",{});
    const contexts = tree?.contexts;
    const initialFixturePresent = Array.isArray(contexts) &&
      contexts.some(c => c.url === A);
    if (!initialFixturePresent) {
      throw new Error("No A fixture in BiDi context tree; observer NO_GO");
    }
    process.stdout.write(JSON.stringify({
      status:"READY_SUBSCRIBED_BIDI",phase,initialFixturePresent,
      instruction:"Press Enter, then click B ONCE in A within the next 15 s",
      // No raw URL, request ID, profile details or arbitrary browsing data.
    })+"\n");
    const rl=createInterface({input:process.stdin,output:process.stderr});
    try {
      await new Promise((resolve,reject) => {
        rl.question("Arm 15-second observation (Enter): ",()=>resolve());
        rl.once("close",()=>reject(new Error("Input closed before arming")));
      });
    } finally {rl.close();}
    evidence.armWindow();
    process.stdout.write(JSON.stringify({status:"OBSERVATION_WINDOW_STARTED",phase})+"\n");
    await new Promise(resolve=>setTimeout(resolve,15000));
    finished=true;
    const summary=evidence.summary({
      transportComplete:!broken && open,
      subscriptionConfirmed:true,
      initialFixturePresent
    });
    process.stdout.write(JSON.stringify({summary})+"\n");
    return summary;
  } finally {
    finished=true;
    try {ws.close();} catch (_) { /* already disconnected */ }
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  run(process.argv.slice(2)).catch(() => {
    process.stderr.write("UNPROVEN_OBSERVER: BiDi connection/coverage failed\n");
    process.exitCode=1;
  });
}
