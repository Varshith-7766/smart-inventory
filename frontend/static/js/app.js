/* ===========================================================================
   SMART INVENTORY — Shared Dashboard JavaScript
   API client, auth, sidebar, theme, toast, utility functions
   =========================================================================== */

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
const API_BASE = "/api";

// ---------------------------------------------------------------------------
// CSRF token — fetched from API, stored for subsequent requests
// ---------------------------------------------------------------------------
let _csrfToken = "";

async function refreshCSRFToken() {
    try {
        const resp = await fetch("/api/auth/csrf-token", { credentials: "include" });
        const data = await resp.json();
        _csrfToken = data.csrf_token || "";
    } catch { _csrfToken = ""; }
}

function getCSRFToken() {
    return _csrfToken;
}

// ---------------------------------------------------------------------------
// Loading spinner overlay
// ---------------------------------------------------------------------------
let loaderCount = 0;

function showLoader() {
    loaderCount++;
    let el = document.getElementById("global-loader");
    if (!el) {
        el = document.createElement("div");
        el.id = "global-loader";
        el.innerHTML = '<div class="spinner"></div>';
        document.body.appendChild(el);
    }
    el.style.display = "flex";
}

function hideLoader() {
    loaderCount = Math.max(0, loaderCount - 1);
    const el = document.getElementById("global-loader");
    if (el && loaderCount === 0) el.style.display = "none";
}

// ---------------------------------------------------------------------------
// API Client — wraps fetch with CSRF token, loading spinners & error handling
// ---------------------------------------------------------------------------
const api = {
    async request(method, path, body = null) {
        const url = `${API_BASE}${path}`;
        const headers = { "Content-Type": "application/json" };
        const token = getCSRFToken();
        if (token) headers["X-CSRFToken"] = token;

        const options = {
            method,
            headers,
            credentials: "include",
        };
        if (body) options.body = JSON.stringify(body);

        showLoader();
        try {
            const res = await fetch(url, options);
            const data = await res.json().catch(() => ({}));

            if (res.status === 401) {
                // Session expired or not logged in — send the user to login.
                // Skip on the login/register pages themselves.
                const onAuthPage = /(login|register)\.html/.test(window.location.pathname);
                if (!onAuthPage) {
                    window.location.href = "/login.html";
                    return data;
                }
            }

            if (!res.ok) {
                throw new Error(data.error || `Request failed (${res.status})`);
            }
            return data;
        } finally {
            hideLoader();
        }
    },

    get(path)       { return this.request("GET", path); },
    post(path, b)   { return this.request("POST", path, b); },
    put(path, b)    { return this.request("PUT", path, b); },
    patch(path, b)  { return this.request("PATCH", path, b); },
    delete(path)    { return this.request("DELETE", path); },
};

// ---------------------------------------------------------------------------
// Toast notification system
// ---------------------------------------------------------------------------
function showToast(message, type = "info") {
    let toast = document.querySelector(".toast");
    if (!toast) {
        toast = document.createElement("div");
        toast.className = "toast";
        document.body.appendChild(toast);
    }

    const icons = { success: "check-circle", error: "x-circle", info: "info" };
    toast.className = `toast ${type}`;
    toast.innerHTML = `<i data-feather="${icons[type] || "info"}"></i><span>${message}</span>`;
    toast.classList.add("show");

    setTimeout(() => toast.classList.remove("show"), 3500);
}

// ---------------------------------------------------------------------------
// Theme toggle (light / dark)
// ---------------------------------------------------------------------------
function initTheme() {
    const saved = localStorage.getItem("theme") || "light";
    document.documentElement.setAttribute("data-theme", saved);

    const btn = document.getElementById("themeToggle");
    if (btn) {
        btn.innerHTML = saved === "dark"
            ? '<i data-feather="sun"></i>'
            : '<i data-feather="moon"></i>';
        btn.addEventListener("click", () => {
            const current = document.documentElement.getAttribute("data-theme");
            const next = current === "dark" ? "light" : "dark";
            document.documentElement.setAttribute("data-theme", next);
            localStorage.setItem("theme", next);
            btn.innerHTML = next === "dark"
                ? '<i data-feather="sun"></i>'
                : '<i data-feather="moon"></i>';
            if (typeof feather !== "undefined") feather.replace();
        });
    }
}

// ---------------------------------------------------------------------------
// Sidebar
// ---------------------------------------------------------------------------
function initSidebar() {
    const ham = document.getElementById("hamburger");
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");

    if (ham && sidebar) {
        ham.addEventListener("click", () => {
            sidebar.classList.toggle("open");
            if (overlay) overlay.classList.toggle("open");
        });
    }
    if (overlay) {
        overlay.addEventListener("click", () => {
            sidebar.classList.remove("open");
            overlay.classList.remove("open");
        });
    }
}

// ---------------------------------------------------------------------------
// Highlight active nav link
// ---------------------------------------------------------------------------
function setActiveNav(page) {
    document.querySelectorAll(".nav-item").forEach(el => {
        el.classList.toggle("active", el.dataset.page === page);
    });
}

// ---------------------------------------------------------------------------
// Modal helpers
// ---------------------------------------------------------------------------
function openModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add("open");
}

function closeModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove("open");
}

// Close modal on overlay click
document.addEventListener("click", (e) => {
    if (e.target.classList.contains("modal-overlay")) {
        e.target.classList.remove("open");
    }
});

// ---------------------------------------------------------------------------
// Format helpers
// ---------------------------------------------------------------------------
function currency(n) {
    return "$" + Number(n).toFixed(2);
}

// HTML-escape user-controlled values before interpolating them into innerHTML.
// Prevents stored XSS via product names, notes, device IDs, etc.
function esc(value) {
    if (value === null || value === undefined) return "";
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function dateStr(d) {
    if (!d) return "-";
    return new Date(d).toLocaleDateString("en-US", {
        year: "numeric", month: "short", day: "numeric",
    });
}

function dateTimeStr(d) {
    if (!d) return "-";
    return new Date(d).toLocaleString("en-US", {
        year: "numeric", month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit",
    });
}

// ---------------------------------------------------------------------------
// Feather icons auto-replace (called after dynamic content loads)
// ---------------------------------------------------------------------------
function refreshIcons() {
    if (typeof feather !== "undefined") feather.replace();
}

// ---------------------------------------------------------------------------
// Boot — runs on every page
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initSidebar();
    // Pre-fetch CSRF token so it's available for POST/PUT/DELETE
    refreshCSRFToken();
});
