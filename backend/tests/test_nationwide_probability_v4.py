"""Windows-safe model reload and frozen-study separation for v4 research."""

import numpy as np
from xgboost import XGBClassifier

from scripts import nationwide_probability_v3 as v3
from scripts import nationwide_probability_v4 as v4


def test_v4_reload_saved_model_bytes_and_predict(tmp_path) -> None:
    features = np.array([[0.0], [0.1], [0.2], [0.3], [0.7], [0.8], [0.9], [1.0]], dtype=np.float32)
    labels = np.array([0, 0, 0, 0, 1, 1, 1, 1], dtype=np.uint8)
    original = XGBClassifier(n_estimators=3, max_depth=2, n_jobs=1, tree_method="hist",
                             random_state=26080).fit(features, labels)
    path = tmp_path / "heavy_head.json"
    original.save_model(path)
    reloaded = v4._load_head(path)
    np.testing.assert_allclose(v4._head_probability(reloaded, features),
                               v4._head_probability(original, features), rtol=0, atol=0)


def test_v4_output_is_separate_from_failed_v3_attempt() -> None:
    assert v4.OUT != v3.OUT
    assert v4.PROTOCOL != v3.PROTOCOL
    assert v4.SEAL != v3.SEAL
    assert v4.SCORE != v3.SCORE
