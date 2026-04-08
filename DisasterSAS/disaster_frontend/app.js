/* ================================================================
   DisasterSAS — Shared JavaScript
   Auth management, API helpers, RBAC, sidebar rendering, toast system
   ================================================================ */

const API_BASE = (() => {
  if (window.location.protocol === "file:") return "http://127.0.0.1:5000";
  if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
    return `${window.location.protocol}//${window.location.hostname}:5000`;
  }
  return window.location.origin;
})();

const UI_ICONS = {
  dashboard: '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="9"></rect><rect x="14" y="3" width="7" height="5"></rect><rect x="14" y="12" width="7" height="9"></rect><rect x="3" y="16" width="7" height="5"></rect></svg>',
  weather: '<svg viewBox="0 0 24 24"><path d="M20 16.5a4.5 4.5 0 0 0-1.1-8.87 6 6 0 0 0-11.36 2.5A3.8 3.8 0 0 0 8 18h10"></path><path d="M13 19l-2 3"></path><path d="M17 19l-2 3"></path></svg>',
  map: '<svg viewBox="0 0 24 24"><polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21 3 6"></polygon><line x1="9" y1="3" x2="9" y2="18"></line><line x1="15" y1="6" x2="15" y2="21"></line></svg>',
  alerts: '<svg viewBox="0 0 24 24"><path d="M10.3 3.4a2.4 2.4 0 0 1 3.4 0l.9.9a2 2 0 0 0 1.2.6l1.2.2a2.4 2.4 0 0 1 1.9 1.9l.2 1.2a2 2 0 0 0 .6 1.2l.9.9a2.4 2.4 0 0 1 0 3.4l-.9.9a2 2 0 0 0-.6 1.2l-.2 1.2a2.4 2.4 0 0 1-1.9 1.9l-1.2.2a2 2 0 0 0-1.2.6l-.9.9a2.4 2.4 0 0 1-3.4 0l-.9-.9a2 2 0 0 0-1.2-.6l-1.2-.2a2.4 2.4 0 0 1-1.9-1.9l-.2-1.2a2 2 0 0 0-.6-1.2l-.9-.9a2.4 2.4 0 0 1 0-3.4l.9-.9a2 2 0 0 0 .6-1.2l.2-1.2a2.4 2.4 0 0 1 1.9-1.9l1.2-.2a2 2 0 0 0 1.2-.6z"></path><line x1="12" y1="8" x2="12" y2="13"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>',
  shelters: '<svg viewBox="0 0 24 24"><path d="M3 11l9-7 9 7"></path><path d="M5 10v10h14V10"></path><path d="M9 20v-6h6v6"></path></svg>',
  survivors: '<svg viewBox="0 0 24 24"><circle cx="9" cy="8" r="3"></circle><path d="M4 20a5 5 0 0 1 10 0"></path><circle cx="17" cy="9" r="2.5"></circle><path d="M14.5 20a4 4 0 0 1 7 0"></path></svg>',
  missing: '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
  volunteers: '<svg viewBox="0 0 24 24"><path d="M7 12l3 3 7-7"></path><path d="M4 5h16v14H4z"></path></svg>',
  requests: '<svg viewBox="0 0 24 24"><path d="M12 3l9 16H3z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
  resources: '<svg viewBox="0 0 24 24"><path d="M3 7l9-4 9 4-9 4-9-4z"></path><path d="M3 7v10l9 4 9-4V7"></path><path d="M12 11v10"></path></svg>',
  emergency: '<svg viewBox="0 0 24 24"><path d="M22 16.9v3a2 2 0 0 1-2.2 2A19.8 19.8 0 0 1 11.2 19a19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.7.7 2.5a2 2 0 0 1-.5 2.1L8 9.6a16 16 0 0 0 6.4 6.4l1.3-1.3a2 2 0 0 1 2.1-.5c.8.3 1.6.6 2.5.7A2 2 0 0 1 22 16.9z"></path></svg>',
  user: '<svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"></circle><path d="M4 21a8 8 0 0 1 16 0"></path></svg>'
};

