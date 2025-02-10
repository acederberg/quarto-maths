"""Bucket for images using Linode object storage. :rocket:

This is done using the Linode cloud API directly.

.. seealso::

   https://techdocs.akamai.com/linode-api/reference/post-object-storage-bucket


For now, the bucket will be available on `bucket.acederberg.io`.
At the end of this file there is commented out code. I was playing with making
requests directly to `s3` but the bucket uses `AWS` signed authentication, 
which requires a great deal of overhead.
"""

import asyncio
import contextlib
from datetime import datetime
from typing import Annotated, Generic, NamedTuple, Self, TypeVar

import httpx
import pydantic
import rich
import rich.panel
import rich.syntax
import typer
import yaml
import yaml_settings_pydantic as ysp

from acederbergio import env, util

logger = env.create_logger(__name__)

URL_BUCKETS = "https://api.linode.com/v4/object-storage"
CONFIG = env.CONFIGS / "bucket.yaml"
STATE = env.CONFIGS / "bucket.state.yaml"


class BucketConfig(ysp.BaseYamlSettings):
    """Bucket configuration.

    Should be stored at the path specified by ``Config``.
    """

    model_config = ysp.YamlSettingsConfigDict(
        yaml_files={CONFIG: ysp.YamlFileConfigDict(required=True)}
    )

    prefix: Annotated[str, pydantic.Field("acederbergio")]
    region: Annotated[str, pydantic.Field("us-lax")]
    token: Annotated[pydantic.SecretStr, pydantic.Field()]

    s3_access_key_maybe: Annotated[
        pydantic.SecretStr | None, pydantic.Field(None, alias="s3_access_key")
    ]
    s3_secret_key_maybe: Annotated[
        pydantic.SecretStr | None, pydantic.Field(None, alias="s3_secret_key")
    ]

    @property
    def s3_secret_key(self) -> pydantic.SecretStr:
        if (key := self.s3_secret_key_maybe) is None:
            raise ValueError()

        return key

    @property
    def s3_access_key(self) -> pydantic.SecretStr:
        if (key := self.s3_access_key_maybe) is None:
            raise ValueError()

        return key

    @pydantic.computed_field
    @property
    def headers(self) -> dict[str, str]:
        """Headers for Linode requrests."""
        return {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {self.token.get_secret_value()}",
        }

    def req_create_bucket(self) -> httpx.Request:
        """
        Create the object storage bucket.

        - https://techdocs.akamai.com/linode-api/reference/post-object-storage-bucket
        """

        return httpx.Request(
            method="POST",
            url=URL_BUCKETS + "/buckets",
            json=dict(
                acl="private",
                cors_enabled=True,
                versioning=True,
                region=self.region,
                label=f"{self.prefix}-object-storage",
            ),
            headers=self.headers,
        )


class BucketKey(pydantic.BaseModel):
    """
    Bucket key object.

    Data is pulled down from the API.
    """

    label: str
    id: int
    limited: bool
    access_key: str
    secret_key: pydantic.SecretStr

    @pydantic.field_serializer("secret_key", when_used="json")
    def dump_secret(self, v):
        return v.get_secret_value()

    def req_destroy(self, config: BucketConfig) -> httpx.Request:
        """
        Remove the object storage key.

        -
        """
        return httpx.Request(
            method="DELETE",
            url=URL_BUCKETS + f"/keys/{ self.id }",
            headers=config.headers,
        )

    def req_get(self, config: BucketConfig) -> httpx.Request:
        url = URL_BUCKETS + f"/keys/{ self.id }"
        return httpx.Request(method="GET", url=url, headers=config.headers)


class Bucket(pydantic.BaseModel):
    """Bucket object.

    Data is pulled down from the API.
    """

    created: util.FieldTime
    hostname: str
    label: str
    objects: int
    region: str
    s3_endpoint: str
    size: int

    def req_create_access_key(self, config: BucketConfig) -> httpx.Request:
        """
        Create the access key.

        - https://techdocs.akamai.com/linode-api/reference/post-object-storage-keys
        """

        return httpx.Request(
            method="POST",
            url=URL_BUCKETS + "/keys",
            json=dict(
                bucket_access=[
                    dict(
                        bucket_name=self.label,
                        permissions="read_write",
                        region=self.region,
                    )
                ],
                label=f"{config.prefix}-object-storage-key",
            ),
            headers=config.headers,
        )

    def req_get(self, config: BucketConfig) -> httpx.Request:
        """
        Get the bucket.

        - https://techdocs.akamai.com/linode-api/reference/get-object-storage-buckets
        """

        url = URL_BUCKETS + f"/buckets/{self.region}/{self.label}"
        return httpx.Request(method="GET", url=url, headers=config.headers)

    def create_s3_url(self, *parts: str) -> str:

        return "https://" + "/".join((self.hostname, "/".join(parts)))


