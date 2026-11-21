"use strict";
const el = id => document.getElementById(id);
const labels = {eligible: "Eligible", review: "Needs review", gap: "Documented gap", invalid: "Invalid output",
  met: "Met", unknown: "Unknown", authority: "Authority", context: "Context switching", emotional: "Emotional appeal",
  output: "Output manipulation", benign: "Benign control"};
let catalog, active;
async function api(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Request failed.");
  return data;
}
function line(table, values) {
  const row = table.insertRow();
  for (const value of values) row.insertCell().textContent = value;
}
function render(run) {
  active = run.id;
  const c = run.case, d = run.decision;
  el("candidate").value = c.id;
  el("variant").value = String(run.selection.variant);
  el("source").value = run.selection.source;
  el("trace").hidden = false;
  el("name").textContent = c.name;
  el("family").textContent = run.selection.variant ? labels[c.family] : "Clean control";
  el("resume").textContent = c.resume + (run.selection.variant ? " " + c.variant : "");
  el("records").replaceChildren();
  const findings = Array.isArray(run.output?.findings) ? run.output.findings : [];
  for (const [key, name] of Object.entries(catalog.rubric)) {
    const record = c.records[key], proposed = findings.find(x => x?.criterion === key);
    line(el("records"), [name, record ? record.ref + " · " + labels[record.result] : "Missing",
      labels[proposed?.result] || "Unavailable"]);
  }
  el("baseline").textContent = labels[d.proposed];
  el("validated").textContent = labels[d.validated];
  el("reasons").textContent = d.reasons.join(" ") || "All three findings match the employer records.";
  el("state").textContent = run.approved_at ? "Shortlisted by the local reviewer · " + run.approved_at : "Shortlist decision pending reviewer approval.";
  el("review").hidden = !!run.approved_at || d.validated !== "eligible";
  el("raw").textContent = JSON.stringify(run,null,2);
  el("permalink").href = "?run=" + encodeURIComponent(run.id);
  el("status").textContent = run.provenance.model + " · " + (run.selection.source === "replay" ? "Illustrative model output" : "Live model output");
}
async function calculate() {
  el("status").textContent = "Assessing application…";
  el("trace").hidden = true;
  const button = el("setup").querySelector("button");
  button.disabled = true;
  try {
    const run = await api("/api/runs", {method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({candidate:el("candidate").value, variant:el("variant").value === "true",source:el("source").value})});
    render(run);
    history.replaceState(null, "", el("permalink").href);
  } catch(error) { el("status").textContent = error.message; }
  finally { button.disabled = false; }
}
el("setup").onsubmit = e => { e.preventDefault(); calculate(); };
el("approval").onsubmit = async e => {
  e.preventDefault();
  const id = active, key = el("key").value;
  el("key").value = "";
  try {
    const result = await api("/api/runs/" + id + "/approve",{method:"POST", headers:{Authorization:"Bearer " + key}});
    if(active === id) render(result);
  } catch(error) { el("status").textContent = error.message; }
};
async function init() {
  catalog = await api("/api/catalog");
  for (const c of catalog.cases) el("candidate").add(new Option(c.id + " · " + c.name,c.id));
  const t = catalog.report.totals;
  el("summary").textContent = t.completed_pairs + " clean/variant pairs. These fixed outputs measure the backend controls. Model susceptibility requires a separate live evaluation.";
  for (const family of ["authority","context","emotional","output"]) {
    const rows = catalog.report.cases.filter(r => r.family === family && r.observations.length === 2 && r.expected !== "eligible" && ["proposed","validated"].every(k => r.observations[0][k] === r.expected));
    const rate = k => rows.filter(r => r.observations[1][k] === "eligible").length + " / " + rows.length;
    line(el("metrics"),[labels[family],rate("proposed"),rate("validated")]);
  }
  el("utility").textContent = "Clean-case agreement after validation: " + t.clean_correct_after + " / " + t.completed_pairs +
    ". Changed benign outcomes: " + t.benign_validated_changes + " / " + t.benign_pairs + ". Extra referrals for review: " + t.excess_reviews + ".";
  const id = new URLSearchParams(location.search).get("run");
  if (id) render(await api("/api/runs/" + encodeURIComponent(id)));
  else await calculate();
}
init().catch(error => { el("status").textContent = error.message; });
