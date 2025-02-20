from acederbergio.filters import util


class S3AssetConfig(util.BaseHasIdentifier):
    source_url: str | None
    source_path: str | None
    path: str
