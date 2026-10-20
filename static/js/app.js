// ---------- state ----------
const state = { status: "all", category: "all", priority: "all", sort: "newest", search: "" };
const $ = (id) => document.getElementById(id);

// ---------- API helper ----------
async function api(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (res.status === 401) { window.location.href = "/auth"; throw new Error("Logged out"); }
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => t.classList.remove("show"), 2200);
}

const esc = (s) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function formatDue(iso) {
  if (!iso) return "";
  const d = new Date(iso + "T00:00:00");
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const diff = Math.round((d - today) / 86400000);
  if (diff === 0) return "Due today";
  if (diff === 1) return "Due tomorrow";
  if (diff === -1) return "Due yesterday";
  return "Due " + d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: d.getFullYear() === today.getFullYear() ? undefined : "numeric" });
}

// ---------- rendering ----------
async function loadUser() {
  const u = await api("/api/me");
  $("user-name").textContent = u.name;
  $("user-email").textContent = u.email;
  const hour = new Date().getHours();
  const part = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  $("greeting").textContent = `${part}, ${u.name.split(" ")[0]}`;
}

async function loadStats() {
  const s = await api("/api/stats");
  $("percent").textContent = s.percent + "%";
  $("ring-fg").style.strokeDashoffset = 326.7 * (1 - s.percent / 100);
  $("progress-text").textContent = s.total ? `${s.completed} of ${s.total} tasks completed` : "No tasks yet";
  $("c-all").textContent = s.total;
  $("c-active").textContent = s.active;
  $("c-completed").textContent = s.completed;
  $("c-overdue").textContent = s.overdue;
  $("subhead").textContent = s.total === 0 ? "Add your first task to get started."
    : s.due_today ? `${s.due_today} due today, ${s.active} active in total.` : `${s.active} active ${s.active === 1 ? "task" : "tasks"}.`;

  // categories
  const nav = $("category-filters");
  nav.innerHTML = `<button data-cat="all" class="${state.category === "all" ? "active" : ""}">All categories</button>` +
    s.categories.map((c) => `<button data-cat="${esc(c)}" class="${state.category === c ? "active" : ""}">${esc(c)}</button>`).join("");
  $("category-list").innerHTML = s.categories.map((c) => `<option value="${esc(c)}">`).join("");
  if (state.category !== "all" && !s.categories.includes(state.category)) { state.category = "all"; loadTasks(); }
}

async function loadTasks() {
  const q = new URLSearchParams({ ...state });
  const tasks = await api("/api/tasks?" + q);
  const list = $("task-list");
  list.innerHTML = tasks.map(taskHTML).join("");

  const empty = $("empty");
  empty.hidden = tasks.length > 0;
  if (!tasks.length) {
    const filtering = state.search || state.status !== "all" || state.category !== "all" || state.priority !== "all";
    empty.innerHTML = filtering
      ? "<h3>No tasks match these filters</h3><p>Try clearing the search or choosing a different view.</p>"
      : "<h3>Nothing here yet</h3><p>Use <b>Add task</b> to write down your first one.</p>";
  }
}

function taskHTML(t) {
  const due = formatDue(t.due_date);
  return `
  <li class="task p-${t.priority} ${t.completed ? "done" : ""}" data-id="${t.id}">
    <input type="checkbox" class="check" ${t.completed ? "checked" : ""} aria-label="Mark ${esc(t.title)} as ${t.completed ? "not done" : "done"}">
    <div class="task-body">
      <div class="task-title">${esc(t.title)}</div>
      ${t.description ? `<div class="task-desc">${esc(t.description)}</div>` : ""}
      <div class="meta">
        <span class="chip">${esc(t.category)}</span>
        <span class="chip prio">${t.priority} priority</span>
        ${due ? `<span class="chip ${t.overdue ? "overdue" : ""}">${t.overdue ? "Overdue · " : ""}${due}</span>` : ""}
      </div>
    </div>
    <div class="task-actions">
      <button class="icon-btn edit" aria-label="Edit task">Edit</button>
      <button class="icon-btn delete" aria-label="Delete task">Delete</button>
    </div>
  </li>`;
}

