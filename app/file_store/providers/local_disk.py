import shutil
from pathlib import Path

from app.file_store.base import BaseFileStore
from app.file_store.registry import FileStoreRegistry


@FileStoreRegistry.register("local_disk")
class LocalDiskFileStore(BaseFileStore):
    """Stores documents as plain files under ``data_dir/uploads/<doc_id>/``."""

    def __init__(self, cfg: dict):
        """
        Parameters
        ----------
        cfg : dict
            Provider config block. Reads ``data_dir`` (default ``./data``).
        """
        self._root = Path(cfg.get("data_dir", "./data")) / "uploads"

    def _dir(self, doc_id: str) -> Path:
        return self._root / doc_id

    def save(self, doc_id: str, filename: str, content: bytes) -> None:
        doc_dir = self._dir(doc_id)
        doc_dir.mkdir(parents=True, exist_ok=True)
        (doc_dir / filename).write_bytes(content)

    def load(self, doc_id: str, filename: str) -> bytes:
        return (self._dir(doc_id) / filename).read_bytes()

    def delete(self, doc_id: str) -> None:
        shutil.rmtree(self._dir(doc_id), ignore_errors=True)
