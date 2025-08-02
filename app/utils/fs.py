import os
import re
from pathlib import Path
import shutil
import logging

logger = logging.getLogger(__name__)

def sanitize_filename(filename):
    """
    Sanitize a filename to be safe for filesystem use.
    Removes or replaces potentially dangerous characters.
    """
    if not filename:
        return "unnamed"
    
    # Remove or replace problematic characters
    # Keep alphanumeric, dash, underscore, and period
    sanitized = re.sub(r'[^\w\-_\.]', '_', str(filename))
    
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    
    # Ensure it's not empty
    if not sanitized:
        return "unnamed"
    
    # Limit length
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    
    # Ensure it doesn't start with a dot (hidden file)
    if sanitized.startswith('.'):
        sanitized = 'file_' + sanitized[1:]
    
    return sanitized

def ensure_directory(path):
    """
    Ensure a directory exists, creating it if necessary.
    Returns the Path object for the directory.
    """
    path_obj = Path(path)
    
    try:
        path_obj.mkdir(parents=True, exist_ok=True)
        return path_obj
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {str(e)}")
        raise

def safe_path_join(base_path, *paths):
    """
    Safely join paths, preventing directory traversal attacks.
    Returns None if the resulting path would be outside base_path.
    """
    try:
        base = Path(base_path).resolve()
        joined = base
        
        for path_part in paths:
            # Sanitize each path part
            sanitized_part = sanitize_filename(str(path_part))
            joined = joined / sanitized_part
        
        # Resolve the final path
        resolved = joined.resolve()
        
        # Ensure the resolved path is within the base path
        try:
            resolved.relative_to(base)
            return resolved
        except ValueError:
            # Path is outside base directory
            logger.warning(f"Attempted directory traversal: {joined}")
            return None
            
    except Exception as e:
        logger.error(f"Error in safe_path_join: {str(e)}")
        return None

def get_file_size_mb(file_path):
    """Get file size in megabytes"""
    try:
        return os.path.getsize(file_path) / (1024 * 1024)
    except OSError:
        return 0

def copy_file_safely(source, destination, overwrite=False):
    """
    Safely copy a file from source to destination.
    
    Args:
        source: Source file path
        destination: Destination file path
        overwrite: Whether to overwrite if destination exists
    
    Returns:
        dict with success status and any error message
    """
    try:
        source_path = Path(source)
        dest_path = Path(destination)
        
        # Check if source exists
        if not source_path.exists():
            return {'success': False, 'error': 'Source file does not exist'}
        
        # Check if destination exists and overwrite flag
        if dest_path.exists() and not overwrite:
            return {'success': False, 'error': 'Destination file already exists'}
        
        # Ensure destination directory exists
        ensure_directory(dest_path.parent)
        
        # Copy the file
        shutil.copy2(source_path, dest_path)
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Failed to copy file from {source} to {destination}: {str(e)}")
        return {'success': False, 'error': str(e)}

def move_file_safely(source, destination, overwrite=False):
    """
    Safely move a file from source to destination.
    """
    try:
        source_path = Path(source)
        dest_path = Path(destination)
        
        # Check if source exists
        if not source_path.exists():
            return {'success': False, 'error': 'Source file does not exist'}
        
        # Check if destination exists and overwrite flag
        if dest_path.exists() and not overwrite:
            return {'success': False, 'error': 'Destination file already exists'}
        
        # Ensure destination directory exists
        ensure_directory(dest_path.parent)
        
        # Move the file
        shutil.move(str(source_path), str(dest_path))
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Failed to move file from {source} to {destination}: {str(e)}")
        return {'success': False, 'error': str(e)}

