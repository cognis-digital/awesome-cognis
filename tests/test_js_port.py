"""
Integration tests for the JavaScript port of the awesome-cognis scanner.
Covers error/edge paths introduced by hardening.
"""
import json
import subprocess
import tempfile
from pathlib import Path

import pytest

JS_PORT = Path(__file__).parent.parent / "ports" / "javascript" / "index.js"

# A path that is guaranteed not to exist on any OS.
_MISSING = str(Path(tempfile.gettempdir()) / "awesome_cognis_no_such_dir_xyzzy_9999")


def run_scanner(*args, cwd=None):
    """Run ``node index.js`` with given args.

    Returns ``(returncode, stdout, stderr)`` as strings.
    """
    cmd = ["node", str(JS_PORT)] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return result.returncode, result.stdout, result.stderr


def node_available():
    """Return True if node is on PATH."""
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


pytestmark = pytest.mark.skipif(
    not node_available(), reason="node not available on PATH"
)


class TestMissingPath:
    def test_nonexistent_path_exits_nonzero(self):
        """Passing a path that does not exist must exit with a non-zero code."""
        rc, out, err = run_scanner(_MISSING)
        assert rc != 0, f"Expected non-zero exit for missing path, got {rc}"

    def test_nonexistent_path_reports_to_stderr(self):
        """Error message for missing path must appear on stderr, not stdout."""
        rc, out, err = run_scanner(_MISSING)
        assert "error" in err.lower(), f"Expected 'error' in stderr, got: {err!r}"
        # stdout must be empty on error so callers don't get garbled JSON
        assert out.strip() == "", f"Expected empty stdout on error, got: {out!r}"

    def test_nonexistent_path_exit_code_is_2(self):
        """Missing path should return exit code 2 (input-error convention)."""
        rc, _out, _err = run_scanner(_MISSING)
        assert rc == 2, f"Expected exit code 2 for missing path, got {rc}"


class TestValidInput:
    def test_empty_directory_returns_valid_json(self):
        """Scanning an empty directory must return valid JSON with zero findings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rc, out, err = run_scanner(tmpdir)
        assert rc == 0, f"Expected exit 0 for empty dir, got {rc}; stderr={err!r}"
        data = json.loads(out)
        assert data["score"] == 0
        assert data["findings"] == []
        assert data["tool"] == "awesome-cognis"

    def test_file_with_todo_detected(self):
        """A file containing TODO must produce a GEN-001 finding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "sample.txt").write_text("# TODO fix this\n")
            rc, out, _err = run_scanner(tmpdir)
        assert rc == 0
        data = json.loads(out)
        ids = [f["id"] for f in data["findings"]]
        assert "GEN-001" in ids

    def test_file_with_fixme_detected(self):
        """A file containing FIXME must produce a GEN-002 finding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "code.py").write_text("x = 1  # FIXME\n")
            rc, out, _err = run_scanner(tmpdir)
        assert rc == 0
        data = json.loads(out)
        ids = [f["id"] for f in data["findings"]]
        assert "GEN-002" in ids

    def test_clean_directory_zero_score(self):
        """A directory with no markers must return score=0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "clean.txt").write_text("all good here\n")
            rc, out, _err = run_scanner(tmpdir)
        assert rc == 0
        data = json.loads(out)
        assert data["score"] == 0

    def test_output_is_valid_json_on_success(self):
        """Scanner output on success must be parseable JSON with required keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rc, out, _err = run_scanner(tmpdir)
        assert rc == 0
        data = json.loads(out)
        for key in ("tool", "findings", "score"):
            assert key in data, f"Missing key {key!r} in output"

    def test_default_target_scans_cwd(self):
        """Running without args should scan the working directory without error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rc, out, err = run_scanner(cwd=tmpdir)
        assert rc == 0, f"Expected exit 0; stderr={err!r}"
        data = json.loads(out)
        assert "tool" in data
