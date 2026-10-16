import { apiFetch, buildQuery } from "./client";

export const graphApi = {
    listClusters(params) {
        return apiFetch(`/api/graph/clusters${buildQuery(params)}`);
    },
    countClusters(params) {
        return apiFetch(`/api/graph/clusters/count${buildQuery(params)}`);
    },
    getCluster(id) {
        return apiFetch(`/api/graph/clusters/${id}`);
    },
    findByLabel(label) {
        return apiFetch(`/api/graph/clusters${buildQuery({ label })}`);
    },
};
