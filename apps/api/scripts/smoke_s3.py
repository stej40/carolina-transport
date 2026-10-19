"""Smoke test: presigned PUT/GET round-trip against the configured S3 endpoint.

Usage (with infra stack running):
    uv run python scripts/smoke_s3.py
"""

import boto3
import httpx
from botocore.config import Config

from app.config import settings

s3 = boto3.client(
    "s3",
    endpoint_url=settings.s3_endpoint,
    aws_access_key_id=settings.s3_access_key,
    aws_secret_access_key=settings.s3_secret_key,
    region_name=settings.s3_region,
    config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
)

key = "smoke/hello.txt"
params = {"Bucket": settings.s3_bucket, "Key": key}

put_url = s3.generate_presigned_url("put_object", Params=params, ExpiresIn=60)
r = httpx.put(put_url, content=b"hello karolina", headers={"Content-Type": "text/plain"})
assert r.status_code == 200, f"presigned PUT failed: {r.status_code} {r.text}"
print("presigned PUT ok")

head = s3.head_object(**params)
assert head["ContentLength"] == len(b"hello karolina")
print("head_object ok")

get_url = s3.generate_presigned_url("get_object", Params=params, ExpiresIn=60)
r = httpx.get(get_url)
assert r.status_code == 200 and r.content == b"hello karolina", (
    f"presigned GET failed: {r.status_code}"
)
print("presigned GET ok")

s3.delete_object(**params)
print("ALL S3 SMOKE CHECKS PASSED")
