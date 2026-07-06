from abc import ABC, abstractmethod


class BaseFileStore(ABC):
    """Provider-agnostic store for the raw bytes of uploaded documents.

    Documents are addressed by ``doc_id`` (one per uploaded file); ``delete``
    removes everything stored under that id.
    """

    @abstractmethod
    def save(self, doc_id: str, filename: str, content: bytes) -> None:
        """Persist a document's raw bytes.

        Parameters
        ----------
        doc_id : str
            Document UUID the bytes belong to.
        filename : str
            Original filename, kept so extension-based parsing still works.
        content : bytes
            Raw file content.
        """

    @abstractmethod
    def load(self, doc_id: str, filename: str) -> bytes:
        """Retrieve a document's raw bytes.

        Parameters
        ----------
        doc_id : str
            Document UUID the bytes belong to.
        filename : str
            Original filename passed to :meth:`save`.

        Returns
        -------
        bytes
            Raw file content.
        """

    @abstractmethod
    def delete(self, doc_id: str) -> None:
        """Remove everything stored for a document.

        Safe to call for a document whose files no longer exist (e.g. already
        purged after ingestion completed).

        Parameters
        ----------
        doc_id : str
            Document UUID to purge.
        """
