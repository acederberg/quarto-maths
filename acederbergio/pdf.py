import asyncio
import enum
import hashlib
import math
import pathlib
from typing import Annotated, Any, ClassVar, Generator, Optional, Protocol, Self

import motor
import motor.motor_asyncio
import nltk
import pandas as pd
import pydantic
import pypdf as pdf
import rake_nltk as rake
import typer

from acederbergio import db, env, util

logger = env.create_logger(__name__)

MetricsNamesMap = {
    rake.Metric.WORD_DEGREE: "degree",
    rake.Metric.WORD_FREQUENCY: "frequency",
    rake.Metric.DEGREE_TO_FREQUENCY_RATIO: "ratio",
}
MetricsColumns = ["phrase", *(MetricsNamesMap[metric] for metric in rake.Metric)]


class MetricsHighlighter(Protocol):
    def __call__(
        self, phrase: str, match: str, *, metrics: "MetricsRow | None" = None
    ) -> str: ...


# MetricsStopWords = set(stopwords.words("english"))


# start snippet metrics
class MetricsRow(pydantic.BaseModel):
    phrase: str
    degree: float
    frequency: float
    ratio: float

    @classmethod
    def fromDFRow(cls, row: pd.Series) -> Self:
        return cls.model_validate(dict(zip(MetricsColumns, row)))

    def to_df_row(self) -> tuple[str, float, float, float]:
        return (self.phrase, self.degree, self.frequency, self.ratio)


class MetricsComparison(pydantic.BaseModel):
    phrases: Annotated[set[str], pydantic.Field(description="Common phrases.")]
    left: "Metrics"
    right: "Metrics"

    count_left: int
    score_left: Annotated[
        float,
        pydantic.Field(description="Percent containment of left in right."),
    ]

    count_right: int
    score_right: Annotated[
        float,
        pydantic.Field(description="Percent containerment of right in left."),
    ]

    @classmethod
    def compare(cls, left: "Metrics", right: "Metrics") -> Self:

        phrases = set(left.metrics) & set(right.metrics)
        count_left = len(left.metrics)
        count_right = len(right.metrics)
        return cls(
            phrases=phrases,
            score_left=100 * len(phrases) / count_left,
            score_right=100 * len(phrases) / count_right,
            count_left=count_left,
            count_right=count_right,
            left=left,
            right=right,
        )