T_ProvisionInfo = TypeVar("T_ProvisionInfo")


class ProvisionInfo(NamedTuple, Generic[T_ProvisionInfo]):
    """
    Response for methods of :class:`BucketHandler`.
    """

    data: T_ProvisionInfo
    response: httpx.Response | None


class BucketState(ysp.BaseYamlSettings):
    """
    Bucket state.

    Data can be refreshed using the :class:`BucketHandler` with the `verify`
    option true.

    The context manager :func:`BucketHandler.context` will load this and dump it
    when the context ends.
    """

    bucket: Annotated[Bucket | None, pydantic.Field(None)]
    key: Annotated[BucketKey | None, pydantic.Field(None)]
    saved: Annotated[datetime | None, pydantic.Field(None)]

    model_config = ysp.YamlSettingsConfigDict(
        yaml_files={STATE: ysp.YamlFileConfigDict(required=False)}
    )

    def save(self):
        self.saved = datetime.now()
        with open(STATE, "w") as file:
            yaml.dump(self.model_dump(mode="json"), file)


class BucketHandler(pydantic.BaseModel):

    state: BucketState
    config: BucketConfig
    verify: bool = False

    @contextlib.contextmanager
    @staticmethod
    def context(save: bool = True):
        with util.catch_httpx():
            handler = BucketHandler.fromYaml()
            yield handler

            if save:
                handler.state.save()

    @classmethod
    def fromYaml(cls) -> Self:
        return cls(state=BucketState(), config=BucketConfig())

    async def ensure_bucket(self, client: httpx.AsyncClient) -> ProvisionInfo[Bucket]:

        response = None
        if self.state.bucket is None:
            response = await client.send(self.config.req_create_bucket())
        elif self.verify:
            response = await client.send(self.state.bucket.req_get(self.config))

        if response is not None:
            response.raise_for_status()
            self.state.bucket = Bucket.model_validate(response.json())

        if self.state.bucket is None:
            raise ValueError()

        return ProvisionInfo(self.state.bucket, response)

    async def ensure_key(self, client: httpx.AsyncClient) -> ProvisionInfo[BucketKey]:

        if (bucket := self.state.bucket) is None:
            raise ValueError()

        response = None
        if self.state.key is None:
            response = await client.send(bucket.req_create_access_key(self.config))
        elif self.verify:
            response = await client.send(self.state.key.req_get(self.config))

        if response is not None:
            response.raise_for_status()
            self.state.key = BucketKey.model_validate(response.json())

        if (key := self.state.key) is None:
            raise ValueError()

        return ProvisionInfo(key, response)

    async def up(self):

        async with httpx.AsyncClient() as client:
            info_bucket = await self.ensure_bucket(client)
            if (response := info_bucket.response) is not None:
                if response.status_code == 200:
                    rich.print("[green]Ensured bucket.")
                elif response.status_code == 201:
                    rich.print("[green]New bucket created 🚀")
            else:
                rich.print("[blue]Bucket already exists.")

            info_key = await self.ensure_key(client)
            if response := info_key.response:
                if response.request.method == "GET":
                    rich.print("[green]Ensured access key.")
                if response.request.method == "POST":

                    # NOTE: Make sure that the key is shown to the user, since
                    #       it will not be shown again with `GET`.
                    assert self.state.key
                    code = (
                        f"s3_secret_key: {self.state.key.secret_key.get_secret_value()}"
                    )
                    code += "\n"
                    code += f"s3_access_key: `{self.state.key.access_key}`"

                    rich.print(
                        rich.panel.Panel(
                            rich.console.Group(
                                f"[bold yellow]Copy to `{CONFIG}`.\n",
                                rich.syntax.Syntax(
                                    code=code, lexer="yaml", background_color="default"
                                ),
                                "\n",
                                "Use this information to configure s3cmd.",
                                "See https://techdocs.akamai.com/cloud-computing/docs/using-s3cmd-with-object-storage",
                                "\n",
                            ),
                            title="[red]Bucket Access Key",
                            subtitle="[yellow]This will only be printed once!",
                            style="bold yellow",
                        )
                    )
            else:
                rich.print("[blue]Bucket key already exists.")

    async def down(self):
        if self.state.key is None:
            rich.print("[green]No access key to revoke.")
            raise typer.Exit(0)

        async with httpx.AsyncClient() as client:
            response = await client.send(self.state.key.req_destroy(self.config))
            response.raise_for_status()
            rich.print("[green]Successfully revoked access key.")
            self.state.key = None


