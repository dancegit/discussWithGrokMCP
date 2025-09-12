#!/usr/bin/env python3
"""
Demo script showing the new enhanced context loading capabilities.
"""

import asyncio
import tempfile
from pathlib import Path
import sys

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib.tools.context_loader import ContextLoader


async def main():
    """Demonstrate various context loading capabilities."""
    
    print("=" * 60)
    print("MCP Server Enhanced Context Loading Demo")
    print("=" * 60)
    
    # Create demo directory structure
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample files
        print(f"\n📁 Creating demo files in {tmpdir}...")
        
        # Python files
        (Path(tmpdir) / "main.py").write_text(
            "def main():\n    print('Hello World')\n\nif __name__ == '__main__':\n    main()\n"
        )
        
        (Path(tmpdir) / "utils.py").write_text(
            "def helper():\n    return 42\n"
        )
        
        # Create subdirectory
        subdir = Path(tmpdir) / "tests"
        subdir.mkdir()
        
        (subdir / "test_main.py").write_text(
            "import pytest\n\ndef test_main():\n    assert True\n"
        )
        
        (subdir / "test_utils.py").write_text(
            "from utils import helper\n\ndef test_helper():\n    assert helper() == 42\n"
        )
        
        # Documentation
        (Path(tmpdir) / "README.md").write_text(
            "# Demo Project\n\nThis is a demo.\n"
        )
        
        # Config file
        (Path(tmpdir) / "config.json").write_text(
            '{"version": "1.0.0", "debug": true}\n'
        )
        
        print("✅ Demo files created")
        
        # Demo 1: Load a single file
        print("\n" + "-" * 40)
        print("Demo 1: Load a single file")
        print("-" * 40)
        context, metadata = ContextLoader.load_context([str(Path(tmpdir) / "main.py")])
        print(f"Loaded {metadata['files_processed']} file(s), {metadata['total_lines']} lines")
        print("Content preview:", context[:100] + "...")
        
        # Demo 2: Load entire directory
        print("\n" + "-" * 40)
        print("Demo 2: Load entire directory (recursive)")
        print("-" * 40)
        context, metadata = ContextLoader.load_context([tmpdir])
        print(f"Loaded {metadata['files_processed']} file(s), {metadata['total_lines']} lines")
        
        # Demo 3: Load only Python files
        print("\n" + "-" * 40)
        print("Demo 3: Load only Python files")
        print("-" * 40)
        spec = {
            "path": tmpdir,
            "recursive": True,
            "extensions": [".py"]
        }
        context, metadata = ContextLoader.load_context([spec])
        print(f"Loaded {metadata['files_processed']} Python file(s), {metadata['total_lines']} lines")
        
        # Demo 4: Use glob pattern
        print("\n" + "-" * 40)
        print("Demo 4: Use glob pattern for test files")
        print("-" * 40)
        pattern = str(Path(tmpdir) / "**" / "test_*.py")
        context, metadata = ContextLoader.load_context([pattern])
        print(f"Loaded {metadata['files_processed']} test file(s), {metadata['total_lines']} lines")
        
        # Demo 5: Load with line ranges
        print("\n" + "-" * 40)
        print("Demo 5: Load specific line ranges")
        print("-" * 40)
        spec = {
            "path": str(Path(tmpdir) / "main.py"),
            "from": 1,
            "to": 2
        }
        context, metadata = ContextLoader.load_context([spec])
        print(f"Loaded lines 1-2 from main.py:")
        print(context)
        
        # Demo 6: Mixed specifications
        print("\n" + "-" * 40)
        print("Demo 6: Mixed specifications")
        print("-" * 40)
        specs = [
            str(Path(tmpdir) / "README.md"),  # Single file
            {
                "path": str(Path(tmpdir) / "main.py"),
                "from": 1,
                "to": 2
            },  # File with line range
            {
                "path": str(Path(tmpdir) / "tests"),
                "recursive": False,
                "extensions": [".py"]
            }  # Directory with filters
        ]
        context, metadata = ContextLoader.load_context(specs)
        print(f"Loaded {metadata['files_processed']} file(s) using mixed specs")
        
        # Demo 7: Context type auto-detection
        print("\n" + "-" * 40)
        print("Demo 7: Context type auto-detection")
        print("-" * 40)
        
        # Code context
        context, metadata = ContextLoader.load_context(
            [tmpdir],
            context_type='code'
        )
        print(f"Code context: {metadata['files_processed']} file(s)")
        
        # Docs context
        context, metadata = ContextLoader.load_context(
            [tmpdir],
            context_type='docs'
        )
        print(f"Docs context: {metadata['files_processed']} file(s)")
        
        # Demo 8: Exclude patterns
        print("\n" + "-" * 40)
        print("Demo 8: Exclude test files")
        print("-" * 40)
        spec = {
            "path": tmpdir,
            "recursive": True,
            "extensions": [".py"],
            "exclude": ["test_*"]
        }
        context, metadata = ContextLoader.load_context([spec])
        print(f"Loaded {metadata['files_processed']} non-test Python file(s)")
        
    print("\n" + "=" * 60)
    print("Demo complete! 🎉")
    print("=" * 60)
    
    print("\n📝 Usage in MCP tools:")
    print("""
    # In grok_discuss, grok_ask_with_context, or grok_continue_session:
    
    context_files = [
        "src/",                            # Load entire directory
        "**/*.py",                         # All Python files
        {"path": "main.py", "from": 1, "to": 100},  # Specific lines
        {
            "path": "tests/",
            "recursive": true,
            "extensions": [".py"],
            "exclude": ["__pycache__"]
        }
    ]
    """)


if __name__ == "__main__":
    asyncio.run(main())