const ROLE_PERMISSION_FALLBACK = {
  public: [
    "dashboard:view",
    "weather:view",
    "map:view",
    "shelters:view",
    "missing:view",
    "emergency_contacts:view",
    "requests:create",
  ],
  volunteer: [
    "dashboard:view",
    "weather:view",
    "weather:forecast",
    "alerts:view",
    "shelters:view",
    "map:view",
    "emergency_contacts:view",
    "missing:report",
    "requests:create",
    "survivors:view",
    "survivors:manage",
    "missing:view",
    "missing:manage",
    "requests:view",
    "requests:manage",
    "requests:queue",
    "requests:stats",
    "volunteers:view",
    "resources:view",
  ],
  admin: ["*"],
};

const PAGE_ACCESS_RULES = [
  { href: "dashboard.html", allow: () => can("dashboard:view"), icon: UI_ICONS.dashboard, label: "Dashboard" },
  { href: "weather.html", allow: () => can("weather:view"), icon: UI_ICONS.weather, label: "Weather" },
  { href: "map.html", allow: () => can("map:view"), icon: UI_ICONS.map, label: "Live Map" },
  { href: "alerts.html", allow: () => can("alerts:view"), icon: UI_ICONS.alerts, label: "Alerts" },
  { href: "shelters.html", allow: () => can("shelters:view"), icon: UI_ICONS.shelters, label: "Shelters" },
  { href: "survivors.html", allow: () => can("survivors:view"), icon: UI_ICONS.survivors, label: "Survivors" },
  { href: "missing.html", allow: () => canAny(["missing:view", "missing:report"]), icon: UI_ICONS.missing, label: "Missing Persons" },
  { href: "volunteers.html", allow: () => can("volunteers:view"), icon: UI_ICONS.volunteers, label: "Volunteers" },
  { href: "requests.html", allow: () => canAny(["requests:view", "requests:create"]), icon: UI_ICONS.requests, label: "Emergency Requests" },
  { href: "resources.html", allow: () => can("resources:view"), icon: UI_ICONS.resources, label: "Resources" },
  { href: "emergency.html", allow: () => can("emergency_contacts:view"), icon: UI_ICONS.emergency, label: "Emergency Contacts" },
];
const PUBLIC_ALLOWED_PAGES = new Set(["dashboard.html"]);
const WEATHER_THEME_STORAGE_KEY = "weatherTheme";
const WEATHER_CONTEXT_STORAGE_KEY = "weatherThemeContext";

/* ── Auth Helpers ─────────────────────────────────────────────── */
function getToken() { return localStorage.getItem("token"); }
function getRole() { return localStorage.getItem("role") || "public"; }
function getUsername() { return localStorage.getItem("username") || ""; }

function normalizeRole(role) {
  const raw = String(role || "public").trim().toLowerCase();
  return ROLE_PERMISSION_FALLBACK[raw] ? raw : "public";
}

function parsePermissions(raw) {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw.map((p) => String(p)).filter(Boolean);
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.map((p) => String(p)).filter(Boolean);
  } catch (e) {
    return [];
  }
}

function getPermissions() {
  const fromStorage = parsePermissions(localStorage.getItem("permissions"));
  const role = normalizeRole(getRole());
  const fallback = ROLE_PERMISSION_FALLBACK[role] || ROLE_PERMISSION_FALLBACK.public;
  if (!fromStorage.length) return [...fallback];
  if (fallback.includes("*")) return [...new Set(fromStorage)];
  const allowed = new Set(fallback);
  return [...new Set([...fallback, ...fromStorage.filter((permission) => allowed.has(permission))])];
}

function setAuth(token, role, username, permissions = []) {
  const normalizedRole = normalizeRole(role);
  const resolvedPermissions = parsePermissions(permissions);
  localStorage.setItem("token", token);
  localStorage.setItem("role", normalizedRole);
  localStorage.setItem("username", username);
  localStorage.setItem(
    "permissions",
    JSON.stringify(resolvedPermissions.length ? resolvedPermissions : ROLE_PERMISSION_FALLBACK[normalizedRole] || [])
  );
}

function clearAuth() {
  localStorage.removeItem("token");
  localStorage.removeItem("role");
  localStorage.removeItem("username");
  localStorage.removeItem("permissions");
}

