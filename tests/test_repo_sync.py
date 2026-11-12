# Copyright © Michal Čihař <michal@weblate.org>
#
# SPDX-License-Identifier: BSD-3-Clause
# ruff: noqa: PT009
# These tests use standard-library unittest assertions without pytest.

"""Offline regression tests for shared file synchronization."""

from __future__ import annotations

import runpy
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

Repository = runpy.run_path(Path(__file__).resolve().parents[1] / "repo-sync.py")[
    "Repository"
]

SHARED_FILES = {
    ".pre-commit-config.yaml": b"repos: []\n",
    ".github/renovate.json": b'{"extends": ["config:best-practices"]}\n',
    ".github/workflows/pre-commit.yml": (
        b"name: pre-commit check\non: [push, pull_request]\n"
        b"jobs:\n  pre-commit:\n    runs-on: ubuntu-latest\n"
        b"    steps:\n    - run: uvx prek run --all-files\n"
    ),
}
RELEASE_WORKFLOW = ".github/workflows/release.yml"


class UpdateFilesTest(unittest.TestCase):
    """Exercise file updates without checking out, committing, or pushing."""

    def setUp(self) -> None:
        """Create isolated source and destination repositories."""
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.base = root / "social-core"
        for name, content in {
            **SHARED_FILES,
            RELEASE_WORKFLOW: b"# Core release workflow\n",
        }.items():
            path = self.base / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        self.repo = Repository("social-app-django", self.base)
        self.repo.directory = root / "social-app-django"
        self.repo.directory.mkdir()

    def test_preserves_existing_release_workflow(self) -> None:
        """Preserve the destination's repository-specific publishing guard."""
        release = self.repo.directory / RELEASE_WORKFLOW
        release.parent.mkdir(parents=True)
        content = b"if: github.repository == 'python-social-auth/social-app-django'\r\n"
        release.write_bytes(content)

        self.repo.update_files()

        self.assertEqual(release.read_bytes(), content)

    def test_does_not_create_release_workflow(self) -> None:
        """Leave repositories without a release workflow as they are."""
        self.repo.update_files()

        self.assertFalse((self.repo.directory / RELEASE_WORKFLOW).exists())

    def test_copies_shared_files(self) -> None:
        """Copy shared configuration and the standalone pre-commit workflow."""
        existing = self.repo.directory / ".pre-commit-config.yaml"
        existing.write_bytes(b"# Outdated configuration\n")

        self.repo.update_files()

        for name, content in SHARED_FILES.items():
            with self.subTest(name=name):
                self.assertEqual((self.repo.directory / name).read_bytes(), content)

    def test_base_repository_does_not_copy_onto_itself(self) -> None:
        """Keep base files unchanged and avoid copying a file onto itself."""
        self.repo = Repository("social-core", self.base)
        self.repo.directory = self.base
        before = {
            path.relative_to(self.base): path.read_bytes()
            for path in self.base.rglob("*")
            if path.is_file()
        }

        self.repo.update_files()

        after = {
            path.relative_to(self.base): path.read_bytes()
            for path in self.base.rglob("*")
            if path.is_file()
        }
        self.assertEqual(after, before)
