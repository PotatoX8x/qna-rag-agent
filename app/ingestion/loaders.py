from pathlib import Path

_ALLOWED_SUFFIXES = {".pdf", ".docx", ".doc", ".pptx", ".xlsx", ".txt", ".md", ".html", ".htm", ".csv"}


def load_file(path: Path) -> str:
    """Extract raw text from a file using Unstructured.

    Parameters
    ----------
    path : Path
        Absolute path to the file on disk.

    Returns
    -------
    str
        Extracted plain text with page/section breaks joined by ``\\n\\n``.
    """
    from langchain_community.document_loaders import UnstructuredFileLoader

    loader = UnstructuredFileLoader(str(path), mode="single")
    docs = loader.load()
    return "\n\n".join(d.page_content for d in docs if d.page_content.strip())


def sniff_content_type(filename: str) -> str:
    """Infer MIME type from the file extension.

    Parameters
    ----------
    filename : str
        File name or path whose suffix determines the type.

    Returns
    -------
    str
        MIME type string, defaulting to ``text/plain`` for unknown extensions.
    """
    suffix = Path(filename).suffix.lower()
    return {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".html": "text/html",
        ".htm": "text/html",
        ".csv": "text/csv",
    }.get(suffix, "text/plain")


def allowed_suffix(filename: str) -> bool:
    """Return ``True`` when the file extension is accepted by the ingestion pipeline.

    Parameters
    ----------
    filename : str
        File name whose suffix is checked against the allowed set.

    Returns
    -------
    bool
        ``True`` if the extension is supported, ``False`` otherwise.
    """
    return Path(filename).suffix.lower() in _ALLOWED_SUFFIXES
