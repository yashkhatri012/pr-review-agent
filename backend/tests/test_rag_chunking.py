from services.rag_service import _chunk_text, _guess_language


def test_chunk_text_splits_by_line_count():
    content = "\n".join(f"line {i}" for i in range(10))
    chunks = _chunk_text(content, chunk_size=4, overlap=0)
    assert len(chunks) == 3
    assert chunks[0].splitlines() == ["line 0", "line 1", "line 2", "line 3"]


def test_chunk_text_applies_overlap():
    content = "\n".join(f"line {i}" for i in range(6))
    chunks = _chunk_text(content, chunk_size=4, overlap=2)
    # step = chunk_size - overlap = 2, so chunks start at 0, 2, 4
    assert chunks[0].splitlines()[0] == "line 0"
    assert chunks[1].splitlines()[0] == "line 2"


def test_chunk_text_empty_content_returns_no_chunks():
    assert _chunk_text("", chunk_size=10, overlap=0) == []


def test_guess_language_known_extension():
    assert _guess_language("app/main.py") == "python"
    assert _guess_language("web/index.ts") == "typescript"


def test_guess_language_unknown_extension_returns_none():
    assert _guess_language("README") is None
