// SPDX-License-Identifier: AGPL-3.0-or-later
// Test Node.js sans navigateur ni dépendance externe : contrôles du DOM P3.2.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const source = fs.readFileSync(path.join(__dirname, "../extension/historique.js"), "utf8");
const base = "file:///home/fiction/alliage-experiences/historique/p31-final-demo/navigation.html";
const sha = n => n.toString(16).padStart(40, "0");
const payload = () => ({
  schema:"alliage.quarto-navigation.v0",
  reference_id:"V3",
  deployment_verified:false,
  reference_is_working_tree:false,
  verification:"POINT_IN_TIME_ONLY",
  entries:[1,2,3].map(n => ({
    id:"V"+n, commit:sha(n), quarto_version:"1.10.19",
    publication_status:"NOT_INITIATED_BY_ALLIAGE",
    html:"./V"+n+"/project/_site/activite.html"
  }))
});
class Element {
  constructor(tag) {
    this.tagName=tag;
    this.children=[];
    this.events={};
    this.style={};
    this.attributes={};
    this.textContent="";
    this.disabled=false;
    this.hidden=false;
    this.value="";
  }
  append(...items) { this.children.push(...items); }
  appendChild(element) { this.children.push(element); }
  attachShadow() { this.shadow=new Element("shadow"); return this.shadow; }
  setAttribute(key,value) { this.attributes[key]=value; }
  addEventListener(name,fn) { this.events[name]=fn; }
  emit(event) { if(this.events[event]) this.events[event](); }
}
function find(root,tag) {
  if(root.tagName===tag) return root;
  for(const node of [...root.children,...(root.shadow?[root.shadow]:[])]) {
    const found=find(node,tag);
    if(found) return found;
  }
  return null;
}
function findAll(root,tag) {
  const result=[];
  if(root.tagName===tag) result.push(root);
  for(const n of [...root.children,...(root.shadow?[root.shadow]:[])]) result.push(...findAll(n,tag));
  return result;
}
function run(data,href=base) {
  const nodes={
    "alliage-history-panel": null,
    "alliage-history-data":new Element("script"),
    "alliage-preview-frame":new Element("iframe"),
    "alliage-fallback":new Element("p")
  };
  nodes["alliage-history-data"].type="application/json";
  nodes["alliage-history-data"].textContent=JSON.stringify(data);
  nodes["alliage-preview-frame"].src="./V3/project/_site/activite.html";
  const document={
    documentElement:new Element("html"),
    getElementById:id => nodes[id]||null,
    createElement:tag=>new Element(tag)
  };
  const loc=new URL(href);
  vm.runInNewContext(source, {document,location:loc,URL,Set,Number,JSON,console}, {timeout:1000});
  const host=document.documentElement.children[0]||null;
  return {host,nodes,document};
}
test("navigation précédent/suivant et retour dans le même iframe, sans I/O",()=>{
  const result=run(payload());
  assert.ok(result.host);
  assert.equal(result.nodes["alliage-fallback"].hidden,true);
  const [prev,next,back]=findAll(result.host,"button");
  const select=find(result.host,"select");
  const frame=result.nodes["alliage-preview-frame"];
  assert.match(frame.src,/\/V3\/project\/_site\/activite\.html$/);
  assert.equal(next.disabled,true);
  assert.equal(back.disabled,true);
  select.value="V1";select.emit("change");
  assert.match(frame.src,/\/V1\/project\/_site\/activite\.html$/);
  assert.equal(prev.disabled,true);
  next.emit("click");
  assert.match(frame.src,/\/V2\/project\/_site\/activite\.html$/);
  back.emit("click");
  assert.match(frame.src,/\/V3\/project\/_site\/activite\.html$/);
  assert.equal(back.disabled,true);
});
test("métadonnées invalides ou chemin échappé : aucune interface injectée",()=>{
  const cases=[];
  const unverified=payload();unverified.deployment_verified=true;cases.push(unverified);
  const nonLocal=payload();nonLocal.entries[0].html="https://example.invalid/path";cases.push(nonLocal);
  const escape=payload();escape.entries[0].html="./V1/../../../../private/activite.html";cases.push(escape);
  const dups=payload();dups.entries[1].commit=dups.entries[0].commit;cases.push(dups);
  const wrongRef=payload();wrongRef.reference_id="V9";cases.push(wrongRef);
  for(const input of cases) {
    const {host,nodes}=run(input);
    assert.equal(host,null);
    assert.equal(nodes["alliage-fallback"].hidden,false);
  }
});
test("script non injecté sur une autre page locale",()=>{
  const result=run(payload(),"file:///home/fiction/Documents/navigation.html");
  assert.equal(result.host,null);
});
