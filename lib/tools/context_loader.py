"""
Enhanced context loader with support for directories, patterns, and file filtering.
"""

import os
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
import logging

logger = logging.getLogger(__name__)


class ContextLoader:
    """Handles loading context from files, directories, and patterns."""
    
    # Default file extensions to include when processing directories
    DEFAULT_EXTENSIONS = {
        'code': ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp', 
                 '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.r', '.m'],
        'docs': ['.md', '.txt', '.rst', '.adoc', '.tex', '.org'],
        'config': ['.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.xml'],
        'web': ['.html', '.htm', '.css', '.scss', '.sass', '.less'],
        'data': ['.csv', '.tsv', '.sql'],
        'all': []  # Empty means all files
    }
    
    # Files/directories to always exclude
    EXCLUDE_PATTERNS = {
        '__pycache__', '.git', '.svn', '.hg', 'node_modules', '.venv', 'venv',
        'env', '.env', '*.pyc', '*.pyo', '*.pyd', '.DS_Store', 'Thumbs.db',
        '*.egg-info', 'dist', 'build', '.pytest_cache', '.mypy_cache',
        '.coverage', 'htmlcov', '.tox', '.idea', '.vscode', '*.swp', '*.swo'
    }
    
    @classmethod
    def load_context(
        cls,
        file_specs: List[Union[str, Dict[str, Any]]],
        max_lines_per_file: int = 100,
        max_total_lines: int = 10000,
        context_type: str = 'general'
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Load context from various file specifications.
        
        Args:
            file_specs: List of file specifications, can be:
                - String path to a file or directory
                - Dict with keys:
                    - path: str (required) - file, directory, or glob pattern
                    - from: int (optional) - start line for files
                    - to: int (optional) - end line for files
                    - recursive: bool (optional) - for directories
                    - extensions: List[str] (optional) - file extensions to include
                    - exclude: List[str] (optional) - patterns to exclude
                    - pattern: str (optional) - glob pattern for matching files
            max_lines_per_file: Maximum lines to include per file
            max_total_lines: Maximum total lines across all files
            context_type: Type of context ('code', 'docs', 'general', etc.)
            
        Returns:
            Tuple of (context_string, metadata_dict)
        """
        context_parts = []
        metadata = {
            'files_processed': 0,
            'total_lines': 0,
            'skipped_files': [],
            'errors': []
        }
        total_lines = 0
        
        for spec in file_specs:
            if total_lines >= max_total_lines:
                metadata['skipped_files'].append(f"Remaining files (max lines reached)")
                break
                
            try:
                files_to_process = cls._resolve_file_spec(spec, context_type)
                
                for file_info in files_to_process:
                    if total_lines >= max_total_lines:
                        metadata['skipped_files'].append(file_info['path'])
                        continue
                        
                    file_path = file_info['path']
                    from_line = file_info.get('from')
                    to_line = file_info.get('to')
                    
                    # Load the file content
                    content, lines_read = cls._load_file_content(
                        file_path, 
                        from_line, 
                        to_line,
                        max_lines_per_file,
                        max_total_lines - total_lines
                    )
                    
                    if content:
                        # Add file header
                        header = f"\n--- File: {file_path}"
                        if from_line or to_line:
                            header += f" (lines {from_line or 1}-{to_line or lines_read})"
                        header += " ---\n"
                        
                        context_parts.append(header + content)
                        metadata['files_processed'] += 1
                        total_lines += lines_read
                        metadata['total_lines'] = total_lines
                    
            except Exception as e:
                logger.error(f"Error processing spec {spec}: {e}")
                metadata['errors'].append(f"Error with {spec}: {str(e)}")
        
        context = "\n".join(context_parts)
        return context, metadata
    
    @classmethod
    def _resolve_file_spec(
        cls,
        spec: Union[str, Dict[str, Any]],
        context_type: str
    ) -> List[Dict[str, Any]]:
        """
        Resolve a file specification to a list of file paths with metadata.
        
        Returns:
            List of dicts with 'path' and optional 'from'/'to' keys
        """
        if isinstance(spec, str):
            # Simple string path
            path = Path(spec)
            
            if '*' in spec or '?' in spec or '[' in spec:
                # It's a glob pattern
                return cls._resolve_glob_pattern(spec)
            elif path.is_file():
                # Single file
                return [{'path': str(path)}]
            elif path.is_dir():
                # Directory - use default extensions for context type
                extensions = cls.DEFAULT_EXTENSIONS.get(context_type, cls.DEFAULT_EXTENSIONS['all'])
                # For string directories, use recursive=True by default
                return cls._resolve_directory(str(path), recursive=True, extensions=extensions)
            else:
                logger.warning(f"Path not found: {spec}")
                return []
                
        elif isinstance(spec, dict):
            path = spec.get('path', '')
            
            if not path:
                logger.warning("No path specified in file spec")
                return []
            
            # Check for explicit pattern field
            pattern = spec.get('pattern')
            if pattern:
                # Pattern is relative to the path
                base_path = path if Path(path).is_dir() else '.'
                full_pattern = os.path.join(base_path, pattern)
                return cls._resolve_glob_pattern(full_pattern)
            
            # Check for glob pattern in the path itself
            if '*' in path or '?' in path or '[' in path:
                return cls._resolve_glob_pattern(path)
            
            path_obj = Path(path)
            
            if path_obj.is_file():
                # Single file with optional line ranges
                return [{
                    'path': str(path_obj),
                    'from': spec.get('from'),
                    'to': spec.get('to')
                }]
            elif path_obj.is_dir():
                # Directory with options
                recursive = spec.get('recursive', True)
                extensions = spec.get('extensions', 
                                     cls.DEFAULT_EXTENSIONS.get(context_type, cls.DEFAULT_EXTENSIONS['all']))
                exclude = spec.get('exclude', [])
                
                return cls._resolve_directory(
                    str(path_obj),
                    recursive=recursive,
                    extensions=extensions,
                    exclude=exclude
                )
            else:
                logger.warning(f"Path not found: {path}")
                return []
        
        return []
    
    @classmethod
    def _resolve_directory(
        cls,
        directory: str,
        recursive: bool = True,
        extensions: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Resolve a directory to a list of file paths.
        """
        files = []
        exclude_patterns = set(cls.EXCLUDE_PATTERNS)
        if exclude:
            exclude_patterns.update(exclude)
        
        for root, dirs, filenames in os.walk(directory):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not cls._should_exclude(d, exclude_patterns)]
            
            for filename in filenames:
                # Check if file should be excluded
                if cls._should_exclude(filename, exclude_patterns):
                    continue
                
                # Check extension if specified
                if extensions and not any(filename.endswith(ext) for ext in extensions):
                    continue
                
                file_path = os.path.join(root, filename)
                files.append({'path': file_path})
            
            if not recursive:
                break
        
        return files
    
    @classmethod
    def _resolve_glob_pattern(cls, pattern: str) -> List[Dict[str, Any]]:
        """
        Resolve a glob pattern to a list of file paths.
        """
        files = []
        for path in glob.glob(pattern, recursive=True):
            if os.path.isfile(path):
                # Check if it should be excluded
                if not cls._should_exclude(path, cls.EXCLUDE_PATTERNS):
                    files.append({'path': path})
        return files
    
    @classmethod
    def _should_exclude(cls, path: str, exclude_patterns: set) -> bool:
        """
        Check if a path should be excluded based on patterns.
        """
        path_parts = Path(path).parts
        
        for pattern in exclude_patterns:
            # Check exact match
            if any(part == pattern for part in path_parts):
                return True
            
            # Check wildcard patterns
            if '*' in pattern:
                import fnmatch
                if fnmatch.fnmatch(os.path.basename(path), pattern):
                    return True
        
        return False
    
    @classmethod
    def _load_file_content(
        cls,
        file_path: str,
        from_line: Optional[int] = None,
        to_line: Optional[int] = None,
        max_lines: int = 100,
        remaining_total: int = None
    ) -> Tuple[str, int]:
        """
        Load content from a file with optional line range.
        
        Returns:
            Tuple of (content_string, lines_read)
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Apply line range if specified
            if from_line is not None:
                from_idx = max(0, from_line - 1)  # Convert to 0-based index
            else:
                from_idx = 0
            
            if to_line is not None:
                to_idx = min(len(lines), to_line)  # to_line is inclusive
            else:
                to_idx = len(lines)
            
            lines = lines[from_idx:to_idx]
            
            # Apply max lines limit
            if len(lines) > max_lines:
                truncated_lines = lines[:max_lines]
                truncated_lines.append("... (truncated, showing first {} lines)\n".format(max_lines))
                lines = truncated_lines
            
            # Apply remaining total limit if specified
            if remaining_total is not None and len(lines) > remaining_total:
                lines = lines[:remaining_total]
                lines.append("... (truncated due to total line limit)\n")
            
            # Count actual content lines (not truncation messages)
            actual_lines = [l for l in lines if not l.startswith('...')]
            content = ''.join(lines)
            lines_read = len(actual_lines)
            
            return content, lines_read
            
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return f"Error reading file: {str(e)}\n", 0