const DISASTER_SUPPORTED_CITIES = Object.freeze([
  { name: "Hyderabad", aliases: ["hyderabad", "hyd"], lat: 17.3850, lng: 78.4867 },
  { name: "Mumbai", aliases: ["mumbai", "bombay"], lat: 19.0760, lng: 72.8777 },
  { name: "Delhi", aliases: ["delhi"], lat: 28.6139, lng: 77.2090 },
  { name: "Bengaluru", aliases: ["bengaluru", "bangalore"], lat: 12.9716, lng: 77.5946 },
  { name: "Chennai", aliases: ["chennai", "madras"], lat: 13.0827, lng: 80.2707 },
  { name: "Kolkata", aliases: ["kolkata", "calcutta"], lat: 22.5726, lng: 88.3639 },
  { name: "Pune", aliases: ["pune"], lat: 18.5204, lng: 73.8567 },
  { name: "Ahmedabad", aliases: ["ahmedabad"], lat: 23.0225, lng: 72.5714 },
  { name: "Jaipur", aliases: ["jaipur"], lat: 26.9124, lng: 75.7873 },
  { name: "Lucknow", aliases: ["lucknow"], lat: 26.8467, lng: 80.9462 },
  { name: "Patna", aliases: ["patna"], lat: 25.5941, lng: 85.1376 },
  { name: "Bhubaneswar", aliases: ["bhubaneswar"], lat: 20.2961, lng: 85.8245 },
  { name: "Guwahati", aliases: ["guwahati"], lat: 26.1445, lng: 91.7362 },
  { name: "Kochi", aliases: ["kochi"], lat: 9.9312, lng: 76.2673 },
  { name: "Surat", aliases: ["surat"], lat: 21.1702, lng: 72.8311 }
]);

const DISASTER_LOCATION_ALIAS_LOOKUP = (() => {
  const lookup = new Map();
  for (const city of DISASTER_SUPPORTED_CITIES) {
    lookup.set(String(city.name).toLowerCase(), city);
    for (const alias of city.aliases || []) {
      lookup.set(String(alias).toLowerCase(), city);
    }
  }
  return lookup;
})();

function normalizeCityKey(value) {
  return String(value || "").trim().toLowerCase().replace(/\s+/g, " ");
}

function resolveSupportedCity(input) {
  const key = normalizeCityKey(input);
  if (!key) return null;

  const direct = DISASTER_LOCATION_ALIAS_LOOKUP.get(key);
  if (direct) return { name: direct.name, lat: direct.lat, lng: direct.lng };

  for (const city of DISASTER_SUPPORTED_CITIES) {
    const cityKey = String(city.name).toLowerCase();
    if (key === cityKey || key.includes(cityKey) || cityKey.includes(key)) {
      return { name: city.name, lat: city.lat, lng: city.lng };
    }
    for (const alias of city.aliases || []) {
      const aliasKey = String(alias).toLowerCase();
      if (key === aliasKey || key.includes(aliasKey) || aliasKey.includes(key)) {
        return { name: city.name, lat: city.lat, lng: city.lng };
      }
    }
  }

  return null;
}

function nearestSupportedCity(lat, lng) {
  const nextLat = Number(lat);
  const nextLng = Number(lng);
  if (!Number.isFinite(nextLat) || !Number.isFinite(nextLng) || !DISASTER_SUPPORTED_CITIES.length) return null;

  let closest = null;
  let closestScore = Number.POSITIVE_INFINITY;
  for (const city of DISASTER_SUPPORTED_CITIES) {
    const dLat = city.lat - nextLat;
    const dLng = city.lng - nextLng;
    const score = (dLat * dLat) + (dLng * dLng);
    if (score < closestScore) {
      closest = city;
      closestScore = score;
    }
  }
  return closest ? { name: closest.name, lat: closest.lat, lng: closest.lng } : null;
}

function requestPrecisePosition(options = {}) {
  const {
    timeout = 20000,
    maximumAge = 0,
    enableHighAccuracy = true
  } = options;

  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("Geolocation is not supported by your browser."));
      return;
    }

    navigator.geolocation.getCurrentPosition(resolve, reject, {
      enableHighAccuracy,
      timeout,
      maximumAge
    });
  });
}

function watchPrecisePosition(success, error, options = {}) {
  const {
    timeout = 20000,
    maximumAge = 0,
    enableHighAccuracy = true
  } = options;

  if (!navigator.geolocation) return null;
  return navigator.geolocation.watchPosition(success, error, {
    enableHighAccuracy,
    timeout,
    maximumAge
  });
}

