import sys
import os
import pytest
import logging
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.worker_engine import WorkerEngine

# Mock internal dependencies to avoid side effects (file system, network)
@pytest.fixture
def mock_engine():
    with patch("core.worker_engine.QSettings") as mock_settings:
        # Mock settings to avoid registry access
        mock_settings.return_value.value.return_value = "" 
        
        # Instantiate engine with a mock progress callback
        engine = WorkerEngine(api_key="test_key", progress_callback=MagicMock())
        
        # Redirect logger to capture logs for inspection
        engine.logger = logging.getLogger("TestWorkerEngine")
        engine.logger.setLevel(logging.INFO) # Fix: Set level to INFO to capture info logs
        engine.logger.handlers = [] # Clear handlers
        
        return engine

def test_sanitize_filename_basics(mock_engine):
    assert mock_engine.sanitize_filename("valid_file.txt") == "valid_file.txt"
    assert mock_engine.sanitize_filename("invalid/file.txt") == "invalid_file.txt"
    # Strict sanitizer collapses .. -> . and strips leading . so it becomes parent.txt
    assert mock_engine.sanitize_filename("..\\parent.txt") == "parent.txt" 
    assert mock_engine.sanitize_filename("file with spaces.txt") == "file_with_spaces.txt"
    
def test_sanitize_filename_injection(mock_engine):
    # Test strict sanitization for fixit.md #3
    dangerous = "../../etc/passwd"
    safe = mock_engine.sanitize_filename(dangerous)
    assert ".." not in safe
    assert "/" not in safe
    assert "\\" not in safe

class MockLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = []
    def emit(self, record):
        self.messages.append(self.format(record))

def test_log_sanitization(mock_engine):
    # Setup log capture
    handler = MockLogHandler()
    mock_engine.logger.addHandler(handler)
    
    # Test fixit.md #1
    secret_key = "AIzaSySecretKey"
    mock_engine.api_key = secret_key # Engine only sanitizes its own key
    mock_engine.log_and_progress(f"Using key: {secret_key}")
    
    # Check if key is masked in the log
    log_content = handler.messages[0]
    assert "Using key:" in log_content
    assert secret_key not in log_content # Key should NOT be visible

