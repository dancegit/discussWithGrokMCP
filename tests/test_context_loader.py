"""
Tests for the enhanced ContextLoader with directory and pattern support.
"""

import pytest
import tempfile
import os
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.tools.context_loader import ContextLoader


class TestContextLoader:
    """Test suite for ContextLoader functionality."""
    
    @pytest.fixture
    def test_directory(self):
        """Create a temporary directory with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            test_files = {
                'file1.py': 'print("Hello from file1")\n# Line 2\n# Line 3\n',
                'file2.txt': 'Text file content\nLine 2 of text\nLine 3 of text\n',
                'file3.md': '# Markdown\n## Section\nContent here\n',
                'subdir/file4.py': 'def function():\n    pass\n',
                'subdir/file5.js': 'console.log("JavaScript");\n',
                'subdir/deep/file6.py': 'import os\n# Deep file\n',
                'test_file.py': 'import pytest\n# Test file\n',
                'config.json': '{"key": "value"}\n',
                'data.csv': 'col1,col2\nval1,val2\n',
                'ignore.pyc': 'compiled python\n',
                '__pycache__/cache.py': 'cache file\n'
            }
            
            for filepath, content in test_files.items():
                full_path = Path(tmpdir) / filepath
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
            
            yield tmpdir
    
    def test_load_single_file(self, test_directory):
        """Test loading a single file."""
        file_path = os.path.join(test_directory, 'file1.py')
        context, metadata = ContextLoader.load_context([file_path])
        
        assert 'Hello from file1' in context
        assert metadata['files_processed'] == 1
        assert metadata['total_lines'] == 3
    
    def test_load_file_with_line_range(self, test_directory):
        """Test loading a file with specific line range."""
        file_path = os.path.join(test_directory, 'file1.py')
        spec = {'path': file_path, 'from': 2, 'to': 3}
        
        context, metadata = ContextLoader.load_context([spec])
        
        assert 'Hello from file1' not in context  # Line 1 excluded
        assert '# Line 2' in context
        assert '# Line 3' in context
        assert metadata['files_processed'] == 1
        assert metadata['total_lines'] == 2
    
    def test_load_directory_non_recursive(self, test_directory):
        """Test loading files from a directory non-recursively."""
        spec = {
            'path': test_directory,
            'recursive': False,
            'extensions': ['.py', '.txt']
        }
        
        context, metadata = ContextLoader.load_context([spec])
        
        # Should include file1.py and file2.txt but not subdir files
        assert 'Hello from file1' in context
        assert 'Text file content' in context
        assert 'def function()' not in context  # subdir/file4.py excluded
        assert metadata['files_processed'] == 3  # file1.py, file2.txt, test_file.py
    
    def test_load_directory_recursive(self, test_directory):
        """Test loading files from a directory recursively."""
        spec = {
            'path': test_directory,
            'recursive': True,
            'extensions': ['.py']
        }
        
        context, metadata = ContextLoader.load_context([spec])
        
        # Should include all .py files recursively
        assert 'Hello from file1' in context
        assert 'def function()' in context  # subdir/file4.py included
        assert 'import os' in context  # subdir/deep/file6.py included
        assert 'import pytest' in context  # test_file.py included
        assert 'Text file content' not in context  # .txt excluded
        assert 'console.log' not in context  # .js excluded
        assert metadata['files_processed'] == 4  # All .py files
    
    def test_glob_pattern(self, test_directory):
        """Test loading files using glob patterns."""
        pattern = os.path.join(test_directory, '**/*.py')
        
        context, metadata = ContextLoader.load_context([pattern])
        
        # Should include all .py files
        assert 'Hello from file1' in context
        assert 'def function()' in context
        assert 'import os' in context
        assert metadata['files_processed'] == 4
    
    def test_mixed_specifications(self, test_directory):
        """Test mixing different types of file specifications."""
        specs = [
            os.path.join(test_directory, 'file1.py'),  # Single file
            {
                'path': os.path.join(test_directory, 'file2.txt'),
                'from': 1,
                'to': 2
            },  # File with line range
            {
                'path': os.path.join(test_directory, 'subdir'),
                'recursive': False,
                'extensions': ['.js']
            },  # Directory non-recursive
            os.path.join(test_directory, '*.md')  # Glob pattern
        ]
        
        context, metadata = ContextLoader.load_context(specs)
        
        assert 'Hello from file1' in context
        assert 'Text file content' in context
        assert 'console.log' in context
        assert '# Markdown' in context
        assert metadata['files_processed'] == 4
    
    def test_exclude_patterns(self, test_directory):
        """Test excluding files based on patterns."""
        spec = {
            'path': test_directory,
            'recursive': True,
            'extensions': ['.py'],
            'exclude': ['test_*', '__pycache__']
        }
        
        context, metadata = ContextLoader.load_context([spec])
        
        # Should exclude test_file.py and __pycache__ files
        assert 'Hello from file1' in context
        assert 'def function()' in context
        assert 'import pytest' not in context  # test_file.py excluded
        assert 'cache file' not in context  # __pycache__ excluded
        assert metadata['files_processed'] == 3  # file1.py, file4.py, file6.py
    
    def test_context_type_extensions(self, test_directory):
        """Test automatic extension selection based on context type."""
        # Code context should select code files
        context, metadata = ContextLoader.load_context(
            [test_directory],
            context_type='code'
        )
        
        assert 'Hello from file1' in context  # .py included
        assert 'console.log' in context  # .js included
        assert '# Markdown' not in context  # .md excluded
        
        # Docs context should select documentation files
        context, metadata = ContextLoader.load_context(
            [test_directory],
            context_type='docs'
        )
        
        assert '# Markdown' in context  # .md included
        assert 'Text file content' in context  # .txt included
        assert 'Hello from file1' not in context  # .py excluded
    
    def test_max_lines_per_file(self, test_directory):
        """Test max lines per file limit."""
        file_path = os.path.join(test_directory, 'file1.py')
        
        context, metadata = ContextLoader.load_context(
            [file_path],
            max_lines_per_file=2
        )
        
        assert 'Hello from file1' in context
        assert '# Line 2' in context
        assert '# Line 3' not in context  # Truncated
        assert 'truncated' in context.lower()
    
    def test_max_total_lines(self, test_directory):
        """Test max total lines limit across all files."""
        spec = {
            'path': test_directory,
            'recursive': True,
            'extensions': ['.py', '.txt', '.md']
        }
        
        context, metadata = ContextLoader.load_context(
            [spec],
            max_total_lines=5
        )
        
        assert metadata['total_lines'] <= 5
        assert len(metadata['skipped_files']) > 0
    
    def test_nonexistent_file(self, test_directory):
        """Test handling of nonexistent files."""
        context, metadata = ContextLoader.load_context(
            ['/nonexistent/file.txt']
        )
        
        assert metadata['files_processed'] == 0
        assert context == ''
    
    def test_empty_directory(self):
        """Test handling of empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            context, metadata = ContextLoader.load_context([tmpdir])
            
            assert metadata['files_processed'] == 0
            assert context == ''
    
    def test_binary_file_handling(self, test_directory):
        """Test handling of binary files."""
        # Create a binary file
        binary_path = Path(test_directory) / 'binary.bin'
        binary_path.write_bytes(b'\x00\x01\x02\x03')
        
        context, metadata = ContextLoader.load_context([str(binary_path)])
        
        # Should handle binary file gracefully
        assert metadata['files_processed'] == 1
        # Content might be garbled but shouldn't crash
    
    def test_large_file_truncation(self, test_directory):
        """Test truncation of large files."""
        # Create a large file
        large_file = Path(test_directory) / 'large.txt'
        lines = [f'Line {i}\n' for i in range(1000)]
        large_file.write_text(''.join(lines))
        
        context, metadata = ContextLoader.load_context(
            [str(large_file)],
            max_lines_per_file=50
        )
        
        assert 'Line 0' in context
        assert 'Line 49' in context
        assert 'Line 50' not in context
        assert 'truncated' in context.lower()
        assert metadata['total_lines'] == 50
    
    def test_pattern_in_spec_dict(self, test_directory):
        """Test using pattern field in specification dict."""
        spec = {
            'path': test_directory,
            'pattern': '**/*.md'
        }
        
        context, metadata = ContextLoader.load_context([spec])
        
        assert '# Markdown' in context
        assert metadata['files_processed'] == 1
    
    def test_invalid_specifications(self, test_directory):
        """Test handling of invalid specifications."""
        specs = [
            123,  # Invalid type
            {'invalid': 'spec'},  # Missing 'path'
            None,  # None value
        ]
        
        for spec in specs:
            context, metadata = ContextLoader.load_context([spec])
            # Should handle gracefully without crashing
            assert isinstance(context, str)
            assert isinstance(metadata, dict)


