import { apiFetch, buildQuery } from "./client";

export const numbersApi = {
    list(params) {
        return apiFetch(`/api/numbers${buildQuery(params)}`);
    },
    count(params) {
        return apiFetch(`/api/numbers/count${buildQuery(params)}`);
    },
    get(id) {
        return apiFetch(`/api/numbers/${id}`);
    },
    aggregateBySubscriber() {
        return apiFetch("/api/numbers/aggregate/by-subscriber");
    },
    aggregateInvalidReasons() {
        return apiFetch("/api/numbers/aggregate/invalid-reasons");
    },
};
