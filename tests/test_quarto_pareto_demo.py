# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pareto launcher: validate no implicit fetch, opt-in and server lifetime.

No real Quarto, Firefox, network or private Git repository is used here.
"""
from __future__ import annotations

from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
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
        self.assertIn("Actualisation Git explicitement demandée : NON", buf.getvalue())

    def test_invalid_repository_identity_rejected(self):
        for x in ("../private", "fiction/private/a", "https://github.com/fiction/lab"):
            with self.subTest(x=x), self.assertRaises(pilot.DemoRefused):
                pilot.validate_inputs(x, self.SHA, self.REF, True)


    def test_explicit_fetch_restricted_to_the_exact_public_demo(self):
        with tempfile.TemporaryDirectory() as path:
            repo = Path(path)
            before = "a" * 40
            calls = []

            def fake_git(_repo, *args):
                calls.append(args)
                if args == ("rev-parse", "--show-toplevel"):
                    return (str(repo) + "\n").encode()
                if args == ("remote", "get-url", "origin"):
                    return b"https://github.com/djibian/alliage.git\n"
                if args == ("rev-parse", "--verify",
                             "refs/remotes/origin/experiment/pareto-quarto-demo^{commit}"):
                    return (before + "\n").encode()
                raise AssertionError(args)

            with (patch.object(pilot, "_git", side_effect=fake_git),
                  patch.object(pilot.subprocess, "run",
                               return_value=SimpleNamespace(returncode=0)) as fetch):
                previous = pilot.fetch_fictional_demo(
                    repo, "djibian/alliage",
                    "refs/remotes/origin/experiment/pareto-quarto-demo")
            self.assertEqual(previous, before)
            command = fetch.call_args.args[0]
            self.assertEqual(command[:4], ["git", "-C", str(repo), "fetch"])
            self.assertIn("--no-tags", command)
            self.assertEqual(command[-1],
                             "refs/heads/experiment/pareto-quarto-demo:"
                             "refs/remotes/origin/experiment/pareto-quarto-demo")
            self.assertEqual(fetch.call_args.kwargs["env"]["GIT_TERMINAL_PROMPT"], "0")

    def test_explicit_fetch_refuses_any_other_branch_repo_or_remote(self):
        with tempfile.TemporaryDirectory() as path:
            repo = Path(path)
            with patch.object(pilot, "_git") as git, patch.object(
                    pilot.subprocess, "run") as fetch:
                for repository_id, ref in [
                    ("other/private", "refs/remotes/origin/experiment/pareto-quarto-demo"),
                    ("djibian/alliage", "refs/remotes/origin/experiment/other"),
                ]:
                    with self.assertRaises(pilot.DemoRefused):
                        pilot.fetch_fictional_demo(repo, repository_id, ref)
                git.side_effect = lambda _repo, *args: (
                    (str(repo) + "\n").encode()
                    if args == ("rev-parse", "--show-toplevel")
                    else b"https://example.invalid/other.git\n"
                )
                with self.assertRaises(pilot.DemoRefused):
                    pilot.fetch_fictional_demo(
                        repo, "djibian/alliage",
                        "refs/remotes/origin/experiment/pareto-quarto-demo")
                fetch.assert_not_called()

    def test_one_command_refresh_uses_old_tracking_sha_and_requires_consent(self):
        ref = "refs/remotes/origin/experiment/pareto-quarto-demo"
        args = ["--repo", "/fiction", "--repository-id", "djibian/alliage",
                "--tracking-ref", ref, "--fetch-demo",
                "--public-fictional-trusted"]
        result = {
            "resource_id": "quarto:djibian/alliage:activite.qmd",
            "session_path": "/fiction/session",
            "baseline_commit": "a" * 40,
            "observed_commit": "b" * 40,
        }
        with (patch.object(pilot, "fetch_fictional_demo",
                           return_value="a" * 40) as fetch,
              patch.object(pilot, "create_observed_session",
                           return_value=result) as render,
              patch.object(pilot, "AttestedPreview") as preview,
              patch.object(pilot, "make_server") as server):
            server.return_value.server_port = 12345
            preview.return_value.browser_url.return_value = (
                "http://127.0.0.1:12345/fixture")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(pilot.main(args), 0)
            fetch.assert_called_once_with(Path("/fiction"), "djibian/alliage", ref)
            self.assertEqual(render.call_args.args[4], "a" * 40)
            server.return_value.serve_forever.assert_called_once_with()
            self.assertIsNotNone(preview.call_args)
            with self.assertRaises(SystemExit) as exit_status:
                pilot.main(args[:-1])
            self.assertEqual(exit_status.exception.code, 2)
            self.assertEqual(fetch.call_count, 1)


    def test_demo_shortcut_uses_exact_fixture_with_no_implicit_fetch(self):
        result = {
            "resource_id": "quarto:djibian/alliage:activite.qmd",
            "session_path": "/fiction/session",
            "baseline_commit": self.SHA,
            "observed_commit": "b" * 40,
        }
        preview = Mock()
        preview.browser_url.return_value = "http://127.0.0.1:10000/test"
        server = Mock()
        server.server_port = 10000
        with (patch.object(pilot, "prepare",
                           return_value=(result, preview, server)) as prepare,
              patch.object(pilot, "fetch_fictional_demo") as fetch):
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(pilot.main([
                    "--repo", "/fiction", "--demo",
                    "--baseline-sha", self.SHA,
                    "--public-fictional-trusted",
                ]), 0)
        prepare.assert_called_once_with(
            Path("/fiction"), pilot.PUBLIC_DEMO_REPOSITORY,
            pilot.PUBLIC_DEMO_TRACKING_REF, self.SHA,
            public_fictional_trusted=True)
        fetch.assert_not_called()
        self.assertIn(pilot.PUBLIC_DEMO_TRACKING_REF, buf.getvalue())
        self.assertIn("Actualisation Git explicitement demandée : NON", buf.getvalue())

    def test_demo_shortcut_preserves_explicit_fetch_and_consent(self):
        result = {
            "resource_id": "quarto:djibian/alliage:activite.qmd",
            "session_path": "/fiction/session",
            "baseline_commit": self.SHA,
            "observed_commit": "b" * 40,
        }
        with (patch.object(pilot, "fetch_fictional_demo",
                           return_value=self.SHA) as fetch,
              patch.object(pilot, "prepare") as prepare,
              patch.object(pilot, "AttestedPreview"),
              patch.object(pilot, "make_server")):
            preview = Mock()
            preview.browser_url.return_value = "http://127.0.0.1:10000/test"
            server = Mock()
            server.server_port = 10000
            prepare.return_value = (result, preview, server)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(pilot.main([
                    "--repo", "/fiction", "--demo", "--fetch-demo",
                    "--public-fictional-trusted",
                ]), 0)
            fetch.assert_called_once_with(
                Path("/fiction"), pilot.PUBLIC_DEMO_REPOSITORY,
                pilot.PUBLIC_DEMO_TRACKING_REF)
            self.assertEqual(prepare.call_args.args[3], self.SHA)

            with self.assertRaises(SystemExit) as refused:
                pilot.main(["--repo", "/fiction", "--demo", "--fetch-demo"])
            self.assertEqual(refused.exception.code, 2)
            self.assertEqual(fetch.call_count, 1)

    def test_demo_shortcut_rejects_conflicting_targets_before_git(self):
        cases = [
            ["--repository-id", "other/repo"],
            ["--tracking-ref", "refs/remotes/origin/experiment/other"],
        ]
        with (patch.object(pilot, "prepare") as prepare,
              patch.object(pilot, "fetch_fictional_demo") as fetch):
            for extra in cases:
                with self.subTest(extra=extra), self.assertRaises(SystemExit) as refused:
                    pilot.main([
                        "--repo", "/fiction", "--demo", "--fetch-demo",
                        "--public-fictional-trusted", *extra,
                    ])
                self.assertEqual(refused.exception.code, 2)
            with self.assertRaises(SystemExit) as missing_explicit:
                pilot.main(["--repo", "/fiction",
                            "--baseline-sha", self.SHA,
                            "--public-fictional-trusted"])
            self.assertEqual(missing_explicit.exception.code, 2)
            prepare.assert_not_called()
            fetch.assert_not_called()


class RealParetoQuartoTests(unittest.TestCase):
    """Opt-in CI test: genuine Quarto rendering, local Git, local HTTP, no Firefox."""
    REF = ParetoLaunchTests.REF

    @unittest.skipUnless(__import__("os").environ.get("ALLIAGE_TEST_REAL_QUARTO") == "1",
                         "Only the dedicated real Quarto workflow runs this test")
    def test_real_quarto_css_change_and_http_preview(self):
        import http.client
        import subprocess
        import tempfile
        import threading
        from urllib.parse import urlsplit

        def git(repo, *args):
            return subprocess.check_output(
                ["git", "-C", str(repo), *args], text=True
            ).strip()

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            repo = home / "public-fiction"
            repo.mkdir()
            git(repo, "init", "-q")
            git(repo, "config", "user.name", "Fiction CI")
            git(repo, "config", "user.email", "fixture@example.invalid")
            (repo / "_quarto.yml").write_text(
                "project:\n  type: default\n  output-dir: _site\n\n"
                "format:\n  html:\n    css: styles.css\n\n"
                "execute:\n  enabled: false\n", encoding="utf-8")
            (repo / "activite.qmd").write_text(
                "---\ntitle: Activité publique fictive\n---\n\n"
                "## Consigne\nFaire un test de rendu.\n", encoding="utf-8")
            (repo / "styles.css").write_text(
                "h2 { color: #991b1b; }\n", encoding="utf-8")
            git(repo, "add", "-A")
            git(repo, "commit", "-qm", "V1 rouge")
            first = git(repo, "rev-parse", "HEAD")
            (repo / "styles.css").write_text(
                "h2 { color: #7c3aed; }\n", encoding="utf-8")
            git(repo, "add", "-A")
            git(repo, "commit", "-qm", "V2 violette")
            second = git(repo, "rev-parse", "HEAD")
            git(repo, "update-ref", self.REF, second)
            before = (git(repo, "rev-parse", "HEAD"),
                      git(repo, "status", "--porcelain"))
            with patch("quarto_observed_session.Path.home", return_value=home):
                result, preview, server = pilot.prepare(
                    repo, "fiction/lab", self.REF, first,
                    public_fictional_trusted=True)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    url = urlsplit(preview.browser_url(server.server_port))
                    conn = http.client.HTTPConnection(url.hostname, url.port, timeout=8)
                    conn.request("GET", url.path + "?" + url.query)
                    resp = conn.getresponse()
                    body = resp.read()
                    conn.close()
                    self.assertEqual(resp.status, 200)
                    self.assertIn(b"Faire un test de rendu", body)
                    self.assertEqual(result["baseline_commit"], first)
                    self.assertEqual(result["observed_commit"], second)
                    self.assertFalse(result["deployment_verified"])
                    self.assertFalse(result["remote_freshness_verified"])
                    first_css = preview.get_asset(
                        preview.prefix + "/V1/project/_site/styles.css")[0]
                    second_css = preview.get_asset(
                        preview.prefix + "/V2/project/_site/styles.css")[0]
                    self.assertIn(b"#991b1b", first_css)
                    self.assertIn(b"#7c3aed", second_css)
                    self.assertNotEqual(first_css, second_css)
                    self.assertEqual(
                        before, (git(repo, "rev-parse", "HEAD"),
                                 git(repo, "status", "--porcelain")))
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
