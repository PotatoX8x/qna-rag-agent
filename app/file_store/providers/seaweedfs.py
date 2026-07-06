import boto3
from botocore.exceptions import ClientError

from app.file_store.base import BaseFileStore
from app.file_store.registry import FileStoreRegistry


@FileStoreRegistry.register("seaweedfs")
class SeaweedFSFileStore(BaseFileStore):
    """Stores documents in SeaweedFS via its S3-compatible gateway.

    Objects are keyed as ``<doc_id>/<filename>`` inside a single bucket,
    created on first use if it doesn't already exist.
    """

    def __init__(self, cfg: dict):
        """
        Parameters
        ----------
        cfg : dict
            Provider config block. Reads ``endpoint_url``, ``access_key``,
            ``secret_key``, and ``bucket`` (default ``documents``).
        """
        self._bucket = cfg.get("bucket", "documents")
        self._client = boto3.client(
            "s3",
            endpoint_url=cfg["endpoint_url"],
            aws_access_key_id=cfg.get("access_key", ""),
            aws_secret_access_key=cfg.get("secret_key", ""),
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            try:
                self._client.create_bucket(Bucket=self._bucket)
            except ClientError:
                pass  # created concurrently by another process

    def _key(self, doc_id: str, filename: str) -> str:
        return f"{doc_id}/{filename}"

    def save(self, doc_id: str, filename: str, content: bytes) -> None:
        self._client.put_object(Bucket=self._bucket, Key=self._key(doc_id, filename), Body=content)

    def load(self, doc_id: str, filename: str) -> bytes:
        obj = self._client.get_object(Bucket=self._bucket, Key=self._key(doc_id, filename))
        return obj["Body"].read()

    def delete(self, doc_id: str) -> None:
        prefix = f"{doc_id}/"
        resp = self._client.list_objects_v2(Bucket=self._bucket, Prefix=prefix)
        keys = [{"Key": obj["Key"]} for obj in resp.get("Contents", [])]
        if keys:
            self._client.delete_objects(Bucket=self._bucket, Delete={"Objects": keys})