@pytest.mark.asyncio
async def test_with_actual_tools():
    """Test ContextLoader integration with actual tools."""
    from lib import GrokClient
    from lib.tools import AskWithContextTool, DiscussTool, SessionManager
    
    # Create mock client
    class MockGrokClient:
        async def ask(self, prompt, stream=False):
            from lib.grok_client import GrokResponse
            return GrokResponse(
                content="Test response",
                tokens_used=10,
                model="test",
                timestamp=0,
                streaming=False
            )
        
        async def ask_with_history(self, messages, stream=False):
            from lib.grok_client import GrokResponse
            return GrokResponse(
                content="Test response with history",
                tokens_used=20,
                model="test",
                timestamp=0,
                streaming=False
            )
    
    client = MockGrokClient()
    
    # Test with AskWithContextTool
    tool = AskWithContextTool(client)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        file1 = Path(tmpdir) / 'test.py'
        file1.write_text('def test():\n    pass\n')
        
        subdir = Path(tmpdir) / 'subdir'
        subdir.mkdir()
        file2 = subdir / 'test2.py'
        file2.write_text('import os\n')
        
        # Test with directory
        result = await tool.execute(
            question="What does this code do?",
            context_files=[tmpdir],
            context_type="code"
        )
        
        assert "Test response" in result
        assert "2 files" in result or "Context:" in result
        
        # Test with DiscussTool
        session_manager = SessionManager(Path(tmpdir) / 'sessions')
        discuss_tool = DiscussTool(client, session_manager)
        
        result = await discuss_tool.execute(
            topic="Code review",
            context_files=[
                tmpdir,
                {'path': str(file1), 'from': 1, 'to': 1}
            ],
            max_turns=1,
            paginate=False
        )
        
        assert "Code review" in result
        assert "Session ID" in result


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])