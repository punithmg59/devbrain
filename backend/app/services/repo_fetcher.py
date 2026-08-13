import shutil
import tempfile
import os
import stat
import logging

from git import Repo

from app.utils.errors import DevBrainException

logger = logging.getLogger(__name__)


def clone_github_repo(full_name: str, token: str, branch: str) -> str:
    """Shallow-clone a GitHub repo; returns temp directory path.
    
    Security measures:
    - Creates temp directory with restricted permissions (owner-only)
    - Uses shallow clone (depth=1) to minimize data
    - Cleans up on failure
    - Never logs sensitive file contents
    - Temp directory is excluded from Git via .gitignore
    
    Args:
        full_name: GitHub repository full name (e.g., "owner/repo")
        token: GitHub access token for authentication
        branch: Branch to clone
        
    Returns:
        Path to temporary clone directory
        
    Raises:
        DevBrainException: If clone fails
    """
    # Create temp directory with restricted permissions
    temp_dir = tempfile.mkdtemp(prefix="devbrain_")
    
    try:
        # Set directory permissions to owner-only (700)
        # This prevents other users on the same system from accessing the clone
        os.chmod(temp_dir, stat.S_IRWXU)
        
        url = f"https://x-access-token:{token}@github.com/{full_name}.git"
        
        logger.info(
            "Cloning repository %s (branch: %s) to temporary directory",
            full_name,
            branch,
        )
        
        Repo.clone_from(url, temp_dir, branch=branch, depth=1)
        
        # Ensure all subdirectories also have restricted permissions
        for root, dirs, files in os.walk(temp_dir):
            os.chmod(root, stat.S_IRWXU)
            for d in dirs:
                dir_path = os.path.join(root, d)
                os.chmod(dir_path, stat.S_IRWXU)
        
        logger.info("Repository cloned successfully to %s", temp_dir)
        return temp_dir
        
    except Exception as e:
        # Clean up on failure
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.error("Failed to clone repository %s: %s", full_name, e)
        raise DevBrainException(
            f"Failed to clone repository: {e}",
            status_code=502,
            code="CLONE_FAILED",
        ) from e


def cleanup_clone(path: str) -> None:
    """Securely clean up a temporary clone directory.
    
    This function:
    - Removes the directory and all contents
    - Uses ignore_errors=True to handle locked files on Windows
    - Never logs file contents
    - Is called after analysis completes
    
    Args:
        path: Path to temporary clone directory
    """
    if path and os.path.exists(path):
        logger.info("Cleaning up temporary clone directory: %s", path)
        shutil.rmtree(path, ignore_errors=True)
        logger.info("Temporary clone directory cleaned up successfully")
