import { apiFetch } from "./client";

export const statsApi = {
    summary() {
        return apiFetch("/api/stats/summary");
    },
    daily() {
        return apiFetch("/api/stats/daily");
    },
    hourly() {
        return apiFetch("/api/stats/hourly");
    },
    scoreDistribution() {
        return apiFetch("/api/stats/score-distribution");
    },
    factors() {
        return apiFetch("/api/stats/factors");
    },
    directions() {
        return apiFetch("/api/stats/directions");
    },
    invalidReasons() {
        return apiFetch("/api/stats/invalid-reasons");
    },
};