class Metrics(util.HasTimestamp, db.HasMongoId):
    """
    **RAKE** metrics for a piece of text.

    The goal is to put data into `MongoDB` and have this data be easily
    comparable to metrics for other documents.

    .. This should eventually use TLSH fuzzy hashes so similarity of documents
       can be clustered. For now, a ``sha_256`` hash is used to distinguish one
       document from another.

    :ivar text: The raw text for which the metrics are computed.
    :ivar metadata: Metadata.
    :ivar metrics: Key phrase metrics for :ivar:`text`.
    .. :ivar labels: Some labels for the data.
    """

    _collection: ClassVar[str] = "metrics"

    text_hash_256: Annotated[str, pydantic.Field()]
    text: str
    metadata: dict[str, str]

    metrics: dict[str, MetricsRow]

    @pydantic.model_validator(mode="before")
    def compute_hashes(cls, v):

        hasher = hashlib.sha256()
        hasher.update(v["text"].encode())
        v["text_hash_256"] = hasher.hexdigest()

        return v

    @classmethod
    def createDFItem(
        cls, text: str, *, ranking_metric: rake.Metric, **rake_kwargs
    ) -> pd.DataFrame:

        if "include_repeated_phrases" not in rake_kwargs:
            rake_kwargs.update(include_repeated_phrases=False)
        # if "stopwords" not in rake_kwargs:
        #     rake_kwargs.update(stopwords=MetricsStopWords)

        r = rake.Rake(
            language="english",
            ranking_metric=ranking_metric,
            **rake_kwargs,
        )
        r.extract_keywords_from_text(text)
        q = {key: [value] for value, key in r.get_ranked_phrases_with_scores()}

        return pd.DataFrame(q)

    @classmethod
    def createDF(cls, text: str, **rake_kwargs) -> pd.DataFrame:
        """Create the dataframe from nothing.

        This should be compatible with the shape of `cls.metrics`.
        """

        logger.info("Creating metrics dataframe.")
        df = pd.concat(
            [
                cls.createDFItem(text, ranking_metric=ranking_metric, **rake_kwargs)
                for ranking_metric in rake.Metric
            ],
            ignore_index=True,
        )

        df = df.transpose()  # .rename(columns=[metric.name for metric in rake.])
        df.reset_index(inplace=True)
        df.columns = MetricsColumns  # type: ignore[assignment]

        return df

    @classmethod
    def create(
        cls, df: pd.DataFrame, *, text: str, metadata: dict[str, str] | None = None
    ) -> Self:
        """Transform a compatible dataframe into this object."""

        metrics = {row[0]: MetricsRow.fromDFRow(row) for _, row in df.iterrows()}
        return cls(metrics=metrics, text=text, metadata=metadata)  # type: ignore[call-arg,arg-type]

    @classmethod
    def match_text(cls, text: str) -> dict:
        """Match query against text digest."""

        hasher = hashlib.sha256()
        hasher.update(text.encode())

        return {"$match": {"text_hash_256": hasher.hexdigest()}}

    @classmethod
    async def fetch(
        cls,
        db: motor.motor_asyncio.AsyncIOMotorDatabase,
        *,
        text: str,
    ) -> Self | None:

        collection = db[cls._collection]
        res = await collection.find_one(cls.match_text(text)["$match"])
        if res is None:
            return None

        return cls.model_validate(res)

    @classmethod
    async def lazy(
        cls,
        db: motor.motor_asyncio.AsyncIOMotorDatabase,
        *,
        text: str,
        metadata: dict[str, str] | None = None,
        force: bool = False,
    ) -> Self:

        # if db is None:
        #     return cls.create(cls.createDF(text), text=text, metadata=metadata)

        collection = db[cls._collection]
        res = await collection.find_one(cls.match_text(text)["$match"])
        if not force and res is not None:
            logger.info("Loading metrics dataframe from mongodb.")
            pydantic_data = cls.model_validate(res)
        else:
            if res is not None and force:
                client = db[cls._collection]
                res = await client.delete_one({"_id": res["_id"]})

                if not res.deleted_count:
                    raise ValueError("Failed to deleted object.")

            logger.info("Creating metrics dataframe since not found.")
            pydantic_data = cls.create(cls.createDF(text), text=text, metadata=metadata)
            await pydantic_data.store(db)

        return pydantic_data

    async def store(self, db: motor.motor_asyncio.AsyncIOMotorDatabase):
        logger.info("Saving metrics data to mongodb.")
        collection = db[self._collection]
        res = await collection.insert_one(self.model_dump(mode="json"))
        return res

    def to_df(self) -> pd.DataFrame:

        rows = [value.to_df_row() for value in self.metrics.values()]
        df = pd.DataFrame(rows, columns=MetricsColumns)

        return df

    def trie(self) -> dict[str, Any]:

        root: dict[str, Any] = {}

        for phrase, metrics in self.metrics.items():
            node = root
            for word in nltk.tokenize.word_tokenize(phrase):
                if word in node:
                    node = node[word]
                else:
                    node[word] = {}
                    node = node[word]

            # NOTE: Terminal node contains data.
            node["__metrics__"] = metrics

        return root

    def chunks(self) -> Generator[dict[str, Any], None, None]:
        trie = self.trie()
        tokenized = nltk.tokenize.word_tokenize(self.text)
        k, n = 0, len(tokenized)

        phrase: list[str] = []
        while k < n:
            word = tokenized[k]
            word_lower = word.lower()
            node = trie

            keyword = []
            while word_lower in node:
                keyword.append(word)
                node = node[word_lower]
                k += 1
                if k >= n:
                    break

                word = tokenized[k]
                word_lower = word.lower()

            if keyword:
                if phrase:
                    yield {"phrase": phrase}
                    phrase = list()
                if "__metrics__" in node:
                    yield {
                        "match": "full",
                        "phrase": keyword,
                        "metrics": node["__metrics__"],
                    }
                else:
                    yield {"match": "partial", "phrase": keyword}

            k += 1
            phrase.append(word)

        if phrase:
            yield {"phrase": phrase}

    def highlight(self, highlighter: MetricsHighlighter | None = None) -> str:
        """Return :ivar:`text` with the keywords highlighted using
        bold (as in markdown).

        Spaces are not perfect, but that is okay for now. The detokenizer does
        its best to fix everything up.
        """

        # NOTE: Probably faster to rebuild. This would be a good problem to
        #       solve with a trie since phrases.

        detokenizer = nltk.TreebankWordDetokenizer()

        output = []
        for chunk in self.chunks():

            match = chunk.get("match")
            metrics = chunk.get("metrics")
            phrase = detokenizer.detokenize(chunk["phrase"])

            if match is None:
                pass
            elif match == "full":
                phrase = (
                    f"**{phrase}**"
                    if highlighter is None
                    else highlighter(phrase, "full", metrics=metrics)
                )
            elif match == "partial":
                phrase = (
                    f"*{phrase}*"
                    if highlighter is None
                    else highlighter(phrase, "partial", metrics=metrics)
                )
            else:
                raise ValueError()

            output.append(phrase)

        return detokenizer.detokenize(output)

    def highlight_html(
        self,
        *,
        ranking_metric: rake.Metric = rake.Metric.DEGREE_TO_FREQUENCY_RATIO,
    ) -> str:

        ranking_attr = MetricsNamesMap[ranking_metric]
        value_max = (
            max((getattr(item, ranking_attr) for item in self.metrics.values())) // 2
        )

        # fmt: off
        colors = [
            "#2780e3", "#3e78e4", "#5571e5", "#6c6ae6", "#8362e7", "#9b5be8",
            "#b254e9", "#c94cea", "#e045eb", "#f83eec", "#f00",
        ]
        # fmt: on

        def highlighter(phrase: str, match: str, *, metrics: MetricsRow | None = None):
            if match == "partial":
                return phrase

            if metrics is not None:
                tooltip = f"ratio={metrics.ratio}, frequency={metrics.frequency}, degree={metrics.degree}."
            else:
                tooltip = "No metrics."

            value = getattr(metrics, ranking_attr)
            significance = min(math.floor(10 * value / value_max), 10)
            color = colors[significance]
            return f"""<text
              style='background: {color};'
              data-bs-toggle='tooltip'
              data-bs-title='{ tooltip }'
              class='fw-normal text-white'
            >{phrase}</text>
            """

        return f"<div class='rake-highlights text-black fw-lighter pb-5'>{self.highlight(highlighter)}</div>"

    # def __and__(self, other: Self) -> dict[str, MetricsRow]:
    #     """ """
    #     phrases = [row.phrase for row in self.metrics if row.phrase in other.metrics]

    # def __xor__(self, other: Self): ...

    # end snippet metrics


