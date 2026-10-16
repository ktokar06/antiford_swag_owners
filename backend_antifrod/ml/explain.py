"""Точные SHAP CatBoost: сумма вкладов + база = log-odds фрода."""
from catboost import Pool

from ml.features import CATEGORICAL_FEATURES


def explain_features(model, features):
    values = model.get_feature_importance(
        Pool(features, cat_features=CATEGORICAL_FEATURES), type="ShapValues")
    return [
        {"base_log_odds": float(row[-1]), "contribution_unit": "log_odds",
         "factors": sorted(
             [{"feature": name, "contribution": float(value)}
              for name, value in zip(features.columns, row[:-1])],
             key=lambda item: abs(item["contribution"]), reverse=True)}
        for row in values
    ]