function formatLocationAccuracy(accuracyMeters) {
  const value = Number(accuracyMeters);
  if (!Number.isFinite(value)) return "";
  return `GPS ±${Math.round(value)}m`;
}

function isLowLocationAccuracy(accuracyMeters, thresholdMeters = 3000) {
  const value = Number(accuracyMeters);
  return Number.isFinite(value) && value > thresholdMeters;
}

function createLookupGate() {
  let busy = false;
  return {
    begin() {
      if (busy) return false;
      busy = true;
      return true;
    },
    end() {
      busy = false;
    },
    isBusy() {
      return busy;
    }
  };
}

function populateCityDatalists() {
  const optionsHtml = DISASTER_SUPPORTED_CITIES
    .map((city) => `<option value="${city.name}"></option>`)
    .join("");

  document.querySelectorAll("[data-disaster-city-list]").forEach((list) => {
    list.innerHTML = optionsHtml;
  });
}

window.DisasterLocation = {
  supportedCities: DISASTER_SUPPORTED_CITIES,
  resolveCity: resolveSupportedCity,
  nearestCity: nearestSupportedCity,
  requestPrecisePosition,
  watchPrecisePosition,
  formatLocationAccuracy,
  isLowLocationAccuracy,
  createLookupGate,
  populateCityDatalists
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", populateCityDatalists, { once: true });
} else {
  populateCityDatalists();
}

function normalizeWeatherTheme(theme) {
  const key = String(theme || "clear").trim().toLowerCase();
  return ["clear", "cool", "hot", "rainy", "storm"].includes(key) ? key : "clear";
}

function getStoredWeatherTheme() {
  return normalizeWeatherTheme(localStorage.getItem(WEATHER_THEME_STORAGE_KEY));
}