cli = typer.Typer()


@cli.command("up")
def cli_up(verify: bool = False):

    with BucketHandler.context() as handler:
        handler.verify = verify
        asyncio.run(handler.up())


@cli.command("down")
def cli_down():
    "Only deletes keys."

    with BucketHandler.context() as handler:
        asyncio.run(handler.down())


@cli.command("show")
def cli_show():

    handler = BucketHandler.fromYaml()
    util.print_yaml(handler, rule_title="Bucket Handler")


# def get_headers_s3(
#     self,
#     resource: str,
#     *,
#     method: str,
#     content_type: str | None = None,
# ) -> dict[str, str]:
#     """Headers for requests to the s3 bucket itself.
#
#     .. seealso::
#         https://docs.aws.amazon.com/AmazonS3/latest/API/RESTAuthentication.html
#         https://glacius.tmont.com/articles/uploading-to-s3-in-bash
#     """
#
#
#     if self.s3_access_key_maybe is None:
#         raise ValueError
#
#     # Should match `date -R` which should be RFC5322 complient.
#     ts = datetime.now(UTC).replace(microsecond=0)
#     date = format_datetime(ts, usegmt=True)
#     string_to_sign = "\n".join(
#         filter(
#             lambda item: item is not None,
#             (method, "\n", content_type, date, resource),
#         )
#     )
#     print(string_to_sign)
#
#     secret = self.s3_secret_key.get_secret_value().encode("utf-8")
#     sig_raw = hmac.new(
#         secret, string_to_sign.encode("utf-8"), hashlib.sha1
#     ).digest()
#     sig = base64.b64encode(sig_raw).decode("utf-8")
#
#     return {
#         "Authorization": f"AWS {self.s3_access_key}:{sig}",
#         "Content-Type": "application/x-svg",
#     }

# NOTE: Auth is such a pain I'll just use s3cmd.
# def req_upload_object(
#     self, config: BucketConfig, *object_name: str, content: bytes
# ) -> httpx.Request:
#
#     return httpx.Request(
#         method="PUT",
#         url=self.create_s3_url(*object_name),
#         content=content,
#         headers=config.headers_s3,
#     )
#
# def req_get_object(self, config: BucketConfig, *object_name) -> httpx.Request:
#
#     return httpx.Request(
#         method="GET",
#         url=self.create_s3_url(*object_name),
#         headers=config.get_headers_s3("/" + "/".join(object_name), method="GET"),
#     )

# async def upload_object(self):
#     async with httpx.AsyncClient() as client:
#         bucket, _ = await self.ensure_bucket(client)
#         response = await client.send(
#             bucket.req_upload_object(
#                 self.config,
#                 "/test/test_1.txt",
#                 content="This is a test".encode(),
#             )
#         )
#         response.raise_for_status()
#
#         util.print_yaml(response.json(), rule_title="Upload Successful!")
#
# async def get_object(self, *obj: str):
#     async with httpx.AsyncClient() as client:
#         bucket, _ = await self.ensure_bucket(client)
#
#         response = await client.send(bucket.req_get_object(self.config, *obj))
#         response.raise_for_status()
#
#         util.print_yaml(response.json(), rule_title="Reponse Data")


# @cli.command("upload")
# def cli_upload():
#
#     with BucketHandler.context(save=False) as handler:
#         asyncio.run(handler.upload_object())
#
#
# @cli.command("get")
# def cli_get():
#     with BucketHandler.context(save=False) as handler:
#         asyncio.run(handler.get_object("kube-red.svg"))


# @cli.command("regions")
# def cli_regions():
#
#     async def doit():
#         async with httpx.AsyncClient() as client:
#             response = await client.send(handler.config.req_regions())
#             response.raise_for_status()
#
#             util.print_yaml(response.json(), title="Available Regions")
#
#     with bucket_context() as handler:
#         asyncio.run(doit())
