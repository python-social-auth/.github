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
    "social-docs",
    ".github",
    "social-app-django",
    "social-app-cherrypy",
    "social-storage-sqlalchemy",
    "social-storage-peewee",
    "social-storage-mongoengine",
    "social-examples",
    "social-app-flask-sqlalchemy",
    "social-app-pyramid",
    "social-app-tornado",
    "social-app-webpy",
    "social-app-django-mongoengine",
    "social-app-flask-peewee",
    "social-app-flask-mongoengine",
    "social-app-flask",
)
ROOT = Path(__file__).parent
REPOS = ROOT / "repos"
COPY_FROM_BASE: tuple[str, ...] = (
    ".pre-commit-config.yaml",
    ".github/renovate.json",
)
ADJUST_FROM_BASE: dict[str, tuple[str, str]] = {
    ".github/workflows/pre-commit.yml": (
        "uses: ./.github/workflows/pre-commit-shared.yml",
        "uses: python-social-auth/social-core/.github/workflows/pre-commit-shared.yml@master",
    ),
    ".github/workflows/release.yml": (
        "uses: ./.github/workflows/release-shared.yml",
        "uses: python-social-auth/social-core/.github/workflows/release-shared.yml@master",
    ),
}
ADJUST_FROM_BASE_EXCEPTIONS: tuple[tuple[str, str], ...] = (
    # These do not release
    (".github", ".github/workflows/release.yml"),
    ("social-docs", ".github/workflows/release.yml"),
    ("social-examples", ".github/workflows/release.yml"),
)
REMOVE_FILES: tuple[str, ...] = (
    ".github/dependabot.yml",
    ".github/workflows/ruff.yml",
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
COMMIT_MESSAGE_PRE_COMMIT = """chore: apply pre-commit fixes

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
        print(f"Updating {highlight(self.name)}")
        # Update files from base repo
        if self.base != self.directory:
            for name in COPY_FROM_BASE:
                output = self.directory / name
                output.parent.mkdir(exist_ok=True, parents=True)
                copyfile(self.base / name, output)

            for name, (original, replacement) in ADJUST_FROM_BASE.items():
                if (self.name, name) in ADJUST_FROM_BASE_EXCEPTIONS:
                    continue
                output = self.directory / name
                output.parent.mkdir(exist_ok=True, parents=True)
                source = (self.base / name).read_text()
                output.write_text(source.replace(original, replacement))

        # Remove extra files
        for name in REMOVE_FILES:
            if (self.name, name) in REMOVE_EXCEPTIONS:
                continue
            file = self.directory / name
            file.unlink(missing_ok=True)

    def commit(self, message: str = COMMIT_MESSAGE) -> None:
        """Commit and push pending changes."""
        self.run(["git", "add", "."])
        print(f"Comparing {highlight(self.name)}")
        if self.run(["git", "diff", "--cached", "--exit-code"], check=False).returncode:
            print(f"Committing {highlight(self.name)}...")
            self.run(["git", "commit", "-m", message])
            self.run(["git", "push"])

    def update_readme(self, base: Readme) -> None:
        """Update README files to match base."""
        for name in ["README.md", "profile/README.md"]:
            path = self.directory / name
            if path.exists():
                readme = Readme(path)
                readme.update(base)
                readme.save()

    def pre_commit(self) -> None:
        """Run pre-commit on the repository."""
        self.run(["uvx", "pre-commit", "run", "--all-files"], check=False)
        self.commit(message=COMMIT_MESSAGE_PRE_COMMIT)


def main() -> None:
    """Update all repositories."""
    # Base repository (social-core)
    base = REPOS / REPOSITORIES[0]

    repos = [Repository(name, base) for name in REPOSITORIES]

    # Update working copies and files from base
    for repo in repos:
        repo.checkout()

    # Update files
    for repo in repos:
        repo.update_files()

    # Update readme
    readme = Readme(base / "README.md")
    for repo in repos:
        repo.update_readme(readme)

    # Commit changes
    for repo in repos:
        repo.commit()

    # Apply pre-commit changes
    for repo in repos:
        repo.pre_commit()


if __name__ == "__main__":
    main()
