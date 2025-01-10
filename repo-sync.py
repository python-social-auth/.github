# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "termcolor==2.5.0",
# ]
# ///

from __future__ import annotations
import subprocess
from pathlib import Path
from termcolor import colored
from shutil import copyfile

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
    return colored(value, "cyan")


class Repository:
    def __init__(self, name: str, base: Path):
        self.name = name
        self.directory = REPOS / name
        self.base = base

    def run(
        self, args: list[str], *, cwd: Path | None = None, check: bool = True
    ) -> subprocess.CompletedProcess:
        if cwd is None:
            cwd = self.directory
        return subprocess.run(args, cwd=cwd, check=check)

    def checkout(self) -> None:
        if self.directory.exists():
            print(f"Updating {highlight(self.name)}...")
            # Update
            self.run(["git", "reset", "--quiet", "--hard", "origin/HEAD"])
            self.run(["git", "remote", "prune", "origin"])
            subprocess.run(["git", "pull", "--quiet"])
        else:
            print(f"Cloning {highlight(self.name)}...")
            # Initial checkout
            REPOS.mkdir(exist_ok=True)
            self.run(
                ["git", "clone", f"git@github.com:python-social-auth/{self.name}.git"],
                cwd=REPOS,
            )

    def update_files(self) -> None:
        if self.base == self.directory:
            return
        for name in COPY_FROM_BASE:
            copyfile(self.base / name, self.directory / name)

    def commit(self) -> None:
        self.run(["git", "add", "."])
        if self.run(["git", "diff", "--cached", "--exit-code"], check=False).returncode:
            print(f"Committing {highlight(self.name)}...")
            self.run(["git", "commit", "-m", COMMIT_MESSAGE])
            self.run(["git", "push"])


def main() -> None:
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
