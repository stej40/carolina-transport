"""Garage/S3 presign helper.

Files travel client -> Garage directly; the API only presigns URLs and
verifies object existence on confirm (upload bytes never transit the API).
"""

from functools import lru_cache
from typing import Any

import boto3  # type: ignore[import-untyped]
from botocore.config import Config  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from app.config import settings


@lru_cache
def _client() -> Any:
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def presign_put(key: str, mime: str | None) -> str:
    params: dict[str, Any] = {"Bucket": settings.s3_bucket, "Key": key}
    if mime:
        params["ContentType"] = mime
    return str(
        _client().generate_presigned_url(
            "put_object", Params=params, ExpiresIn=settings.presign_ttl_sec
        )
    )


def presign_get(key: str) -> str:
    return str(
        _client().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": key},
            ExpiresIn=settings.presign_ttl_sec,
        )
    )


def object_exists(key: str) -> bool:
    try:
        _client().head_object(Bucket=settings.s3_bucket, Key=key)
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Status Code", ""))
        if code in ("404", "403") or exc.response.get("Error", {}).get("Code") in (
            "NoSuchKey",
            "404",
        ):
            return False
        raise
    return True
