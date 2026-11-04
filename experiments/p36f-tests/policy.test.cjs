// SPDX-License-Identifier: AGPL-3.0-or-later
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const P = require("../p36f-extension/policy.js");
const good = P.fixtureURL(18765);
function sample(overrides={}) {
  return {tabId:12,type:"main_frame",method:"GET",frameId:0,url:good,...overrides};
}
function armed() {
  const p=P.createPolicy();
  p.newGeneration("test-generation-001");
  assert.equal(p.arm({tabId:12,url:good,generation:"test-generation-001",
    permissionConfirmed:true}),true);
  return p;
}
test("closed from creation and generation restart; no persistence",() => {
  const p=P.createPolicy();
  assert.deepEqual(p.decide(sample()),{cancel:true});
  p.newGeneration("test-generation-001");
  assert.deepEqual(p.decide(sample()),{cancel:true});
  assert.equal(p.arm({tabId:12,url:good,generation:"wrong",permissionConfirmed:true}),false);
  assert.equal(p.arm({tabId:12,url:good,generation:"test-generation-001",
    permissionConfirmed:false}),false);
  assert.deepEqual(p.decide(sample()),{cancel:true});
  assert.equal(p.arm({tabId:12,url:good,generation:"test-generation-001",
    permissionConfirmed:true}),true);
  p.newGeneration("test-generation-002");
  assert.deepEqual(p.decide(sample()),{cancel:true});
});
test("one exact main_frame GET consumes grant BEFORE second request",() => {
  const p=armed();
  assert.deepEqual(p.decide(sample()),{cancel:false});
  assert.deepEqual(p.decide(sample()),{cancel:true});
  assert.deepEqual(p.decide(sample({url:"http://127.0.0.1:18766/escape"})),{cancel:true});
  assert.equal(p.status().allowed,1);
});
test("global deny for all other tabs, speculative and ambiguous requests",() => {
  const cases=[
    {tabId:13},{tabId:-1},{tabId:undefined},{type:"sub_frame"},
    {type:"image"},{type:"speculative"},{type:undefined},{method:"POST"},
    {method:undefined},{frameId:1},{frameId:undefined},
    {url:"http://127.0.0.1:18766/p36f-fiction/lesson.html"},
    {url:"http://127.0.0.1:18765/other"},
    {url:"https://example.invalid/fiction"},{url:undefined}
  ];
  for(const c of cases){
    const p=armed();
    assert.deepEqual(p.decide(sample(c)),{cancel:true},JSON.stringify(c));
    assert.deepEqual(p.decide(sample()),{cancel:false},"denial must not consume grant");
  }
});
test("exceptions and malformed input always deny, never fail open",() => {
  const p=armed();
  for(const item of [null,undefined,false,0,"x",Object.create(null),
    {get type(){throw Error("boom");}}]){
    assert.deepEqual(p.decide(item),{cancel:true});
  }
  assert.deepEqual(p.decide(sample()),{cancel:false});
});
test("synthetic fixture URL validation forbids real/private HTML",() => {
  assert.equal(P.validFixtureURL(good),true);
  for(const input of [
    "https://127.0.0.1:18765/p36f-fiction/lesson.html",
    "http://localhost:18765/p36f-fiction/lesson.html",
    "http://127.0.0.1:18765/p36f-fiction/lesson.html?x=1",
    "http://127.0.0.1:18765/p36f-fiction/lesson.html#secret",
    "http://127.0.0.1:18765/p36f-fiction/../other.html",
    "http://127.0.0.1:18765/p36f-fiction/lesson.html/",
    "http://127.0.0.1:18765/enseignements/prive.html",
    "http://user:password@127.0.0.1:18765/p36f-fiction/lesson.html",
    "http://127.0.0.1:80/p36f-fiction/lesson.html",
    "http://127.0.0.1:18765/p36f-fiction/lesson.html?code=fiction"
  ]) assert.equal(P.validFixtureURL(input),false,input);
  for(const port of [0,80,65536,NaN,18765.3,"18765"]) {
    assert.throws(()=>P.fixtureURL(port));
  }
});
test("close revokes outstanding permission",()=>{
  const p=armed();
  p.close();
  assert.deepEqual(p.decide(sample()),{cancel:true});
});
