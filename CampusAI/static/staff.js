const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
let token = sessionStorage.getItem("cai_token");
let filter = "";

async function api(path, opts = {}) {
  const r = await fetch(path, {
    ...opts,
    headers: { "Content-Type": "application/json", Authorization: "Bearer " + token, ...(opts.headers || {}) },
  });
  if (r.status === 401 && token) { logout(); throw new Error("Session expired"); }
  return r;
}

function logout() {
  sessionStorage.clear(); token = null;
  $("dash").style.display = "none"; $("loginBox").style.display = "block"; $("logout").style.display = "none";
}
$("logout").addEventListener("click", (e) => { e.preventDefault(); logout(); });

$("loginBtn").addEventListener("click", async () => {
  const r = await fetch("/api/staff/login", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role: $("role").value, pin: $("pin").value }),
  });
  const d = await r.json();
  if (!r.ok) { $("loginMsg").innerHTML = `<div class="msg err">${esc(d.error)}</div>`; return; }
  token = d.token;
  sessionStorage.setItem("cai_token", token);
  sessionStorage.setItem("cai_who", `${d.name} - ${d.category} complaints`);
  $("pin").value = "";
  start();
});

function start() {
  $("loginBox").style.display = "none"; $("dash").style.display = "block"; $("logout").style.display = "inline";
  $("who").textContent = sessionStorage.getItem("cai_who") || "";
  refresh();
}

async function refresh() {
  try {
    const s = await (await api("/api/staff/stats")).json();
    $("stats").innerHTML = ["total", "pending", "in-progress", "resolved"]
      .map((k) => `<div class="stat"><b>${s[k] ?? 0}</b>${k}</div>`).join("");
    const list = await (await api("/api/staff/complaints" + (filter ? "?status=" + filter : ""))).json();
    $("list").innerHTML = list.length ? list.map(item).join("") : `<div class="card">No complaints here. 🎉</div>`;
  } catch (e) { /* logged out */ }
}

function item(c) {
  const btn = (s, label) => c.status === s ? "" : `<button class="ghost" onclick="setStatus(${c.id},'${s}')">${label}</button>`;
  return `<div class="item">
    <div class="top"><b>${esc(c.ticket)} · ${esc(c.category)}</b>
      <span><span class="badge p-${esc(c.priority)}">${esc(c.priority)}</span> <span class="badge s-${esc(c.status)}">${esc(c.status)}</span></span></div>
    <div>${esc(c.description)}</div>
    <div class="meta">📍 ${esc(c.location)} · 👤 ${esc(c.student_name) || "Anonymous"} ${c.student_id ? "(" + esc(c.student_id) + ")" : ""} · ${esc(c.created_at)}</div>
    <div class="ai">🤖 <b>AI:</b> ${esc(c.ai_summary)}
      ${c.ai_tags.length ? "<br>Tags: " + c.ai_tags.map(esc).join(", ") : ""}
      ${c.ai_suggested_category && c.ai_suggested_category !== c.category ? `<br>⚠️ AI thinks this may be <b>${esc(c.ai_suggested_category)}</b>` : ""}</div>
    ${c.photo ? `<a href="/uploads/${esc(c.photo)}" target="_blank"><img src="/uploads/${esc(c.photo)}" alt="photo"></a>` : ""}
    <div class="actions">
      <input id="note${c.id}" placeholder="Optional note for student">
      ${btn("pending", "Mark pending")}${btn("in-progress", "Start work")}${btn("resolved", "Mark resolved")}
    </div>
  </div>`;
}

window.setStatus = async (id, status) => {
  const note = $("note" + id).value.trim();
  const r = await api("/api/staff/complaints/" + id, { method: "PATCH", body: JSON.stringify({ status, note }) });
  if (!r.ok) alert((await r.json()).error);
  refresh();
};

$("tabs").addEventListener("click", (e) => {
  if (e.target.tagName !== "BUTTON") return;
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.remove("on"));
  e.target.classList.add("on");
  filter = e.target.dataset.s;
  refresh();
});

setInterval(() => token && refresh(), 15000);
if (token) start();
