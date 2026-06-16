from src.chunking.text_chunker import chunk_text


def test_short_text_no_chunk():
    text = "Hello world. This is a test."
    chunks = chunk_text(text, max_tokens=100)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_long_text_chunks():
    sentences = [f"Sentence number {i} with some extra words." for i in range(200)]
    text = " ".join(sentences)
    chunks = chunk_text(text, max_tokens=50)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) > 0


def test_chunk_preserves_content():
    text = "First sentence. Second sentence. Third sentence. Fourth sentence."
    chunks = chunk_text(text, max_tokens=5)
    combined = " ".join(chunks)
    for sentence in ["First sentence", "Fourth sentence"]:
        assert any(sentence in c for c in chunks)