function getStoredWeatherContext() {
  const raw = localStorage.getItem(WEATHER_CONTEXT_STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch (e) {
    return null;
  }
}

function applyWeatherThemeToShell(theme) {
  const normalized = normalizeWeatherTheme(theme);
  if (!document.body) return normalized;
  document.body.dataset.weatherTheme = normalized;
  document.body.classList.add("app-shell");
  return normalized;
}

function setWeatherTheme(theme, context = null) {
  const normalized = normalizeWeatherTheme(theme);
  localStorage.setItem(WEATHER_THEME_STORAGE_KEY, normalized);
  if (context && typeof context === "object" && Object.keys(context).length) {
    localStorage.setItem(WEATHER_CONTEXT_STORAGE_KEY, JSON.stringify(context));
  }
  return applyWeatherThemeToShell(normalized);
}

function applyStoredWeatherTheme() {
  return applyWeatherThemeToShell(getStoredWeatherTheme());
}

function can(permission) {
  const perms = getPermissions();
  return perms.includes("*") || perms.includes(permission);
}

function canAny(permissions) {
  return (permissions || []).some((permission) => can(permission));
}

function getDefaultPage() {
  const firstAllowed = PAGE_ACCESS_RULES.find((rule) => rule.allow());
  return firstAllowed ? firstAllowed.href : "dashboard.html";
}

function isAuthPage() {
  const file = (window.location.pathname.split("/").pop() || "").toLowerCase();
  return file === "index.html" || file === "register.html" || file === "forgot-password.html" || file === "";
}

function currentPageName() {
  return (window.location.pathname.split("/").pop() || "").toLowerCase();
}

function enforcePublicPageScope() {
  if (normalizeRole(getRole()) !== "public") return true;
  const page = currentPageName();
  if (!page || isAuthPage()) return true;
  if (PUBLIC_ALLOWED_PAGES.has(page)) return true;
  showToast("Limited Access", "Public access is focused on emergency dashboard only.");
  setTimeout(() => { window.location.href = "dashboard.html"; }, 400);
  return false;
}

function requireAuth() {
  if (!getToken()) {
    window.location.href = "index.html";
    return false;
  }
  return true;
}

function redirectToDefaultPage() {
  window.location.href = getDefaultPage();
}

function requirePagePermission(permission) {
  if (!requireAuth()) return false;
  if (!enforcePublicPageScope()) return false;
  if (!permission || can(permission)) return true;
  showToast("Access Denied", "You do not have permission to access this page.");
  redirectToDefaultPage();
  return false;
}

function requireAnyPagePermission(permissions) {
  if (!requireAuth()) return false;
  if (!enforcePublicPageScope()) return false;
  if (canAny(permissions)) return true;
  showToast("Access Denied", "You do not have permission to access this page.");
  redirectToDefaultPage();
  return false;
}

function logout() {
  clearAuth();
  window.location.href = "index.html";
}

function handleForbidden(errorMessage) {
  showToast("Access Denied", errorMessage || "You do not have permission for this action.");
  const currentPage = (window.location.pathname.split("/").pop() || "").toLowerCase();
  const fallback = getDefaultPage();
  if (currentPage !== fallback.toLowerCase()) {
    setTimeout(() => { window.location.href = fallback; }, 700);
  }
}

/* ── API Helpers ──────────────────────────────────────────────── */
async function api(endpoint, options = {}, behavior = {}) {
  const url = API_BASE + endpoint;
  const headers = { "Content-Type": "application/json", ...options.headers };

  const token = getToken();
  if (token) headers["Authorization"] = "Bearer " + token;

  let res;
  try {
    res = await fetch(url, { ...options, headers });
  } catch (networkErr) {
    throw { error: "Backend unreachable. Check that the Flask service is running." };
  }

  const contentType = res.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");

  let data = null;
  if (isJson) {
    data = await res.json();
  } else {
    const raw = await res.text();
    data = raw ? { error: raw.slice(0, 200) } : {};
  }

  if (!res.ok) {
    const message = data.error || data.message || `Request failed (${res.status})`;

    if (res.status === 401 && token && !behavior.silentUnauthorized) {
      clearAuth();
      if (!isAuthPage()) {
        setTimeout(() => { window.location.href = "index.html"; }, 300);
      }
    }

    if (res.status === 403 && !behavior.silentForbidden) {
      handleForbidden(message);
    }

    throw { status: res.status, error: message };
  }

  return data;
}

function apiGet(endpoint, behavior = {}) { return api(endpoint, {}, behavior); }
function apiPost(endpoint, body, behavior = {}) { return api(endpoint, { method: "POST", body: JSON.stringify(body) }, behavior); }
function apiPut(endpoint, body, behavior = {}) { return api(endpoint, { method: "PUT", body: JSON.stringify(body) }, behavior); }
function apiDelete(endpoint, behavior = {}) { return api(endpoint, { method: "DELETE" }, behavior); }

/* ── Sidebar Builder ──────────────────────────────────────────── */
function buildSidebar(activePage) {
  const pageKey = String(activePage || "").replace(/\.html$/i, "") || "dashboard";
  document.body.classList.add("app-shell");
  document.body.classList.add(`shell-page-${pageKey}`);
  document.body.dataset.shellPage = pageKey;
  applyStoredWeatherTheme();

  let links = PAGE_ACCESS_RULES.filter((rule) => rule.allow());
  if (normalizeRole(getRole()) === "public") {
    links = links.filter((rule) => PUBLIC_ALLOWED_PAGES.has(rule.href));
  }
  const nav = links.map((l) =>
    `<a href="${l.href}" class="${activePage === l.href ? "active" : ""}">
      <span class="icon">${l.icon}</span>${l.label}
    </a>`
  ).join("");

  const html = `
    <button class="hamburger" onclick="document.querySelector('.sidebar').classList.toggle('open')">☰</button>
    <aside class="sidebar">
      <div class="sidebar-brand"><span class="brand-mark">DS</span><span>DisasterSAS</span></div>
      <nav class="sidebar-nav">${nav}</nav>
      <div class="sidebar-footer">
        <div class="user-info">
          <span class="icon">${UI_ICONS.user}</span>
          <span>${getUsername() || "Guest"} <small>(${getRole()})</small></span>
        </div>
        <button class="logout-btn" onclick="logout()">Logout</button>
      </div>
    </aside>`;

  document.body.insertAdjacentHTML("afterbegin", html);
}

/* ── Toast System ─────────────────────────────────────────────── */
function initToasts() {
  if (!document.querySelector(".toast-container")) {
    document.body.insertAdjacentHTML("beforeend", '<div class="toast-container" id="toasts"></div>');
  }
}

function showToast(title, msg, duration = 5000) {
  initToasts();
  const container = document.getElementById("toasts");
  const el = document.createElement("div");
  el.className = "toast";
  el.innerHTML = `<div class="toast-title">${title}</div><div class="toast-msg">${msg}</div>`;
  container.appendChild(el);
  setTimeout(() => { el.style.opacity = "0"; setTimeout(() => el.remove(), 300); }, duration);
}

/* ── Badge Helper ─────────────────────────────────────────────── */
function severityBadge(level) {
  const cls = {
    critical: "badge-critical",
    high: "badge-high",
    medium: "badge-medium",
    low: "badge-low",
    open: "badge-open",
    full: "badge-full",
    closed: "badge-closed",
    missing: "badge-missing",
    found: "badge-found",
  }[level] || "badge-medium";
  return `<span class="badge ${cls}">${level}</span>`;
}

/* ── Modal Helper ─────────────────────────────────────────────── */
function openModal(id) {
  document.getElementById(id).classList.add("show");
}

function closeModal(id) {
  document.getElementById(id).classList.remove("show");
}

/* ── Socket.IO (optional; load local client script if needed) ─ */
function initSocket() {
  if (typeof io === "undefined") return null;
  const socket = io(API_BASE);

  socket.on("new_alert", (data) => {
    showToast("Disaster Alert", `${data.alert} in ${data.city} - Temp: ${data.temperature}°C`);
  });

  socket.on("forecast_alert", (data) => {
    showToast("Forecast Warning", `${data.city} - ${data.alerts.join(", ")} in ~${data.hours_ahead}h`);
  });

  return socket;
}

/* ── Format Date ──────────────────────────────────────────────── */
function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })
    + " " + d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