const refresh = () => Promise.all([loadTasks(), loadStats()]);

// ---------- dialog ----------
const dialog = $("task-dialog");
const form = $("task-form");

function openDialog(task) {
  form.reset();
  $("form-error").hidden = true;
  $("dialog-title").textContent = task ? "Edit task" : "Add task";
  $("save-btn").textContent = task ? "Save changes" : "Add task";
  form.id.value = task ? task.id : "";
  if (task) {
    form.title.value = task.title;
    form.description.value = task.description;
    form.category.value = task.category;
    form.priority.value = task.priority;
    form.due_date.value = task.due_date || "";
  }
  dialog.showModal();
  form.title.focus();
}

$("new-task-btn").onclick = () => openDialog(null);
$("cancel-btn").onclick = () => dialog.close();
dialog.addEventListener("click", (e) => { if (e.target === dialog) dialog.close(); });

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    title: form.title.value, description: form.description.value,
    category: form.category.value, priority: form.priority.value, due_date: form.due_date.value,
  };
  const id = form.id.value;
  try {
    await api(id ? `/api/tasks/${id}` : "/api/tasks", { method: id ? "PUT" : "POST", body: payload });
    dialog.close();
    toast(id ? "Changes saved" : "Task added");
    refresh();
  } catch (err) {
    $("form-error").textContent = err.message;
    $("form-error").hidden = false;
  }
});

// ---------- list actions (event delegation) ----------
$("task-list").addEventListener("click", async (e) => {
  const li = e.target.closest(".task");
  if (!li) return;
  const id = li.dataset.id;
  try {
    if (e.target.matches(".check")) {
      const t = await api(`/api/tasks/${id}/toggle`, { method: "PATCH" });
      toast(t.completed ? "Marked as done" : "Marked as not done");
      refresh();
    } else if (e.target.matches(".delete")) {
      if (!confirm("Delete this task? This can't be undone.")) return;
      await api(`/api/tasks/${id}`, { method: "DELETE" });
      toast("Task deleted");
      refresh();
    } else if (e.target.matches(".edit")) {
      const tasks = await api("/api/tasks");
      openDialog(tasks.find((t) => String(t.id) === id));
    }
  } catch (err) { toast(err.message); }
});

// ---------- filters ----------
$("status-filters").addEventListener("click", (e) => {
  const b = e.target.closest("button"); if (!b) return;
  state.status = b.dataset.status;
  document.querySelectorAll("#status-filters button").forEach((x) => x.classList.toggle("active", x === b));
  loadTasks();
});
$("category-filters").addEventListener("click", (e) => {
  const b = e.target.closest("button"); if (!b) return;
  state.category = b.dataset.cat;
  document.querySelectorAll("#category-filters button").forEach((x) => x.classList.toggle("active", x === b));
  loadTasks();
});
$("priority-filter").onchange = (e) => { state.priority = e.target.value; loadTasks(); };
$("sort").onchange = (e) => { state.sort = e.target.value; loadTasks(); };
let searchTimer;
$("search").addEventListener("input", (e) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => { state.search = e.target.value.trim(); loadTasks(); }, 250);
});

$("clear-completed").onclick = async () => {
  if (!confirm("Delete all completed tasks?")) return;
  const r = await api("/api/tasks/completed", { method: "DELETE" });
  toast(r.deleted ? `Removed ${r.deleted} completed ${r.deleted === 1 ? "task" : "tasks"}` : "No completed tasks to remove");
  refresh();
};

$("logout-btn").onclick = async () => {
  await api("/api/logout", { method: "POST" });
  window.location.href = "/auth";
};

// ---------- start ----------
loadUser().then(refresh);
