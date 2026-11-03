// SPDX-License-Identifier: AGPL-3.0-or-later
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const Policy = require("../p36f-extension/policy.js");
const source = fs.readFileSync(
  path.join(__dirname, "../p36f-extension/background.js"), "utf8");
const fixed = "http://127.0.0.1:18765/p36f-fiction/lesson.html";
const probe = "http://127.0.0.1:18766/probe";
const msg = {action:"OPEN_FICTION", port:18765, decoyPort:18766};

function deferred() {
  let resolve, reject;
  const promise = new Promise((r,j) => {resolve=r; reject=j;});
  return {promise, resolve, reject};
}
async function microtasks() {
  for(let i=0;i<18;i++) await Promise.resolve();
}

function environment(options={}) {
  const {permissionHook, createHook, updateHook} = options;
  const listeners={}, calls=[], updates=[], creations=[];
  let nextId=22;
  const browser={
    runtime:{id:"test-lab@alliage.invalid",
      getURL(p){return "moz-extension://test/"+p;},
      onMessage:{addListener(f){listeners.message=f;}}},
    permissions:{
      async contains() {
        return permissionHook ? await permissionHook() : options.permissions !== false;
      },
      onRemoved:{addListener(f){listeners.permissionRemoved=f;}}
    },
    webRequest:{onBeforeRequest:{
      addListener(f,filter,extras){listeners.veto=f;calls.push({filter,extras});},
      hasListener(f){return f===listeners.veto;}
    }},
    webNavigation:{onCommitted:{addListener(f){listeners.committed=f;}}},
    tabs:{onRemoved:{addListener(f){listeners.removed=f;}},
      async create({url}) {
        assert.equal(url,"about:blank");
        creations.push(url);
        if(createHook) await createHook();
        return {id:++nextId};
      },
      async update(id,{url}) {
        updates.push({id,url});
        if(updateHook) await updateHook();
        return {id,url};
      }
    }
  };
  vm.runInNewContext(source,{
    browser,P36FPolicy:Policy,
    crypto:{randomUUID(){return "generation-unique-001";}}
  },{filename:"background.js"});
  const sender={id:browser.runtime.id,url:browser.runtime.getURL("control.html")};
  const send=(action,other={})=>listeners.message({action,...other},sender);
  const open=(other={})=>listeners.message({...msg,...other},sender);
  const state=()=>send("STATUS");
  return {listeners,calls,updates,creations,sender,send,open,state};
}
function req(overrides={}) {
  return {tabId:23,type:"main_frame",frameId:0,method:"GET",url:fixed,...overrides};
}
test("listener is global, blocking, and CLOSED synchronously",() => {
  const e=environment();
  assert.equal(e.calls.length,1);
  assert.deepEqual(JSON.parse(JSON.stringify(e.calls[0].filter)),
    {urls:["<all_urls>"]});
  assert.deepEqual(Array.from(e.calls[0].extras),["blocking"]);
  assert.equal(e.listeners.veto(req()).cancel,true);
});
test("spoofed control or missing permissions cannot arm",async()=>{
  const e=environment({permissions:false});
  assert.equal((await e.open()).status,"NO_GO_PERMISSIONS_OR_LISTENER");
  assert.equal(e.listeners.veto(req()).cancel,true);
  const x=environment();
  assert.equal((await x.listeners.message(msg,{id:"evil",url:x.sender.url})).status,
    "REFUSED");
  assert.equal(x.listeners.veto(req()).cancel,true);
});
test("one synthetic GET, then all reload/new tabs/frames/other URLs denied",async()=>{
  const e=environment();
  assert.equal((await e.open()).status,"OPEN_ATTEMPTED_FICTION_ONLY");
  assert.deepEqual(e.updates,[{id:23,url:fixed}]);
  assert.equal(e.listeners.veto(req()).cancel,false);
  for(const variation of [
    {},{tabId:24,url:probe},{tabId:-1,type:"speculative"},
    {type:"sub_frame"},{url:probe},{method:"POST"}
  ]) assert.equal(e.listeners.veto(req(variation)).cancel,true);
});
test("unexpected navigation is observation, not a veto",async()=>{
  const e=environment();
  await e.open();
  e.listeners.committed({tabId:24,url:probe});
  assert.equal(e.listeners.veto(req()).cancel,true);
  const s=await e.state();
  assert.equal(s.unexpectedCommits,1);
  assert.equal(s.armed,false);
});
test("CLOSE and removed tab both revoke",async()=>{
  const e=environment();
  await e.open();
  assert.equal((await e.send("CLOSE")).status,"CLOSED");
  assert.equal(e.listeners.veto(req()).cancel,true);
  await e.open();
  e.listeners.removed(24);
  assert.equal(e.listeners.veto(req({tabId:24})).cancel,true);
});
test("targeted B denied counter is distinct from all other DENYs",async()=>{
  const e=environment();
  await e.open();
  e.listeners.veto(req({url:"http://127.0.0.1:19999/not-B"}));
  e.listeners.veto(req({url:probe,type:"image"}));
  e.listeners.veto(req({url:probe,tabId:24}));
  e.listeners.veto(req({url:probe,tabId:25,method:"POST"}));
  const s=await e.state();
  assert.equal(s.deniedHTTPB,2);
  assert.equal(s.deniedHTTPBNewTab,1);
  assert.ok(s.denied>=4);
  assert.equal(JSON.stringify(s).includes("127.0.0.1"),false);
  assert.equal(JSON.stringify(s).includes("/probe"),false);
});
test("wrong B port or same A/B port never arms",async()=>{
  const e=environment();
  assert.equal((await e.open({decoyPort:18765})).status,"NO_GO_DECOY_PORT");
  assert.equal((await e.open({decoyPort:0})).status,"NO_GO_INVALID_LOCAL_FIXTURE");
  assert.equal(e.listeners.veto(req()).cancel,true);
});
test("CLOSE revokes OPEN suspended at permissions.contains",async()=>{
  const gate=deferred();
  let called=0;
  const e=environment({permissionHook:()=>++called===1?gate.promise:true});
  const opening=e.open();
  await microtasks();
  assert.equal(called,1);
  assert.equal((await e.send("CLOSE")).status,"CLOSED");
  gate.resolve(true);
  assert.equal((await opening).status,"NO_GO_REVOKED");
  assert.equal(e.creations.length,0);
  assert.equal(e.listeners.veto(req()).cancel,true);
});
test("CLOSE revokes OPEN suspended at tabs.create",async()=>{
  const gate=deferred(); let called=0;
  const e=environment({createHook:()=>{called++;return gate.promise;}});
  const opening=e.open();
  await microtasks();
  assert.equal(called,1);
  await e.send("CLOSE");
  gate.resolve();
  assert.equal((await opening).status,"NO_GO_REVOKED");
  assert.equal(e.updates.length,0);
  assert.equal(e.listeners.veto(req()).cancel,true);
});
test("CLOSE revokes OPEN suspended at tabs.update",async()=>{
  const gate=deferred();
  const e=environment({updateHook:()=>gate.promise});
  const opening=e.open();
  await microtasks();
  assert.equal(e.updates.length,1);
  await e.send("CLOSE");
  gate.resolve();
  assert.equal((await opening).status,"NO_GO_REVOKED");
  assert.equal(e.listeners.veto(req()).cancel,true);
});
test("two concurrent OPENs: old continuation cannot overwrite new arm",async()=>{
  const gate=deferred();let count=0;
  const e=environment({permissionHook:()=>++count===1?gate.promise:true});
  const old=e.open();
  await microtasks();
  const fresh=e.open();
  assert.equal((await fresh).status,"OPEN_ATTEMPTED_FICTION_ONLY");
  gate.resolve(true);
  assert.equal((await old).status,"NO_GO_REVOKED");
  assert.equal(e.creations.length,1);
  assert.equal(e.listeners.veto(req()).cancel,false);
  assert.equal(e.listeners.veto(req()).cancel,true);
});
test("tab removed during pending update revokes the continuation",async()=>{
  const gate=deferred();
  const e=environment({updateHook:()=>gate.promise});
  const opening=e.open();
  await microtasks();
  assert.equal(e.updates.length,1);
  e.listeners.removed(23);
  gate.resolve();
  assert.equal((await opening).status,"NO_GO_REVOKED");
  assert.equal(e.listeners.veto(req()).cancel,true);
});
test("unexpected HTTP commit during pending update revokes OPEN",async()=>{
  const gate=deferred();
  const e=environment({updateHook:()=>gate.promise});
  const opening=e.open();
  await microtasks();
  e.listeners.committed({tabId:24,url:probe});
  gate.resolve();
  assert.equal((await opening).status,"NO_GO_REVOKED");
  assert.equal((await e.state()).unexpectedCommits,1);
  assert.equal(e.listeners.veto(req()).cancel,true);
});
test("permission removal revokes an OPEN even after successful check",async()=>{
  const gate=deferred();
  const e=environment({updateHook:()=>gate.promise});
  const opening=e.open();
  await microtasks();
  e.listeners.permissionRemoved({permissions:["webRequest"]});
  gate.resolve();
  assert.equal((await opening).status,"NO_GO_REVOKED");
  assert.equal((await e.state()).permissionFailure,true);
  assert.equal(e.listeners.veto(req()).cancel,true);
});
test("CLOSE during second permission recheck blocks arming",async()=>{
  const gate=deferred();let checks=0;
  const e=environment({permissionHook:()=>++checks===2?gate.promise:true});
  const opening=e.open();
  await microtasks();
  assert.equal(checks,2);
  assert.equal(e.updates.length,0);
  await e.send("CLOSE");
  gate.resolve(true);
  assert.equal((await opening).status,"NO_GO_REVOKED");
  assert.equal(e.listeners.veto(req()).cancel,true);
});
