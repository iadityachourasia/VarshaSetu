import pandas as pd
try:
    from backend.app.core.config import TRAIN_YEARS, VAL_YEARS, TEST_YEARS, UNSEEN_YEARS
except ModuleNotFoundError:
    from app.core.config import TRAIN_YEARS, VAL_YEARS, TEST_YEARS, UNSEEN_YEARS

def create_chronological_splits(df: pd.DataFrame) -> dict:
    """
    Partitions the dataset chronologically without temporal leakage.
    Returns dictionary with dataframes and partition metadata.
    """
    df_copy = df.copy()
    df_copy['year'] = df_copy['datetime'].dt.year

    train_df = df_copy[df_copy['year'].isin(TRAIN_YEARS)].copy()
    val_df = df_copy[df_copy['year'].isin(VAL_YEARS)].copy()
    test_df = df_copy[df_copy['year'].isin(TEST_YEARS)].copy()
    unseen_df = df_copy[df_copy['year'].isin(UNSEEN_YEARS)].copy()

    def partition_metadata(partition: pd.DataFrame, years: list[int]) -> dict:
        return {
            "years": list(years),
            "rows": int(len(partition)),
            "start_date": None if partition.empty else str(partition["date"].min()),
            "end_date": None if partition.empty else str(partition["date"].max()),
        }

    split_metadata = {
        "train": partition_metadata(train_df, TRAIN_YEARS),
        "validation": partition_metadata(val_df, VAL_YEARS),
        "test": partition_metadata(test_df, TEST_YEARS),
        "unseen": partition_metadata(unseen_df, UNSEEN_YEARS),
    }

    # Verify zero temporal overlap
    assert set(train_df.index).isdisjoint(set(val_df.index))
    assert set(val_df.index).isdisjoint(set(test_df.index))
    assert set(test_df.index).isdisjoint(set(unseen_df.index))
    assert set(train_df["datetime"]).isdisjoint(set(val_df["datetime"]))
    assert set(train_df["datetime"]).isdisjoint(set(test_df["datetime"]))
    assert set(val_df["datetime"]).isdisjoint(set(test_df["datetime"]))

    return {
        "train_df": train_df,
        "val_df": val_df,
        "test_df": test_df,
        "unseen_df": unseen_df,
        "metadata": split_metadata
    }
