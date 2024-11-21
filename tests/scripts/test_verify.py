import datetime
import random
import uuid
from typing import Any, Iterable

import bson
import pydantic
import pytest
from dsa.bst import secrets

from acederbergio import config, db, env, util, verify

logger = env.create_logger(__name__)

# --------------------------------------------------------------------------- #
# Fakers

POPULATE_COUNT = 25

SITEMAP_LASTMOD = datetime.datetime.now()
SITEMAP_URLS = {
    "/index.html",
    "/posts/index.html",
    "/resume/index.html",
    "/projects/index.html",
    "/projects/blog/index.html",
    "projets/nvim-config/index.html",
}

METADATA_TIME_DELTA = datetime.timedelta(days=1)
METADATA_TIME = SITEMAP_LASTMOD - (POPULATE_COUNT * METADATA_TIME_DELTA)
MONGO_COLLECTION = "metadata"
MONGO_COLLECTION_PURE = "metadata_empty"
MONGO_DATABASE = "acederbergio_tests"


# class MetadataPytestInfo(pydantic.BaseModel):
#     index: int
#     uuid: str
#
#
# class Metadata(verify.Metadata):
#     pytest: MetadataPytestInfo


def create_site_map_url(url: str):
    return verify.SiteMapURLSet(  # type: ignore
        loc=url,
        lastmod=SITEMAP_LASTMOD,
    )


def time_for_index(index):
    return (METADATA_TIME_DELTA * index) + METADATA_TIME


def create_build_info(index=0):
    return config.BuildInfo(  # type: ignore
        git_commit=secrets.token_hex(20),
        git_ref="tests/fake-branch",
        time=time_for_index(index),
    )


def create_site_map():
    urlset = {url: create_site_map_url(url) for url in SITEMAP_URLS}
    return verify.SiteMap(urlset=urlset)


def create_metadatas(uuid: str, source: verify.Source, site_map: verify.SiteMap):

    metadatas = list(
        verify.Metadata(  # type: ignore
            time=METADATA_TIME + index * METADATA_TIME_DELTA,
            source=source,
            build_info=create_build_info(index),
            site_map=site_map,
            labels={
                "origin": "pytest",
                "pytest.index": index,
                "pytest.uuid": uuid,
                "pytest.helper": "create_metadatas",
            },
        )
        for index in range(POPULATE_COUNT)
    )

    return metadatas


# --------------------------------------------------------------------------- #
# Fixtures


@pytest.fixture(scope="session")
def pytest_uuid():
    return str(uuid.uuid4())


@pytest.fixture(scope="session")
def db_config():
    return db.Config(
        url="mongodb://root:changeme@db:27017",
        database=MONGO_DATABASE,
    )


@pytest.fixture(scope="session")
def source() -> verify.Source:
    return verify.Source(
        name="test",
        kind="test",
        directory=None,
        site="http://test.site.local",  # type: ignore
    )


@pytest.fixture(scope="session")
def site_map():
    return create_site_map()


# @pytest.fixture(scope="session")
# def build_info():
#     return create_build_info()


@pytest.fixture(scope="session")
def metadatas(pytest_uuid: str, source: verify.Source, site_map: verify.SiteMap):
    return create_metadatas(pytest_uuid, source, site_map)


@pytest.fixture(scope="session", params=[{"pure": False}])
def handler(
    request: pytest.FixtureRequest,
    db_config: db.Config,
    source: verify.Source,
    site_map: verify.SiteMap,
):
    """Session scoped so that io does not have to be performed to make the
    `metadata` property multiple times (if the source is not in test mode)."""
    pure = request.param["pure"]
    collection = MONGO_COLLECTION_PURE if pure else MONGO_COLLECTION
    build_info = create_build_info()
    build_info.time = SITEMAP_LASTMOD + (POPULATE_COUNT + 1) * METADATA_TIME_DELTA

    logger.info("Creating %s handler.", "pure" if pure else "impure")
    handler = verify.Handler(
        db_config=db_config,
        source=source,
        _site_map=site_map,
        _build_info=build_info,
        _collection_name=collection,
    )
    if pure:
        handler.collection.delete_many({})

    yield handler

    # if pure:
    #     handler.collection.delete_many({})


