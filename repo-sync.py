"""
Synchronizes shared content between Python Social Auth repositories.

Execute: uv run repo-sync.py
"""
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "termcolor==2.5.0",
# ]
# ///

from __future__ import annotations

import subprocess
from pathlib import Path
from shutil import copyfile

from termcolor import colored

REPOSITORIES = (
    # Core has to be the first as it is used to update some of the files
    "social-core",
    "social-app-django",
    ".github",
)
ROOT = Path(__file__).parent
REPOS = ROOT / "repos"
COPY_FROM_BASE = (
    ".pre-commit-config.yaml",
    ".github/renovate.json",
)
COMMIT_MESSAGE = """chore: update shared files

Automated update of shared files from the social-core repository.
"""


def highlight(value: str) -> str:
    """Highlight string for terminal output."""
    return colored(value, "cyan")


class Repository:
    """Repository wrapper class to handle updates."""

    def __init__(self, name: str, base: Path) -> None:
        """Repository initiliazition."""
        self.name = name
        self.directory = REPOS / name
        self.base = base

    def run(
        self, args: list[str], *, cwd: Path | None = None, check: bool = True
    ) -> subprocess.CompletedProcess:
        """Execute a process in repository."""
        if cwd is None:
            cwd = self.directory
        return subprocess.run(args, cwd=cwd, check=check)

    def checkout(self) -> None:
        """Checkout or update working copy."""
        if self.directory.exists():
            print(f"Updating {highlight(self.name)}...")
            # Update
            self.run(["git", "reset", "--quiet", "--hard", "origin/HEAD"])
            self.run(["git", "remote", "prune", "origin"])
            subprocess.run(["git", "pull", "--quiet"], check=False)
        else:
            print(f"Cloning {highlight(self.name)}...")
            # Initial checkout
            REPOS.mkdir(exist_ok=True)
            self.run(
                ["git", "clone", f"git@github.com:python-social-auth/{self.name}.git"],
                cwd=REPOS,
            )

    def update_files(self) -> None:
        """Update files from the base repository."""
        if self.base == self.directory:
            return
        for name in COPY_FROM_BASE:
            copyfile(self.base / name, self.directory / name)

    def commit(self) -> None:
        """Commit and push pending changes."""
        self.run(["git", "add", "."])
        if self.run(["git", "diff", "--cached", "--exit-code"], check=False).returncode:
            print(f"Committing {highlight(self.name)}...")
            self.run(["git", "commit", "-m", COMMIT_MESSAGE])
            self.run(["git", "push"])


def main() -> None:
    """Update all repositories."""
    # Base repository (social-core)
    base = REPOS / REPOSITORIES[0]

    # Update repos
    for name in REPOSITORIES:
        repo = Repository(name, base)
        repo.checkout()
        repo.update_files()
        repo.commit()


if __name__ == "__main__":
    main()
