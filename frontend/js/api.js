/* API layer — عيادة دكتورة طيبة */
const API = {
  base: "/api",

  getToken() {
    return localStorage.getItem("taiba_access");
  },

  getUser() {
    try {
      return JSON.parse(localStorage.getItem("taiba_user") || "null");
    } catch {
      return null;
    }
  },

  setSession({ access, refresh, user }) {
    if (access) localStorage.setItem("taiba_access", access);
    if (refresh) localStorage.setItem("taiba_refresh", refresh);
    if (user) localStorage.setItem("taiba_user", JSON.stringify(user));
  },

  clearSession() {
    localStorage.removeItem("taiba_access");
    localStorage.removeItem("taiba_refresh");
    localStorage.removeItem("taiba_user");
  },

  async request(path, options = {}) {
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    };
    const token = this.getToken();
    if (token) headers.Authorization = `Bearer ${token}`;

    const res = await fetch(`${this.base}${path}`, {
      ...options,
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });

    let data = null;
    const text = await res.text();
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = { detail: text };
      }
    }

    if (!res.ok) {
      const err = new Error(extractError(data) || "حدث خطأ");
      err.status = res.status;
      err.data = data;
      if (res.status === 401) {
        this.clearSession();
      }
      throw err;
    }
    return data;
  },

  get(path) {
    return this.request(path);
  },
  post(path, body) {
    return this.request(path, { method: "POST", body });
  },
  patch(path, body) {
    return this.request(path, { method: "PATCH", body });
  },
  del(path) {
    return this.request(path, { method: "DELETE" });
  },

  login(identifier, password) {
    return this.post("/auth/login/", { identifier, password });
  },
  register(payload) {
    return this.post("/auth/register/", payload);
  },
  me() {
    return this.get("/auth/me/");
  },
  info() {
    return this.get("/info/");
  },
};

function extractError(data) {
  if (!data) return "";
  if (typeof data === "string") return data;
  if (data.detail) {
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) return data.detail.map((x) => x.msg || x).join(" — ");
  }
  if (data.non_field_errors) return data.non_field_errors.join(" — ");
  const keys = Object.keys(data);
  if (keys.length) {
    const parts = keys.map((k) => {
      const v = data[k];
      if (Array.isArray(v)) return `${k}: ${v.join(", ")}`;
      if (typeof v === "object") return `${k}: ${JSON.stringify(v)}`;
      return `${k}: ${v}`;
    });
    return parts.join(" — ");
  }
  return "";
}

function $(sel, root = document) {
  return root.querySelector(sel);
}

function $$(sel, root = document) {
  return [...root.querySelectorAll(sel)];
}

function showAlert(el, message, type = "error") {
  if (!el) return;
  el.className = `alert ${type === "ok" ? "alert-ok" : type === "info" ? "" : "alert-error"}`;
  el.textContent = message;
  el.hidden = false;
}

function hideAlert(el) {
  if (el) el.hidden = true;
}

function requireRole(roles, loginPath) {
  const user = API.getUser();
  const token = API.getToken();
  if (!token || !user || !roles.includes(user.role)) {
    location.href = loginPath;
    return null;
  }
  return user;
}

function formatDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("ar-IQ", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function toLocalInputValue(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fromLocalInputValue(val) {
  if (!val) return null;
  return new Date(val).toISOString();
}

window.API = API;
window.$ = $;
window.$$ = $$;
window.showAlert = showAlert;
window.hideAlert = hideAlert;
window.requireRole = requireRole;
window.formatDateTime = formatDateTime;
window.toLocalInputValue = toLocalInputValue;
window.fromLocalInputValue = fromLocalInputValue;
