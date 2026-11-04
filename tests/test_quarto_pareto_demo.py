# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pareto launcher: validate no implicit fetch, opt-in and server lifetime.

No real Quarto, Firefox, network or private Git repository is used here.
"""
from __future__ import annotations

from contextlib import redirect_stdout
import io
from pathlib import Path
import unittest
from unittest.mock import patch, Mock

import quarto_pareto_demo as pilot


class ParetoLaunchTests(unittest.TestCase):
    SHA = "a" * 40
    REF = "refs/remotes/origin/experiment/fiche-quarto"

    def test_consent_required_before_any_render(self):
        with patch.object(pilot, "create_observed_session") as render:
            with self.assertRaises(pilot.DemoRefused):
                pilot.prepare(Path("/fiction"), "fiction/lab", self.REF, self.SHA,
                              public_fictional_trusted=False)
            render.assert_not_called()

    def test_reject_branch_or_sha_not_explicit(self):
        invalid = [
            ("refs/heads/main", self.SHA),
            ("refs/remotes/origin/main", self.SHA),
            ("refs/remotes/origin/experiment/../main", self.SHA),
            ("refs/remotes/origin/experiment//foo", self.SHA),
            ("refs/remotes/origin/experiment/test.lock", self.SHA),
            ("refs/remotes/origin/experiment/test", "short"),
            ("refs/remotes/origin/experiment/test", "g" * 40),
        ]
        for ref, sha in invalid:
            with self.subTest(ref=ref, sha=sha):
                with self.assertRaises(pilot.DemoRefused):
                    pilot.validate_inputs("fiction/lab", sha, ref, True)

    def test_reuses_verified_session_and_loopback_server_without_fetch(self):
        result = {
            "resource_id": "quarto:fiction/lab:activite.qmd",
            "session_path": "/fiction/isolated-session",
            "baseline_commit": self.SHA,
            "observed_commit": "b" * 40,
        }
        preview = Mock()
        preview.browser_url.return_value = "http://127.0.0.1:9999/fiction"
        server = Mock()
        server.server_port = 9999
        with (patch.object(pilot, "create_observed_session", return_value=result) as render,
              patch.object(pilot, "AttestedPreview", return_value=preview) as bound,
              patch.object(pilot, "make_server", return_value=server) as make):
            buf = io.StringIO()
            with redirect_stdout(buf):
                status = pilot.main([
                    "--repo", "/fiction", "--repository-id", "fiction/lab",
                    "--tracking-ref", self.REF, "--baseline-sha", self.SHA,
                    "--public-fictional-trusted"
                ])
        self.assertEqual(status, 0)
        render.assert_called_once_with(
            Path("/fiction"), "fiction/lab", "activite.qmd",
            self.REF, self.SHA, trusted_quarto=True,
        )
        bound.assert_called_once_with(Path(result["session_path"]), result["resource_id"])
        make.assert_called_once_with(preview)
        server.serve_forever.assert_called_once_with()
        server.server_close.assert_called_once_with()
        self.assertIn("http://127.0.0.1:9999/fiction", buf.getvalue())
        self.assertIn("Aucun fetch automatique", buf.getvalue())

    def test_invalid_repository_identity_rejected(self):
        for x in ("../private", "fiction/private/a", "https://github.com/fiction/lab"):
            with self.subTest(x=x), self.assertRaises(pilot.DemoRefused):
                pilot.validate_inputs(x, self.SHA, self.REF, True)


if __name__ == "__main__":
    unittest.main()
