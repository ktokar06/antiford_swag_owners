import { apiFetch, buildQuery } from "./client";

export const blocksApi = {
    journal(params) {
        return apiFetch(`/api/blocks${buildQuery(params)}`);
    },
    numbers(params) {
        return apiFetch(`/api/blocks/numbers${buildQuery(params)}`);
    },
    summary() {
        return apiFetch("/api/blocks/summary");
    },
};
