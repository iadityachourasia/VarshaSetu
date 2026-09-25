# Serialized model artifacts

The `.pkl` files in this directory are retained as legacy audit evidence only.

They were produced from the absent dataset `GOA_DATA (1).csv` with SHA-256
`30e4df58e8b84e13579651aae693dd1885a468f78bd1bc420d6ae0a61f03d1b6`.
They must not be loaded against the checked-in `data/GOA_CLEAN.csv`.

In particular, `xgb_2000.pkl` is not evidence of a distinct 2000-tree run: the
audited implementation used the same 1000-tree configuration as the other
XGBoost experiment. Executable training/report code no longer includes that
mislabeled experiment.