@pytest.fixture(scope="session", autouse=True)
def data(
    db_config: db.Config,
    metadatas: Iterable[verify.Metadata],
) -> dict[str, list[str]]:
    """Populate the impure database, ensure that the pure databse is empty."""

    client = db_config.create_client()
    db = client[MONGO_DATABASE]

    logger.info("Repopulating `%s.%s`", MONGO_DATABASE, MONGO_COLLECTION)
    collection = db[MONGO_COLLECTION]
    collection.delete_many({})
    collection.insert_many([mm.model_dump(mode="json") for mm in metadatas])

    # NOTE: Linking must be done post insert, doing this pre-insert results in
    #       generated `_id`s being overridden.
    res_raw = collection.find()
    res = list(map(verify.Metadata.model_validate, res_raw))

    assert len(res) == POPULATE_COUNT
    _ids, commits = [], []

    head = res[0]
    for item in res[1:]:
        _ids.append(head.mongo_id)
        commits.append(head.build_info.git_commit)

        for q in head.updates_append(item):
            res = collection.update_one(*q)

        head = item

    logger.info("Depopulating `%s.%s`", MONGO_DATABASE, MONGO_COLLECTION)
    collection = db[MONGO_COLLECTION_PURE]
    collection.delete_many({})

    return dict(_id=_ids, commit=commits)  # type: ignore[dict-item]


# --------------------------------------------------------------------------- #
# Tests


def test_populate(db_config: db.Config):

    client = db_config.create_client()
    db = client[MONGO_DATABASE]
    collection = db[MONGO_COLLECTION]

    assert collection.count_documents({}) == POPULATE_COUNT

    res = collection.aggregate(
        [
            {"$sort": {"timestamp": 1}},
            {
                "$project": {
                    "timestamp": "$timestamp",
                    "after": "$after",
                    "before": "$before",
                }
            },
        ]
    )

    head = res.next()
    assert head["after"] is None

    for item in res:
        assert head["timestamp"] < item["timestamp"]
        assert str(head["before"]) == str(item["_id"])

        head = item

    assert head["before"] is None


class TestSource:

    def test_check_one_source(self):
        """Make sure that the validator works as expected."""

        with pytest.raises(pydantic.ValidationError) as err:
            verify.Source(name="pytest", kind="site")  # type: ignore

        msg = str(err.value)
        assert "At least one of ``--directory`` or ``" in msg

        with pytest.raises(pydantic.ValidationError) as err:
            verify.Source(name="pytest", directory=env.BUILD, site="https://localhost:3333")  # type: ignore

        msg = str(err.value)
        assert "Cannot specify both of ``--directory`` and ``--site``." in msg

        verify.Source(name="pytest", kind="test")  # type: ignore
        verify.Source(name="pytest", kind="site", site="https://acederberg.io")  # type: ignore
        verify.Source(name="pytest", kind="directory", directory=env.BUILD)  # type: ignore

    @pytest.mark.parametrize(
        "_source",
        [
            verify.Source(name="pytest", kind="site", site="https://acederberg.io"),  # type: ignore
            verify.Source(name="pytest", kind="directory", directory=env.BUILD),  # type: ignore
        ],
    )
    def test_get_content(self, _source: verify.Source):
        """Make sure that ``get_content`` works for ``site`` and ``directory``."""

        # NOTE: Site does not yet have ``build.json``.
        content = _source._get_content("sitemap.xml")
        assert isinstance(content, str)


