// SPDX-License-Identifier: AGPL-3.0-or-later
"use strict";
// Synthetic BiDi records ONLY. No Firefox, no network, no actual profile.
import { test } from "node:test";
import assert from "node:assert/strict";
import { FixtureNavigationEvidence, parseArgs } from "./observer.mjs";

const A="http://127.0.0.1:18765/p36f-fiction/lesson.html";
const B="http://127.0.0.1:18766/probe";
const msg=(method,context,url)=>({
  type:"event",method:"browsingContext."+method,
  params:{context,url,navigation:"test-id-not-for-export"}
});
const good={transportComplete:true,subscriptionConfirmed:true,
  initialFixturePresent:true};

test("G1 positive control: only exact B commit counts",()=>{
  const o=new FixtureNavigationEvidence("G1");
  o.armWindow();
  o.observe(msg("navigationStarted","tab-real",B));
  const e=o.observe(msg("navigationCommitted","tab-real",B));
  assert.deepEqual(e.method,"navigationCommitted");
  assert.equal(e.context,"CTX_1");
  assert.equal(e.destination,"B_PROBE");
  assert.equal(o.summary(good).observedBCommits,1);
  assert.equal(o.summary(good).verdict,"G1_B_COMMIT_OBSERVED");
  assert.equal(JSON.stringify(o.events).includes(B),false);
  assert.equal(JSON.stringify(o.events).includes("tab-real"),false);
  assert.equal(JSON.stringify(o.events).includes("test-id-not-for-export"),false);
});
test("G1 refuses positive control based solely on navigationStarted",()=>{
  const o=new FixtureNavigationEvidence("G1");o.armWindow();
  o.observe(msg("navigationStarted","old-tab",B));
  assert.equal(o.summary(good).verdict,"G1_UNPROVEN_NO_B_COMMIT");
});
test("G2 silent stream remains UNPROVEN unless independent G1 established",()=>{
  const o=new FixtureNavigationEvidence("G2");o.armWindow();
  o.observe(msg("navigationStarted","a-tab",A));
  o.observe(msg("contextCreated","b-tab","about:blank"));
  assert.equal(o.summary(good).observedBCommits,0);
  assert.equal(o.summary(good).verdict,
    "G2_B_COMMIT_NOT_OBSERVED_UNPROVEN_WITHOUT_G1");
});
test("G2 B navigationCommitted is always recorded, even after failed state",()=>{
  const o=new FixtureNavigationEvidence("G2");o.armWindow();
  o.observe(msg("navigationFailed","a-tab",B));
  o.observe(msg("navigationCommitted","other-tab",B));
  assert.equal(o.summary(good).verdict,"G2_B_COMMIT_OBSERVED");
});
test("pre-window B commit disqualifies temporal attribution",()=>{
  const o=new FixtureNavigationEvidence("G2");
  o.observe(msg("navigationCommitted","stale-tab",B));
  o.armWindow();
  o.observe(msg("navigationStarted","a-tab",A));
  assert.equal(o.summary(good).preWindowBCommits,1);
  assert.equal(o.summary(good).verdict,"UNPROVEN_OBSERVER");
});
test("unexpected URLs including B with fragment do not become B fixture",()=>{
  const o=new FixtureNavigationEvidence("G1");o.armWindow();
  o.observe(msg("navigationCommitted","t",B+"?r=old"));
  o.observe(msg("navigationCommitted","t",B+"#fragment"));
  o.observe(msg("navigationCommitted","t","https://other.invalid/private?token=x"));
  assert.equal(o.summary(good).observedBCommits,0);
  assert.equal(o.events.every(e=>e.destination==="OTHER_REDACTED"),true);
  assert.equal(JSON.stringify(o.events).includes("other.invalid"),false);
});
test("closed or unconfirmed transport cannot justify any observer verdict",()=>{
  const o=new FixtureNavigationEvidence("G1");o.armWindow();
  o.observe(msg("navigationCommitted","t",B));
  for(const keys of [{transportComplete:false},{subscriptionConfirmed:false},
                     {initialFixturePresent:false}]){
    assert.equal(o.summary({...good,...keys}).verdict,"UNPROVEN_OBSERVER");
  }
});
test("arguments allow only a bounded local port and known phase",()=>{
  assert.deepEqual(parseArgs(["--phase","G1","--port","9222"]),
    {phase:"G1",port:9222});
  for(const args of [
    ["--phase","G3","--port","9222"],
    ["--phase","G1","--port","80"],
    ["--phase","G2","--port","65536"],
    ["--phase","G1","--port","9222;evil"],
    ["--phase","G2","--port","http://example.invalid"],
    ["--phase","G2","--port","9222","--target","https://evil.invalid"]
  ]) assert.throws(()=>parseArgs(args));
});
test("malformed events ignored and context IDs anonymized per run",()=>{
  const o=new FixtureNavigationEvidence("G1");o.armWindow();
  assert.equal(o.observe(null),null);
  assert.equal(o.observe({method:"privateUnknown",params:{url:B}}),null);
  assert.equal(o.observe({method:"browsingContext.navigationCommitted",
    params:null}),null);
  o.observe(msg("navigationCommitted","a",A));
  o.observe(msg("navigationCommitted","b",B));
  assert.equal(o.events[0].context,"CTX_1");
  assert.equal(o.events[1].context,"CTX_2");
});
