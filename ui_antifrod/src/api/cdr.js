import { apiFetch, buildQuery } from "./client";

export const cdrApi = {
    files(params) {
        return apiFetch(`/api/cdr/files${buildQuery(params)}`);
    },
    valid(params) {
        return apiFetch(`/api/cdr/valid${buildQuery(params)}`);
    },
    invalid(params) {
        return apiFetch(`/api/cdr/invalid${buildQuery(params)}`);
    },
    upload(file) {
        const form = new FormData();
        form.append("file", file);
        return apiFetch("/api/cdr/upload", { method: "POST", body: form });
    },
    importDirectory() {
        return apiFetch("/api/cdr/import", { method: "POST" });
    },
    job() {
        return apiFetch("/api/cdr/jobs/current");
    },
};
