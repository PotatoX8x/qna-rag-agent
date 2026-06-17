from app.agent.state import ScoredDoc

MAX_CONTEXT_CHARS = 12_000


def format_docs(docs: list[ScoredDoc], max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """Render scored docs as a numbered, character-capped context string.

    Parameters
    ----------
    docs : list[ScoredDoc]
        ``(Document, score)`` pairs to render.
    max_chars : int, optional
        Hard limit on total character count across all excerpts.

    Returns
    -------
    str
        Numbered context block ready for prompt interpolation.
    """
    parts: list[str] = []
    used = 0
    for i, (doc, _) in enumerate(docs):
        excerpt = doc.page_content[:2000]
        if used + len(excerpt) > max_chars:
            break
        parts.append(f"[{i}] {excerpt}")
        used += len(excerpt)
    return "\n\n".join(parts)