class TestHandler:
    """Test functions on an empty (pure) and non-empty (impure) database."""

    def test_history(
        self,
        pytest_uuid: str,
        handler: verify.Handler,
        data: dict[str, list[str]],
    ):

        ids = set(data["_id"])

        def verify_items(history: verify.History, *, count=POPULATE_COUNT):
            assert len(history.items) == count
            assert history.source == handler.source
            assert ids.issubset(set(map(lambda item: item.mongo_id, history.items)))
            assert history.items[0].after is None
            assert history.items[-1].before is None

            head = None
            for item in history.items:
                # NOTE: Verify that each data exists.
                q = {"_id": bson.ObjectId(item.mongo_id)}
                res_raw = handler.collection.find_one(q)
                assert res_raw is not None
                assert item.after is not None or item.before is not None

                res = verify.Metadata.model_validate(res_raw)
                assert res.source == history.source
                assert res.build_info == item.build_info
                assert res.after == item.after and res.before == item.before

                # NOTE: Data should be returned in ascending order.
                #       Further, search should return the ll in proper order.
                if head is not None:
                    assert head.before == item.mongo_id and item.after == head.mongo_id
                    assert head.timestamp < item.timestamp

                head = item

        history = handler.history()
        verify_items(history)

        # NOTE: Verify top.
        top_mongo_id = handler.top()
        assert top_mongo_id is not None

        handler.get(verify.Search(_id=top_mongo_id))  # type: ignore
        # assert top.pytest.index == POPULATE_COUNT - 1

        items: list[bson.ObjectId] = []
        for index in range(POPULATE_COUNT, POPULATE_COUNT + 3):
            print("===========================================")
            handler._build_info = create_build_info(index)

            assert (
                res := handler.push(
                    labels={
                        "pytest.uuid": pytest_uuid,
                        "pytest.test": "test_history",
                        "pytest.test_index": index,
                    },
                    _time=time_for_index(index),
                )
            ) is not None
            history = handler.history()
            util.print_yaml(
                [item.model_dump(mode="json") for item in history.items[20:-1]]
            )

            assert handler.top() == res
            verify_items(history, count=index + 1)

            assert handler.push() is None
            verify_items(history, count=index + 1)
            assert handler.top() == res

            items.append(res)

    def test_get(self, handler: verify.Handler, data: dict[str, list[str]]):
        _id = random.choice(data["_id"])
        commit = random.choice(data["commit"])
        output_id = handler.get(verify.Search(_id=_id))  # type: ignore
        output_commit = handler.get(verify.Search(commit=commit))  # type: ignore

        # if handler._collection_name == MONGO_COLLECTION_PURE:
        #     assert output_id is None and output_commit is None
        #     return

        assert output_commit is not None
        assert commit == output_commit.build_info.git_commit

        assert output_id is not None and output_id.mongo_id == _id

        # NOTE: Add the `$or` condition.
        c = output_id.build_info.git_commit
        params = verify.Search(_id=_id, commit=c)  # type: ignore
        assert "$or" in params.find()
        output_both = handler.get(params)
        assert output_id == output_both

    # def test_top(self, handler: verify.Handler):
    #     top = handler.top()
    #     assert True

    @pytest.mark.parametrize("handler", [{"pure": 1}], indirect=["handler"])
    def test_push(self, handler: verify.Handler, pytest_uuid: str):

        labels: dict[str, Any]
        labels = {"pytest.test": "test_push", "pytest.uuid": pytest_uuid}
        assert handler.top() is None
        assert handler.collection.count_documents({}) == 0

        # NOTE: Iteratively build / destroy the metadata ll and assess
        order = []
        for index in range(25):
            labels["pytest.index"] = index
            build_info = create_build_info(index)
            assert build_info.git_commit != handler.build_info.git_commit

            handler._build_info = build_info
            assert handler.build_info == build_info
            assert handler.metadata().build_info == build_info

            res = handler.push(labels=labels)
            assert handler.collection.count_documents({}) == index + 1

            top = handler.top()
            assert top == res
            order.append(top)

            print("================================")
            print(index)
            print(build_info.model_dump())

            metadata_from_get = handler.get(
                verify.Search(  # type: ignore
                    commit=handler.build_info.git_commit,
                    source=handler.source,
                )
            )
            assert metadata_from_get is not None
            assert metadata_from_get.mongo_id == str(top)

            # NOTE: Pushing again should do nothing.
            assert handler.push(labels=labels) is None

        for index in range(25):
            top_expected = order.pop()
            top = handler.top()
            assert top == top_expected

            pop_metadata = handler.pop()
            assert pop_metadata is not None
            assert pop_metadata.mongo_id == str(top)

            assert handler.collection.count_documents({}) == 25 - index - 1

        # NOTE: There should be nothing left, so ``pop`` should return ``None``
        assert handler.top() is None
        assert handler.pop() is None
        assert len(handler.history().items) == 0

    # def test_pop(self, handler: verify.Handler): ...
