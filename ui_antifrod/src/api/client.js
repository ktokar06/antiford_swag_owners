const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const TOKEN_KEY = "auth_token";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

export class ApiError extends Error {
    constructor(status, data) {
        super(data?.detail || data?.message || `HTTP ${status}`);
        this.status = status;
        this.data = data;
    }
}

export async function apiFetch(
    path,
    { method = "GET", body, headers = {}, ...rest } = {},
) {
    const token = getToken();
    const isForm = body instanceof FormData;
    const res = await fetch(`${BASE_URL}${path}`, {
        method,
        headers: {
            ...(isForm ? {} : { "Content-Type": "application/json" }),
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...headers,
        },
        body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
        ...rest,
    });

    if (res.status === 401 && !path.includes("/api/auth/login")) {
        clearToken();
        if (!window.location.pathname.startsWith("/login")) {
            window.location.href = "/login";
        }
        throw new ApiError(401, { detail: "Unauthorized" });
    }

    const text = await res.text();
    let data = null;
    try {
        data = text ? JSON.parse(text) : null;
    } catch {
        data = { detail: text.slice(0, 200) };
    }
    if (Array.isArray(data?.detail)) {
        data = { ...data, detail: data.detail.map((d) => d.msg).join("; ") };
    }
    if (!res.ok) throw new ApiError(res.status, data);
    return data;
}

export const buildQuery = (params = {}) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
        if (v === undefined || v === null || v === "") return;
        if (Array.isArray(v)) v.forEach((x) => q.append(k, x));
        else q.append(k, v);
    });
    const s = q.toString();
    return s ? `?${s}` : "";
};
