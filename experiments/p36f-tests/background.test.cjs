// SPDX-License-Identifier: AGPL-3.0-or-later
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const Policy = require("../p36f-extension/policy.js");
const source=fs.readFileSync(path.join(__dirname,"../p36f-extension/background.js"),"utf8");
const fixed="http://127.0.0.1:18765/p36f-fiction/lesson.html";
function environment(permissions=true){
  const listeners={},calls=[],updates=[];
  const browser={
    runtime:{id:"test-lab@alliage.invalid",
      getURL(p){return "moz-extension://test/"+p;},
      onMessage:{addListener(f){listeners.message=f;}}},
    permissions:{async contains(){return permissions;}},
    webRequest:{onBeforeRequest:{
      addListener(f,filter,extras){listeners.veto=f;calls.push({filter,extras});},
      hasListener(f){return f===listeners.veto;}
    }},
    webNavigation:{onCommitted:{addListener(f){listeners.committed=f;}}},
    tabs:{onRemoved:{addListener(f){listeners.removed=f;}},
      async create({url}){ assert.equal(url,"about:blank");return {id:23}; },
      async update(id,{url}){updates.push({id,url});return {id,url};}}
  };
  vm.runInNewContext(source,{browser,P36FPolicy:Policy,
    crypto:{randomUUID(){return "generation-unique-001";}}}, {filename:"background.js"});
  const sender={id:browser.runtime.id,url:browser.runtime.getURL("control.html")};
  return {listeners,calls,updates,sender};
}
function req(overrides={}){
  return {tabId:23,type:"main_frame",frameId:0,method:"GET",url:fixed,...overrides};
}
test("top-level listener global, blocking and CLOSED before any handshake",()=>{
  const e=environment();
  assert.equal(e.calls.length,1);
  assert.deepEqual(JSON.parse(JSON.stringify(e.calls[0].filter)),{urls:["<all_urls>"]});
  assert.deepEqual(Array.from(e.calls[0].extras),["blocking"]);
  assert.deepEqual(JSON.parse(JSON.stringify(e.listeners.veto(req()))),{cancel:true});
});
test("spoofed message and missing permissions cannot arm",async()=>{
  const e=environment(false);
  assert.equal((await e.listeners.message({action:"OPEN_FICTION",port:18765},e.sender)).status,
    "NO_GO_PERMISSIONS_OR_LISTENER");
  assert.equal(e.listeners.veto(req()).cancel,true);
  const x=environment();
  const spoof={id:"evil",url:e.sender.url};
  assert.equal((await x.listeners.message({action:"OPEN_FICTION",port:18765},spoof)).status,
    "REFUSED");
  assert.equal(x.listeners.veto(req()).cancel,true);
});
test("one synthetic main GET, then every tab/reload/redirect denied",async()=>{
  const e=environment();
  const answer=await e.listeners.message({action:"OPEN_FICTION",port:18765},e.sender);
  assert.equal(answer.status,"OPEN_ATTEMPTED_FICTION_ONLY");
  assert.deepEqual(e.updates,[{id:23,url:fixed}]);
  assert.equal(e.listeners.veto(req()).cancel,false);
  assert.equal(e.listeners.veto(req()).cancel,true);
  assert.equal(e.listeners.veto(req({tabId:24,url:"http://127.0.0.1:18766/probe"})).cancel,true);
  assert.equal(e.listeners.veto(req({tabId:-1,type:"speculative"})).cancel,true);
  assert.equal(e.listeners.veto(req({type:"sub_frame"})).cancel,true);
  assert.equal(e.listeners.veto(req({url:"http://127.0.0.1:18766/probe"})).cancel,true);
});
test("navigation observation never silently allows requests",async()=>{
  const e=environment();
  await e.listeners.message({action:"OPEN_FICTION",port:18765},e.sender);
  e.listeners.committed({tabId:24,url:"http://127.0.0.1:18766/probe"});
  assert.equal(e.listeners.veto(req()).cancel,true);
  const snapshot=await e.listeners.message({action:"STATUS"},e.sender);
  assert.equal(snapshot.unexpectedCommits,1);
  assert.equal(snapshot.armed,false);
});
test("revocation by CLOSE and tab removed",async()=>{
  const e=environment();
  await e.listeners.message({action:"OPEN_FICTION",port:18765},e.sender);
  await e.listeners.message({action:"CLOSE"},e.sender);
  assert.equal(e.listeners.veto(req()).cancel,true);
  await e.listeners.message({action:"OPEN_FICTION",port:18765},e.sender);
  e.listeners.removed(23);
  assert.equal(e.listeners.veto(req()).cancel,true);
});
