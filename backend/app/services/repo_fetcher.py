import shutil
import tempfile

from git import Repo

from app.utils.errors import DevBrainException


def clone_github_repo(full_name: str, token: str, branch: str) -> str:
    """Shallow-clone a GitHub repo; returns temp directory path."""
    temp_dir = tempfile.mkdtemp(prefix="devbrain_")
    url = f"https://x-access-token:{token}@github.com/{full_name}.git"
    try:
        Repo.clone_from(url, temp_dir, branch=branch, depth=1)
        return temp_dir
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise DevBrainException(
            f"Failed to clone repository: {e}",
            status_code=502,
            code="CLONE_FAILED",
        ) from e


def cleanup_clone(path: str) -> None:
    shutil.rmtree(path, ignore_errors=True)