class JobDescription(pydantic.BaseModel): ...


class PDFConfig(pydantic.BaseModel):

    path: Annotated[pathlib.Path, pydantic.Field()]
    descriptions: list[JobDescription]

    def load(self) -> pdf.PdfReader:
        return pdf.PdfReader(self.path)


class PDFHandler:

    config: PDFConfig
    reader: pdf.PdfReader

    def __init__(self, config):
        self.config = config
        self.reader = config.load()

    # NOTE: Add keywords extracted from ``JobDescription`` and ``reader``.
    #       https://pypdf.readthedocs.io/en/stable/user/metadata.html
    def add_keywords(self): ...

    def get_text(self) -> str:
        return "".join(
            page.extract_text(extraction_mode="layout") for page in self.reader.pages
        )

    def get_links(self) -> list[str]:
        """
        https://pypdf.readthedocs.io/en/stable/user/reading-pdf-annotations.html
        """

        links = {
            obj["/A"]["/URI"]
            for page in self.reader.pages
            if (annotations := page.get("/Annots"))
            for annotation in annotations
            if (obj := annotation.get_object())["/Subtype"] == "/Link"
        }
        return list(links)

    async def get_metrics(
        self, db: motor.motor_asyncio.AsyncIOMotorDatabase
    ) -> Metrics:
        return await Metrics.lazy(db, text=self.get_text())


# TODO: Make context. This should be easy to do, but requires factoring out
#       some functionality of ``api.quarto:Context``.
# class Context:
#
#     database: db.Config
#
#     def __init__(self, )


class OutputEnum(str, enum.Enum):
    chunks = "chunks"
    highlight = "highlight"
    tree = "tree"
    html = "html"


FlagText = Annotated[Optional[str], typer.Option("--text")]
FlagFile = Annotated[Optional[str], typer.Option("--file")]