/* ── Responsive Table Cards ─────────────────────────────────── */
function enhanceResponsiveTables(scope = document) {
  const wraps = scope.querySelectorAll(".table-wrap");
  wraps.forEach((wrap) => {
    wrap.classList.add("mobile-cards");
    const table = wrap.querySelector("table");
    if (!table) return;

    const headers = Array.from(table.querySelectorAll("thead th")).map((th) =>
      (th.textContent || "").replace(/\s+/g, " ").trim()
    );

    const rows = table.querySelectorAll("tbody tr");
    rows.forEach((row) => {
      const cells = Array.from(row.children);
      cells.forEach((cell, idx) => {
        if (!(cell instanceof HTMLElement)) return;
        if (!cell.hasAttribute("data-label")) {
          const label = headers[idx] || `Field ${idx + 1}`;
          cell.setAttribute("data-label", label);
        }

        const label = (cell.getAttribute("data-label") || "").toLowerCase();
        const buttonCount = cell.querySelectorAll(".btn").length;
        const looksLikeActionsLabel = /action|operation|manage|controls?/.test(label);
        const isLastActionColumn = idx === cells.length - 1 && buttonCount >= 2;
        if (looksLikeActionsLabel || isLastActionColumn) {
          cell.classList.add("cell-actions");

          const directButtons = Array.from(cell.children).filter((child) =>
            child instanceof HTMLElement && child.classList.contains("btn")
          );
          if (directButtons.length && !cell.querySelector(":scope > .mobile-action-strip")) {
            const strip = document.createElement("div");
            strip.className = "mobile-action-strip";
            directButtons.forEach((btn) => strip.appendChild(btn));
            cell.appendChild(strip);
          }

          const knownGroups = cell.querySelectorAll(".shelter-actions, .direction-actions");
          knownGroups.forEach((group) => group.classList.add("mobile-action-strip"));
        }
      });
    });
  });
}

let tableEnhanceQueued = false;
function queueResponsiveTableEnhance() {
  if (tableEnhanceQueued) return;
  tableEnhanceQueued = true;
  requestAnimationFrame(() => {
    tableEnhanceQueued = false;
    enhanceResponsiveTables(document);
  });
}

function initResponsiveTableCards() {
  queueResponsiveTableEnhance();

  if (!document.body) return;
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.type !== "childList" || !mutation.addedNodes.length) continue;
      queueResponsiveTableEnhance();
      break;
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initResponsiveTableCards);
} else {
  initResponsiveTableCards();
}
