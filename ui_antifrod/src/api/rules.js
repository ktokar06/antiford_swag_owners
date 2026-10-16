import { apiFetch } from "./client";

export const rulesApi = {
    list() {
        return apiFetch("/api/rules");
    },
    upsert(items) {
        return apiFetch("/api/rules", { method: "PUT", body: { items } });
    },
    getPolicy() {
        return apiFetch("/api/policy");
    },
    updatePolicy(payload) {
        return apiFetch("/api/policy", { method: "PUT", body: payload });
    },
    rescore() {
        return apiFetch("/api/rescore", { method: "POST" });
    },
};
