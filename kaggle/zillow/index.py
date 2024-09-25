import contextlib
import io
import pathlib

import kagglehub
import pandas as pd

DATASET_ID = "robikscube/zillow-home-value-index"


# --------------------------------------------------------------------------- #
# start snippet setup


def get_data():
    console = io.StringIO()
    with contextlib.redirect_stdout(console), contextlib.redirect_stderr(console):
        p = pathlib.Path(kagglehub.dataset_download(DATASET_ID))

    return p, console


def load_data(data_dir: pathlib.Path) -> pd.DataFrame:
    data_dir, _ = get_data()
    data_path = data_dir / "ZHVI.parquet"
    return pd.read_parquet(data_path)


def clean_data(data: pd.DataFrame) -> pd.DataFrame:

    data.columns = [column.lower().replace(" ", "_") for column in data.columns]  # type: ignore[assignment]
    data.index = pd.to_datetime(data.index)
    data["year"] = data.index.year
    data["month"] = data.index.month

    return data


def split_data(data: pd.DataFrame):
    """Want to try to predict the final 5 years of data."""
    return data[:"2019-07-01"], data["2019-07-01":]  # type: ignore[misc]


# end snippet setup
