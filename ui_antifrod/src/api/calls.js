import { apiFetch, buildQuery } from "./client";

export const callsApi = {
    list(params) {
        return apiFetch(`/api/calls${buildQuery(params)}`);
    },
    count(params) {
        return apiFetch(`/api/calls/count${buildQuery(params)}`);
    },
    get(id) {
        return apiFetch(`/api/calls/${id}`);
    },
    update(id, patch) {
        return apiFetch(`/api/calls/${id}`, { method: "PATCH", body: patch });
    },
    bulkReview(ids, reviewStatus) {
        return apiFetch("/api/calls/bulk-review", {
            method: "POST",
            body: { ids, review_status: reviewStatus },
        });
    },
    aggregateByDay() {
        return apiFetch("/api/calls/aggregate/by-day");
    },
};