def delete_file_safely(file_path):
    """
    Safely delete a file.
    """
    try:
        path_obj = Path(file_path)
        
        if not path_obj.exists():
            return {'success': True, 'message': 'File does not exist'}
        
        if path_obj.is_file():
            path_obj.unlink()
            return {'success': True}
        else:
            return {'success': False, 'error': 'Path is not a file'}
            
    except Exception as e:
        logger.error(f"Failed to delete file {file_path}: {str(e)}")
        return {'success': False, 'error': str(e)}

def clean_old_files(directory, days_old=30, pattern="*"):
    """
    Clean up old files in a directory.
    
    Args:
        directory: Directory to clean
        days_old: Files older than this many days will be deleted
        pattern: File pattern to match (default: all files)
    
    Returns:
        dict with cleanup statistics
    """
    try:
        dir_path = Path(directory)
        
        if not dir_path.exists():
            return {'success': True, 'deleted_count': 0, 'message': 'Directory does not exist'}
        
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        deleted_count = 0
        for file_path in dir_path.glob(pattern):
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_date:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete old file {file_path}: {str(e)}")
        
        return {
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Deleted {deleted_count} old files'
        }
        
    except Exception as e:
        logger.error(f"Failed to clean old files in {directory}: {str(e)}")
        return {'success': False, 'error': str(e)}

def get_directory_size(directory):
    """
    Get the total size of a directory in bytes.
    """
    try:
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except OSError:
                    # File might have been deleted or is inaccessible
                    pass
        return total_size
    except Exception as e:
        logger.error(f"Failed to calculate directory size for {directory}: {str(e)}")
        return 0

def validate_file_extension(filename, allowed_extensions):
    """
    Validate that a filename has an allowed extension.
    
    Args:
        filename: The filename to validate
        allowed_extensions: List of allowed extensions (with or without dots)
    
    Returns:
        bool: True if extension is allowed
    """
    if not filename or not allowed_extensions:
        return False
    
    file_ext = Path(filename).suffix.lower()
    
    # Normalize extensions (ensure they start with a dot)
    normalized_extensions = []
    for ext in allowed_extensions:
        if not ext.startswith('.'):
            ext = '.' + ext
        normalized_extensions.append(ext.lower())
    
    return file_ext in normalized_extensions

def read_file_safely(file_path, encoding='utf-8', max_size_mb=10):
    """
    Safely read a file with size and encoding checks.
    
    Args:
        file_path: Path to the file
        encoding: File encoding (default: utf-8)
        max_size_mb: Maximum file size in MB
    
    Returns:
        dict with success status and content or error
    """
    try:
        path_obj = Path(file_path)
        
        if not path_obj.exists():
            return {'success': False, 'error': 'File does not exist'}
        
        if not path_obj.is_file():
            return {'success': False, 'error': 'Path is not a file'}
        
        # Check file size
        size_mb = get_file_size_mb(file_path)
        if size_mb > max_size_mb:
            return {
                'success': False, 
                'error': f'File too large ({size_mb:.1f}MB). Maximum allowed: {max_size_mb}MB'
            }
        
        # Read the file
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        
        return {'success': True, 'content': content}
        
    except UnicodeDecodeError as e:
        return {'success': False, 'error': f'Encoding error: {str(e)}'}
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {str(e)}")
        return {'success': False, 'error': str(e)}

def write_file_safely(file_path, content, encoding='utf-8', backup=True):
    """
    Safely write content to a file with optional backup.
    
    Args:
        file_path: Path to the file
        content: Content to write
        encoding: File encoding (default: utf-8)
        backup: Whether to create a backup of existing file
    
    Returns:
        dict with success status and any error message
    """
    try:
        path_obj = Path(file_path)
        
        # Ensure directory exists
        ensure_directory(path_obj.parent)
        
        # Create backup if file exists and backup is requested
        if backup and path_obj.exists():
            backup_path = path_obj.with_suffix(path_obj.suffix + '.backup')
            shutil.copy2(path_obj, backup_path)
        
        # Write the content
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Failed to write file {file_path}: {str(e)}")
        return {'success': False, 'error': str(e)}
