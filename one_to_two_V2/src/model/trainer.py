"""Model trainer (model layer).

This module contains:
- Dataset: Data class for training dataset
- OneToTwoDatasetBuilder: Build dataset from features
- OneToTwoPredictor: Train and predict using logistic regression

Design Principles:
- No business rule logic here
- No data fetching (belongs to data layer)
- Pure ML model operations
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ..core.constants import ModelNotTrainedError, validate_required_columns


@dataclass
class ModelMeta:
    """Model metadata."""
    train_start: str
    train_end: str
    sample_size: int
    base_success_rate: float
    features: list[str]
    model_type: str
    version: str
    cache_start: str | None = None
    cache_end: str | None = None
    train_months_requested: int | None = None
    train_months_actual: int | None = None


@dataclass
class Dataset:
    """Training dataset."""
    X: pd.DataFrame
    y: pd.Series
    feature_names: list[str]


class OneToTwoDatasetBuilder:
    """Build dataset from stock and market features."""

    def build(
        self,
        stock_features: pd.DataFrame,
        market_features: pd.DataFrame,
        label_col: str = "label",
    ) -> Dataset:
        """Build dataset from features.
        
        Args:
            stock_features: DataFrame with stock features and labels
            market_features: DataFrame with market features
            label_col: Column name for label
            
        Returns:
            Dataset ready for training
        """
        validate_required_columns(stock_features, [label_col], context="OneToTwoDatasetBuilder.stock_features")

        mf = market_features.copy()
        if len(mf) == 1:
            mf = pd.concat([mf] * len(stock_features), ignore_index=True)

        X = pd.concat([stock_features.reset_index(drop=True), mf.reset_index(drop=True)], axis=1)
        validate_required_columns(X, [label_col], context="OneToTwoDatasetBuilder.dataset")

        y = X[label_col]
        X = X.drop(columns=[label_col, "date", "symbol"], errors="ignore")

        return Dataset(X=X, y=y, feature_names=list(X.columns))


class OneToTwoPredictor:
    """One-to-two prediction model using logistic regression."""

    def __init__(self):
        """Initialize predictor with sklearn pipeline."""
        self.pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=500)),
        ])
        self._fitted = False

    def fit(self, dataset: Dataset) -> None:
        """Fit the model on dataset.
        
        Args:
            dataset: Training dataset
        """
        self.pipeline.fit(dataset.X, dataset.y)
        self._fitted = True

    def predict_proba(self, X: pd.DataFrame) -> pd.Series:
        """Predict probability of one-to-two success.
        
        Args:
            X: Feature DataFrame
            
        Returns:
            Series with probabilities
            
        Raises:
            RuntimeError: If model is not fitted
        """
        if not self._fitted:
            raise ModelNotTrainedError()

        proba = self.pipeline.predict_proba(X)[:, 1]
        return pd.Series(proba, index=X.index, name="p_one_to_two")

    def save(self, path: str, meta: ModelMeta | None = None) -> None:
        """Save model to file with optional metadata.
        
        Args:
            path: File path to save model (e.g., data/models/model_xxx.joblib)
            meta: Optional model metadata to save alongside
        """
        import joblib
        joblib.dump(self.pipeline, path)

        if meta is not None:
            meta_path = Path(path).with_suffix(".meta.json")
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(asdict(meta), f, ensure_ascii=False, indent=2)

    def load(self, path: str) -> None:
        """Load model from file.
        
        Args:
            path: File path to load model
        """
        import joblib
        self.pipeline = joblib.load(path)
        self._fitted = True

    @staticmethod
    def load_meta(path: str) -> ModelMeta | None:
        """Load model metadata from file.
        
        Args:
            path: Model file path (e.g., data/models/model_xxx.joblib)
            
        Returns:
            ModelMeta if metadata file exists, None otherwise
        """
        meta_path = Path(path).with_suffix(".meta.json")
        if not meta_path.exists():
            return None

        with open(meta_path, encoding="utf-8") as f:
            data = json.load(f)

        return ModelMeta(**data)
