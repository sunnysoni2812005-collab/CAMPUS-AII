let category = null;
let photoData = null;
const $ = (id) => document.getElementById(id);

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// restore saved student details
$("name").value = localStorage.getItem("cai_name") || "";
$("sid").value = localStorage.getItem("cai_sid") || "";
if ($("sid").value) { $("trackId").value = $("sid").value; loadTrack(); }

document.querySelectorAll(".cat").forEach((el) =>
  el.addEventListener("click", () => {
    document.querySelectorAll(".cat").forEach((x) => x.classList.remove("sel"));
    el.classList.add("sel");
    category = el.dataset.c;
  })
);

$("photo").addEventListener("change", (e) => {
  const f = e.target.files[0];
  if (!f) { photoData = null; $("preview").style.display = "none"; return; }
  if (f.size > 5 * 1024 * 1024) { alert("Photo must be under 5 MB"); e.target.value = ""; return; }
  const r = new FileReader();
  r.onload = () => { photoData = r.result; $("preview").src = photoData; $("preview").style.display = "block"; };
  r.readAsDataURL(f);
});

$("gps").addEventListener("click", () => {
  if (!navigator.geolocation) return alert("GPS not supported in this browser");
  $("gps").textContent = "Locating...";
  navigator.geolocation.getCurrentPosition(
    (p) => {
      const coords = `GPS ${p.coords.latitude.toFixed(5)}, ${p.coords.longitude.toFixed(5)}`;
      $("location").value = $("location").value ? `${$("location").value} (${coords})` : coords;
      $("gps").textContent = "📍 Use GPS";
    },
    () => { alert("Could not get location. Please type it."); $("gps").textContent = "📍 Use GPS"; }
  );
});

function show(el, cls, html) { el.innerHTML = `<div class="msg ${cls}">${html}</div>`; }

$("submit").addEventListener("click", async () => {
  const out = $("result");
  if (!category) return show(out, "err", "Please select a category.");
  const body = {
    category, photo: photoData,
    location: $("location").value.trim(),
    description: $("desc").value.trim(),
    student_name: $("name").value.trim(),
    student_id: $("sid").value.trim(),
  };
  $("submit").disabled = true;
  try {
    const r = await fetch("/api/complaints", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const d = await r.json();
    if (!r.ok) return show(out, "err", esc(d.error || "Something went wrong"));
    localStorage.setItem("cai_name", body.student_name);
    localStorage.setItem("cai_sid", body.student_id);
    show(out, "ok", `✅ Submitted! Ticket <b>${esc(d.ticket)}</b><br>Sent to: ${esc(d.assigned_to)}<br>AI priority: <b>${esc(d.priority)}</b><br><small>${esc(d.summary)}</small>`);
    $("desc").value = ""; $("photo").value = ""; $("preview").style.display = "none"; photoData = null;
    if (body.student_id) { $("trackId").value = body.student_id; loadTrack(); }
  } catch (e) {
    show(out, "err", "Server not reachable.");
  } finally {
    $("submit").disabled = false;
  }
});

function card(c) {
  const hist = (c.history || []).map((h) => `${esc(h.at)} - ${esc(h.status)}${h.note ? " (" + esc(h.note) + ")" : ""}`).join("<br>");
  return `<div class="item">
    <div class="top"><b>${esc(c.ticket)} · ${esc(c.category)}</b>
      <span><span class="badge p-${esc(c.priority)}">${esc(c.priority)}</span> <span class="badge s-${esc(c.status)}">${esc(c.status)}</span></span></div>
    <div>${esc(c.description)}</div>
    <div class="meta">📍 ${esc(c.location)} · ${esc(c.created_at)}</div>
    ${c.photo ? `<img src="/uploads/${esc(c.photo)}" alt="photo">` : ""}
    ${hist ? `<div class="hist">${hist}</div>` : ""}
  </div>`;
}

async function loadTrack() {
  const q = $("trackId").value.trim();
  const box = $("tracked");
  if (!q) return;
  try {
    if (/^CAI-/i.test(q)) {
      const r = await fetch("/api/track/" + encodeURIComponent(q.toUpperCase()));
      const d = await r.json();
      box.innerHTML = r.ok ? card(d) : `<div class="msg err">${esc(d.error)}</div>`;
    } else {
      const r = await fetch("/api/my-complaints?student_id=" + encodeURIComponent(q));
      const list = await r.json();
      if (!list.length) { box.innerHTML = `<div class="msg err">No complaints found.</div>`; return; }
      const full = await Promise.all(list.map((c) => fetch("/api/track/" + c.ticket).then((x) => x.json())));
      box.innerHTML = full.map(card).join("");
    }
  } catch (e) {
    box.innerHTML = `<div class="msg err">Server not reachable.</div>`;
  }
}
$("trackBtn").addEventListener("click", loadTrack);
