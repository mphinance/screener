// panels.js - left rail customization. Collapsible sections and a draggable
// width handle, both persisted to localStorage. Mounts against the shell only,
// so it never touches the feature modules that render into each panel body.

const STORE_KEY = "neon.panelState";
const MIN_W = 200;
const MAX_W = 560;

function loadState() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (!raw) return { collapsed: [], width: null };
    const s = JSON.parse(raw);
    return { collapsed: Array.isArray(s.collapsed) ? s.collapsed : [], width: s.width || null };
  } catch (err) {
    return { collapsed: [], width: null };
  }
}

function saveState(state) {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(state));
  } catch (err) {
    // localStorage can be unavailable or full. A failed save is not fatal.
  }
}

window.Screener.registerModule("panels", () => {
  const rail = document.getElementById("left-rail");
  if (!rail) {
    console.warn("panels: #left-rail not found, skipping.");
    return;
  }

  const state = loadState();
  const collapsed = new Set(state.collapsed);

  // ---- Collapsible sections. The header text is the stable key.
  const sections = [...rail.querySelectorAll(".rail-section")];
  for (const section of sections) {
    const head = section.querySelector(".rail-head");
    const titleEl = section.querySelector(".rail-title");
    if (!head || !titleEl) continue;
    const key = titleEl.textContent.trim();

    // A chevron that rotates when collapsed.
    const chev = document.createElement("span");
    chev.className = "rail-chevron";
    chev.textContent = "▼"; // down triangle
    head.appendChild(chev);

    if (collapsed.has(key)) section.classList.add("collapsed");

    head.addEventListener("click", () => {
      const isCollapsed = section.classList.toggle("collapsed");
      if (isCollapsed) collapsed.add(key);
      else collapsed.delete(key);
      saveState({ collapsed: [...collapsed], width: currentWidth() });
    });
  }

  // ---- Resizable rail width via a fixed handle that tracks --rail-w.
  function currentWidth() {
    const v = getComputedStyle(document.documentElement).getPropertyValue("--rail-w").trim();
    const n = parseFloat(v);
    return Number.isFinite(n) ? n : null;
  }
  function setWidth(px) {
    const w = Math.max(MIN_W, Math.min(MAX_W, Math.round(px)));
    document.documentElement.style.setProperty("--rail-w", w + "px");
    return w;
  }

  if (state.width) setWidth(state.width);

  const handle = document.createElement("div");
  handle.id = "rail-resize";
  handle.title = "Drag to resize. Double click to reset.";
  document.getElementById("app").appendChild(handle);

  let dragging = false;

  function onMove(e) {
    if (!dragging) return;
    // Rail starts at the left edge, so the pointer x is the new width.
    setWidth(e.clientX);
    e.preventDefault();
  }
  function onUp() {
    if (!dragging) return;
    dragging = false;
    handle.classList.remove("dragging");
    document.body.classList.remove("rail-resizing");
    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("pointerup", onUp);
    saveState({ collapsed: [...collapsed], width: currentWidth() });
  }

  handle.addEventListener("pointerdown", (e) => {
    dragging = true;
    handle.classList.add("dragging");
    document.body.classList.add("rail-resizing");
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    e.preventDefault();
  });

  // Double click resets to the default rail width.
  handle.addEventListener("dblclick", () => {
    document.documentElement.style.removeProperty("--rail-w");
    saveState({ collapsed: [...collapsed], width: null });
  });
});
