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
COPY_FROM_BASE: tuple[str, ...] = (
    ".pre-commit-config.yaml",
    ".github/renovate.json",
)
REMOVE_FILES: tuple[str, ...] = (
    ".github/dependabot.yml",
    ".landscape.yaml",
    ".flake8",
    "Makefile",
    "Dockerfile",
    "CONTRIBUTING.md",
    "renovate.json",
)
REMOVE_EXCEPTIONS: tuple[tuple[str, str], ...] = (
    # This is the only location for CONTRIBUTING.md
    (".github", "CONTRIBUTING.md"),
)
README_SECTIONS: tuple[str, ...] = (
    "## Documentation",
    "## Contributing",
    "## Versioning",
    "## License",
    "## Donations",
)
COMMIT_MESSAGE = """chore: update shared files

Automated update of shared files from the social-core repository, see
https://github.com/python-social-auth/.github/blob/main/repo-sync.py
"""


def highlight(value: str) -> str:
    """Highlight string for terminal output."""
    return colored(value, "cyan")


class Readme:
    """README updating helper."""

    def __init__(self, path: Path) -> None:
        """Initialize and load the file."""
        self.path = path
        self.sections: dict[str, str] = {}
        self.load_existing()

    def load_existing(self) -> None:
        """Load existing content from file."""
        if not self.path.exists():
            return
        section: str | None = None
        content: list[str] = []

        for line in self.path.read_text().splitlines():
            if line.startswith("#"):
                if section:
                    self.sections[section] = "\n".join(content)
                section = line
                content = []
            else:
                content.append(line)
        if section:
            self.sections[section] = "\n".join(content)

    def update(self, base: Readme) -> None:
        """Update content to match base."""
        for section, content in base.sections.items():
            if section.startswith("# "):
                # Initial description of PSA
                for ours in self.sections:
                    if ours.startswith("# "):
                        self.sections[ours] = content
            elif section in README_SECTIONS and section in self.sections:
                # Individual sections
                self.sections[section] = content

    def save(self) -> None:
        """Update the file on disk."""
        self.path.write_text(
            "\n".join(
                f"{title.strip()}\n\n{content.strip()}\n"
                for title, content in self.sections.items()
            )
        )


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
            self.run(["git", "remote", "update", "--prune", "origin"])
            self.run(["git", "reset", "--quiet", "--hard", "origin/HEAD"])
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
        # Update files from base repo
        if self.base != self.directory:
            for name in COPY_FROM_BASE:
                copyfile(self.base / name, self.directory / name)
        # Remove extra files
        for name in REMOVE_FILES:
            if (self.name, name) in REMOVE_EXCEPTIONS:
                continue
            file = self.directory / name
            file.unlink(missing_ok=True)

    def commit(self) -> None:
        """Commit and push pending changes."""
        self.run(["git", "add", "."])
        if self.run(["git", "diff", "--cached", "--exit-code"], check=False).returncode:
            print(f"Committing {highlight(self.name)}...")
            self.run(["git", "commit", "-m", COMMIT_MESSAGE])
            self.run(["git", "push"])

    def update_readme(self, base: Readme) -> None:
        """Update README files to match base."""
        for name in ["README.md", "profile/README.md"]:
            path = self.directory / name
            if path.exists():
                readme = Readme(path)
                readme.update(base)
                readme.save()


def main() -> None:
    """Update all repositories."""
    # Base repository (social-core)
    base = REPOS / REPOSITORIES[0]

    repos = [Repository(name, base) for name in REPOSITORIES]

    # Update working copies and files from base
    for repo in repos:
        repo.checkout()
        repo.update_files()

    # Update readme
    readme = Readme(base / "README.md")
    for repo in repos:
        repo.update_readme(readme)

    # Commit changes
    for repo in repos:
        repo.commit()


if __name__ == "__main__":
    main()
