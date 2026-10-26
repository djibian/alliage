// SPDX-License-Identifier: AGPL-3.0-or-later
// P3.4 proof-of-interface: DOM behavior only, not a graphical Firefox test.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../extension/historique_ressource.js"), "utf8");
const sha = n => String(n).padStart(40, "0");
const session = "file:///home/fiction/alliage-experiences/historique/p31-final-observed-demo";
const payload = () => ({
  schema:"alliage.quarto-resource-history.v0",
  resource_id:"quarto:fiction/laboratoire:activite.qmd",
  reference_id:"V1", observed_id:"V2",
  entries:[{id:"V1",commit:sha(1)},{id:"V2",commit:sha(2)}],
  verification:"POINT_IN_TIME_ONLY",
  deployment_verified:false, publication_performed:false
});
const href = (p=payload(),revision="V2") =>
  session+"/"+revision+"/project/_site/activite.html?alliage-history-v0="+
  encodeURIComponent(JSON.stringify(p));

class Element {
  constructor(tag) {
    this.tagName=tag;
    this.children=[];
    this.events={};
    this.style={};
    this.attributes={};
    this.textContent="";
    this.disabled=false;
  }
  append(...items) {this.children.push(...items);}
  appendChild(node) {this.children.push(node);}
  attachShadow() {this.shadow=new Element("shadow");return this.shadow;}
  setAttribute(key,value) {this.attributes[key]=value;}
  addEventListener(event,callback) {this.events[event]=callback;}
  emit(event) {if(this.events[event]) this.events[event]();}
}
function findAll(node,tag) {
  let nodes=node.tagName===tag?[node]:[];
  for(const child of [...node.children,...(node.shadow?[node.shadow]:[])]) {
    nodes.push(...findAll(child,tag));
  }
  return nodes;
}
function run(url,iframe=false) {
  const location=new URL(url);
  const navigations=[];
  const document={
    documentElement:new Element("html"),
    getElementById:()=>null,
    createElement:tag=>new Element(tag)
  };
  const window={location:{assign:url=>navigations.push(url)}};
  window.self=window;
  window.top=iframe?{}:window;
  vm.runInNewContext(source,{location,window,document,URL,URLSearchParams,JSON,Array},{timeout:1000});
  return {host:document.documentElement.children[0]||null,navigations};
}

test("V2 historical Quarto resource opens directly; V1 → V2 keeps same session",()=>{
  const first=run(href());
  assert.ok(first.host,"native resource toolbar should be injected");
  const buttons=findAll(first.host,"button");
  assert.equal(buttons.length,2);
  assert.equal(buttons[0].disabled,false);
  assert.equal(buttons[1].disabled,true);
  assert.match(findAll(first.host,"div").slice(-1)[0].textContent,/non recontrôlées/);
  buttons[0].emit("click");
  assert.equal(first.navigations.length,1);
  assert.match(first.navigations[0],/\/V1\/project\/_site\/activite\.html\?/);
  assert.equal(new URL(first.navigations[0]).search,new URL(href()).search);
  const second=run(first.navigations[0]);
  assert.ok(second.host);
  const back=findAll(second.host,"button");
  assert.equal(back[0].disabled,true);
  assert.equal(back[1].disabled,false);
  back[1].emit("click");
  assert.match(second.navigations[0],/\/V2\/project\/_site\/activite\.html\?/);
  assert.equal(new URL(second.navigations[0]).origin,"null"); // file: opaque origin
});

test("Quarto heading anchors survive history navigation",()=>{
  const current=run(href()+"#consigne");
  assert.ok(current.host);
  findAll(current.host,"button")[0].emit("click");
  assert.equal(current.navigations.length,1);
  const next=new URL(current.navigations[0]);
  assert.equal(next.hash,"#consigne");
  assert.equal(next.search,new URL(href()).search);
  assert.ok(run(next.href).host);
});

test("forged provenance, wrong page and absent explicit query inject nothing",()=>{
  const cases=[
    href().split("?")[0],
    "https://example.invalid/activite.html?alliage-history-v0="+encodeURIComponent(JSON.stringify(payload())),
    "file:///home/fiction/Documents/activite.html?alliage-history-v0="+encodeURIComponent(JSON.stringify(payload())),
    href({...payload(),deployment_verified:true}),
    href({...payload(),publication_performed:true}),
    href({...payload(),verification:"DEPLOYED"}),
    href({...payload(),resource_id:"quarto:../../private:activite.qmd"}),
    href({...payload(),entries:[{id:"V1",commit:sha(1)},{id:"V2",commit:sha(1)}]}),
    href({...payload(),entries:[{id:"V1",commit:sha(1)},{id:"V3",commit:sha(3)}]}),
    href()+"&file=../../private",
    href(payload(),"V3")
  ];
  for(const candidate of cases) {
    assert.equal(run(candidate).host,null,candidate.slice(0,100));
  }
  assert.equal(run(href(),true).host,null,"no iframe injection");
});

test("untrusted query metadata cannot give a custom navigation path",()=>{
  const malicious={...payload(),entries:[
    {id:"V1",commit:sha(1),html:"https://evil.example/private"},
    {id:"V2",commit:sha(2),html:"file:///etc/passwd"}
  ]};
  const result=run(href(malicious));
  assert.ok(result.host);
  findAll(result.host,"button")[0].emit("click");
  assert.equal(result.navigations.length,1);
  assert.ok(result.navigations[0].startsWith(session+"/V1/project/_site/activite.html?"));
  assert.ok(!result.navigations[0].includes("evil.example/private"));
});