class MetricsContext(db.BaseDBContext):

    text: str
    metadata: dict[str, str]

    def __init__(
        self, text: str, metadata: dict[str, str], *, database: db.Config | None = None
    ):
        super().__init__(database)
        self.text = text
        self.metadata = metadata

    @classmethod
    def resolveText(cls, text: FlagText, _file: FlagFile) -> tuple[str, dict[str, str]]:
        if text is None and _file is None:
            util.CONSOLE.print("[red]One of `--text` or `--file` is required.")
            raise typer.Exit(3)

        metadata = dict(origin="cli", origin_file="pdf.py")
        if _file is not None:
            file = pathlib.Path(_file).resolve(strict=True)

            if file.suffix == ".pdf":
                text = PDFHandler(PDFConfig(path=file, descriptions=[])).get_text()
            else:
                with open(file, "r") as file_io:
                    text = "".join(file_io.readlines())

            metadata.update(from_="file", file=str(file))
        else:
            metadata.update(from_="text")

        if text is None:
            util.CONSOLE.print("[red]Failed to determine text.")
            raise typer.Exit(2)

        return text, metadata

    @classmethod
    def forTyper(
        cls,
        _context: typer.Context,
        _text: FlagText = None,
        _path: FlagFile = None,
    ) -> Self:
        text, metadata = cls.resolveText(_text, _path)
        self = cls(text=text, metadata=metadata)
        if not _context.obj:
            _context.obj = dict()
        _context.obj["metrics"] = self
        return self


cli_metrics = typer.Typer()
cli = typer.Typer()
cli.add_typer(cli_metrics, name="metrics", callback=MetricsContext.forTyper)


@cli_metrics.command("find")
def cli_find(
    _context: typer.Context,
    force: bool = False,
    output_yaml: Annotated[bool, typer.Option("--yaml/--dataframe")] = False,
):

    context: MetricsContext = _context.obj["metrics"]
    res = asyncio.run(
        Metrics.lazy(
            context.db, text=context.text, metadata=context.metadata, force=force
        )
    )

    if not output_yaml:
        df = res.to_df()

        util.CONSOLE.print("MongoDB Metadata", style="bold blue")
        util.CONSOLE.print()
        util.print_yaml(res.model_dump(mode="json", exclude={"metrics", "text"}))
        util.CONSOLE.print()

        util.CONSOLE.rule("Dataframe Head", style="bold blue")
        util.CONSOLE.print()
        util.print_df(df, expand=True)
        util.CONSOLE.print()
        return

    util.print_yaml(
        res,
        rule_title="metrics",
        rule_kwargs=dict(characters="=", style="bold blue"),
    )


@cli_metrics.command("highlight")
def cli_highlight(
    _context: typer.Context, *, output: OutputEnum = OutputEnum.highlight
):
    context: MetricsContext = _context.obj["metrics"]
    res = asyncio.run(Metrics.fetch(context.db, text=context.text))
    if res is None:
        util.CONSOLE.print("[red]No document for text.")
        raise typer.Exit(5)

    if output.value == "chunks":
        for chunk in res.chunks():
            util.print_yaml(chunk, as_json=True)
            input()
        return
    elif output.value == "tree":
        util.print_yaml(res.trie(), as_json=False, is_complex=True)
        return
    elif output.value == "html":
        util.CONSOLE.print(res.highlight_html())
        return

    def highlighter(
        phrase: str, match: str, *, metrics: MetricsRow | None = None
    ) -> str:
        print("metrics", metrics)
        # if match is None:
        #     return phrase
        if match == "full":
            color = "green"
        else:
            color = "grey"

        assert metrics
        return f"[{color}]{phrase}[/{color}][pink](score={metrics.ratio:.3})[/pink]"

    util.CONSOLE.print(res.highlight(highlighter=highlighter))


@cli.command("parse")
def cli_parse():
    path = env.BUILD / "resume/resume-2.pdf"
    if not path.is_file():
        util.CONSOLE.print(f"[red]{path} is not a file.")
        raise typer.Exit(1)

    handler = PDFHandler(PDFConfig(path=path, descriptions=[]))
    util.print_yaml(handler.get_links(), as_json=True)
    # print(text)
    # print(handler.reader.metadata)
    # print(handler.reader.attachments)
    return handler


if __name__ == "__main__":
    # cli()
    handler = cli_parse()
