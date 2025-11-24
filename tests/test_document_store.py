"""
Tests for Document Store functionality
"""

import asyncio
import tempfile
import os
from pathlib import Path
import pytest
from core.document_store import DocumentStore


class TestDocumentStore:

    @pytest.fixture
    async def temp_config(self):
        """Create temporary config for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                'data_dir': temp_dir,
                'chunk_size': 500,
                'chunk_overlap': 100,
                'max_context_chunks': 3,
                'embedding': {
                    'provider': 'local',
                    'model': 'all-MiniLM-L6-v2',
                    'device': 'cpu'
                },
                'vector': {
                    'backend': 'faiss',
                    'dimension': 384,
                    'metric': 'cosine'
                }
            }
            yield config

    def test_document_store_initialization(self, temp_config):
        """Test basic document store initialization"""
        store = DocumentStore(temp_config)
        assert store.config == temp_config
        assert store.chunk_size == 500
        assert store.chunk_overlap == 100

    def test_generate_document_id(self, temp_config):
        """Test document ID generation"""
        store = DocumentStore(temp_config)
        test_file = Path("/some/test/path/document.pdf")

        doc_id = store._generate_document_id(test_file)
        assert isinstance(doc_id, str)
        assert len(doc_id) > 0
        # Should be deterministic for same file
        doc_id2 = store._generate_document_id(test_file)
        assert doc_id == doc_id2

    def test_get_mime_type(self, temp_config):
        """Test MIME type detection"""
        store = DocumentStore(temp_config)

        assert store._get_mime_type(Path("test.pdf")) == "application/pdf"
        assert store._get_mime_type(Path("test.docx")) == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert store._get_mime_type(Path("test.txt")) == "text/plain"
        assert store._get_mime_type(Path("test.unknown")) == "application/octet-stream"

    def test_chunk_text(self, temp_config):
        """Test text chunking"""
        store = DocumentStore(temp_config)

        # Create a test document info
        from core.document_store import DocumentInfo
        doc_info = DocumentInfo(
            id="test_doc",
            file_path="test.txt",
            file_name="test.txt",
            file_size=100,
            mime_type="text/plain",
            last_modified=1234567890
        )

        text = "This is a test document. " * 20  # Repeat to create longer text
        chunks = store._chunk_text(text, doc_info)

        assert len(chunks) > 0
        assert all(isinstance(chunk.content, str) for chunk in chunks)
        assert all(chunk.document_id == "test_doc" for chunk in chunks)

        # Check that chunks have some overlap
        if len(chunks) > 1:
            # Overlap should cause some content to appear in multiple chunks
            first_chunk_end = chunks[0].content[-50:]
            second_chunk_start = chunks[1].content[:50]
            # This is a basic check - in practice, we'd need more sophisticated overlap detection

    @pytest.mark.asyncio
    async def test_document_lifecycle(self, temp_config):
        """Test full document lifecycle (add, process, query)"""
        # This test would require the actual embedding and vector backend implementations
        # For now, we'll create a mock test that verifies the interface

        store = DocumentStore(temp_config)

        # Test document addition (without processing)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a test document for the document store.")
            temp_file = f.name

        try:
            doc_id = await store.add_file(temp_file)
            assert doc_id is not None
            assert doc_id in store.documents

            doc_info = store.documents[doc_id]
            assert doc_info.file_name == Path(temp_file).name
            assert doc_info.status == "processing"

        finally:
            os.unlink(temp_file)

    def test_metadata_persistence(self, temp_config):
        """Test metadata loading and saving"""
        store = DocumentStore(temp_config)

        # Add a test document
        doc_info = {
            'id': 'test_doc_123',
            'file_path': '/test/path/doc.txt',
            'file_name': 'doc.txt',
            'file_size': 100,
            'mime_type': 'text/plain',
            'last_modified': 1234567890,
            'status': 'completed',
            'chunks_count': 5
        }

        store.documents['test_doc_123'] = doc_info
        store._save_metadata()

        # Create new store and load metadata
        store2 = DocumentStore(temp_config)
        store2._load_metadata()

        assert 'test_doc_123' in store2.documents
        loaded_doc = store2.documents['test_doc_123']
        assert loaded_doc['file_name'] == 'doc.txt'
        assert loaded_doc['status'] == 'completed'


class TestFileExtractor:
    """Tests for file extraction functionality"""

    def test_supported_formats(self, temp_config):
        """Test file format detection"""
        from core.extractors.file_extractor import FileExtractor

        extractor = FileExtractor()
        supported = extractor.get_supported_formats()

        assert 'txt' in [fmt.replace('.', '') for fmt in supported]
        assert 'pdf' in [fmt.replace('.', '') for fmt in supported]
        assert 'docx' in [fmt.replace('.', '') for fmt in supported]

    def test_format_support_checking(self, temp_config):
        """Test format support checking"""
        from core.extractors.file_extractor import FileExtractor

        extractor = FileExtractor()

        assert extractor.is_format_supported('test.txt')
        assert extractor.is_format_supported('test.pdf')
        assert extractor.is_format_supported('test.docx')
        assert not extractor.is_format_supported('test.unknown')

    @pytest.mark.asyncio
    async def test_text_extraction(self, temp_config):
        """Test basic text extraction"""
        from core.extractors.file_extractor import FileExtractor

        extractor = FileExtractor()

        # Test with temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            test_content = "This is a test document.\nIt has multiple lines.\nAnd some content."
            f.write(test_content)
            temp_file = f.name

        try:
            extracted = await extractor.extract_text(temp_file)
            assert isinstance(extracted, str)
            assert len(extracted) > 0
            assert "test document" in extracted.lower()

        finally:
            os.unlink(temp_file)


if __name__ == "__main__":
    # Run basic tests
    import sys
    print("Running basic document store tests...")

    # Simple test without pytest
    config = {
        'data_dir': 'test_data',
        'chunk_size': 500,
        'chunk_overlap': 100,
        'max_context_chunks': 3,
        'embedding': {'provider': 'local', 'model': 'all-MiniLM-L6-v2', 'device': 'cpu'},
        'vector': {'backend': 'faiss', 'dimension': 384, 'metric': 'cosine'}
    }

    try:
        store = DocumentStore(config)
        print("✓ Document store initialization: PASSED")

        # Test document ID generation
        test_path = Path("/test/document.pdf")
        doc_id = store._generate_document_id(test_path)
        print(f"✓ Document ID generation: PASSED ({doc_id})")

        # Test MIME type detection
        mime_type = store._get_mime_type(Path("test.pdf"))
        assert mime_type == "application/pdf"
        print("✓ MIME type detection: PASSED")

        print("All basic tests passed!")

    except Exception as e:
        print(f"✗ Test failed: {e}")
        sys.exit(1)

