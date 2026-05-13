import mimetypes
import os
import uuid
from functools import lru_cache

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import ClientError


def is_s3_enabled() -> bool:
    return os.getenv("S3_ENABLED", "false").lower() in ("1", "true", "yes")


@lru_cache
def _s3_client() -> BaseClient:
    endpoint = os.getenv("S3_ENDPOINT_URL") or None
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", ""),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def bucket_name() -> str:
    return os.getenv("S3_BUCKET_NAME", "profile-photos")


def ensure_bucket() -> None:
    if not is_s3_enabled():
        return
    client = _s3_client()
    b = bucket_name()
    try:
        client.create_bucket(Bucket=b)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            raise


def upload_profile_photo(profile_id: int, body: bytes, content_type: str, extension: str) -> str:
    ensure_bucket()
    ext = (extension or "jpg").lstrip(".")
    key = f"profiles/{profile_id}/{uuid.uuid4().hex}.{ext}"
    client = _s3_client()
    client.put_object(
        Bucket=bucket_name(),
        Key=key,
        Body=body,
        ContentType=content_type or "application/octet-stream",
    )
    return key


def presigned_get_url(object_key: str, expires_in: int = 3600) -> str:
    client = _s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name(), "Key": object_key},
        ExpiresIn=expires_in,
    )


def delete_object_key(object_key: str) -> None:
    if not object_key:
        return
    client = _s3_client()
    try:
        client.delete_object(Bucket=bucket_name(), Key=object_key)
    except Exception:
        pass


def guess_content_type(file_path: str) -> str:
    ct, _ = mimetypes.guess_type(file_path)
    return ct or "application/octet-stream"
