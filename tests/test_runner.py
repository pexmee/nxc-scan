"""Tests for nxc/runner.py — run_service(), with subprocess mocked out."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from nxc.runner import run_service

_CMD = ["nxc", "smb", "10.0.0.1"]


# ---------------------------------------------------------------------------
# Normal (non-streaming) execution
# ---------------------------------------------------------------------------


def test_run_service_success():
    with patch("nxc.runner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        rc = run_service("smb", _CMD, timeout=None)
    assert rc == 0
    mock_run.assert_called_once_with(_CMD, timeout=None)


def test_run_service_nonzero_exit():
    with patch("nxc.runner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        rc = run_service("smb", _CMD, timeout=None)
    assert rc == 1


def test_run_service_timeout_returns_minus_one():
    with patch("nxc.runner.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(_CMD, 30)
        rc = run_service("smb", _CMD, timeout=30)
    assert rc == -1


def test_run_service_nxc_not_found_exits(capsys):
    with patch("nxc.runner.subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError
        with pytest.raises(SystemExit) as exc_info:
            run_service("smb", _CMD, timeout=None)
    assert exc_info.value.code == 1


def test_run_service_keyboard_interrupt_exits():
    with patch("nxc.runner.subprocess.run") as mock_run:
        mock_run.side_effect = KeyboardInterrupt
        with pytest.raises(SystemExit) as exc_info:
            run_service("smb", _CMD, timeout=None)
    assert exc_info.value.code == 130


# ---------------------------------------------------------------------------
# Streaming execution (stream_output=True)
# ---------------------------------------------------------------------------


def _make_popen_mock(lines: list[str], returncode: int = 0) -> MagicMock:
    """Return a Popen mock whose .stdout iterates over *lines*."""
    mock_proc = MagicMock()
    mock_proc.stdout = iter(lines)
    mock_proc.returncode = returncode
    mock_proc.wait.return_value = None
    return mock_proc


def test_run_service_stream_success():
    mock_proc = _make_popen_mock(["line one\n", "line two\n"], returncode=0)
    with patch("nxc.runner.subprocess.Popen", return_value=mock_proc):
        rc = run_service("smb", _CMD, timeout=None, stream_output=True)
    assert rc == 0


def test_run_service_stream_nonzero_exit():
    mock_proc = _make_popen_mock([], returncode=2)
    with patch("nxc.runner.subprocess.Popen", return_value=mock_proc):
        rc = run_service("smb", _CMD, timeout=None, stream_output=True)
    assert rc == 2


def test_run_service_stream_timeout_kills_process():
    mock_proc = _make_popen_mock([])
    # First wait() (with timeout) raises; second wait() (cleanup, no timeout) succeeds.
    mock_proc.wait.side_effect = [subprocess.TimeoutExpired(_CMD, 5), None]
    with patch("nxc.runner.subprocess.Popen", return_value=mock_proc):
        rc = run_service("smb", _CMD, timeout=5, stream_output=True)
    assert rc == -1
    mock_proc.kill.assert_called_once()


def test_run_service_stream_nxc_not_found_exits():
    with patch("nxc.runner.subprocess.Popen") as mock_popen:
        mock_popen.side_effect = FileNotFoundError
        with pytest.raises(SystemExit) as exc_info:
            run_service("smb", _CMD, timeout=None, stream_output=True)
    assert exc_info.value.code == 1
