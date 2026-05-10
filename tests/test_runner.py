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


class _ImmediateTimer:
    """Fake threading.Timer that fires the callback as soon as .start() is called."""

    def __init__(self, delay: float, fn):
        self._fn = fn

    def start(self) -> None:
        self._fn()

    def cancel(self) -> None:
        pass


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
    """Timer fires during the stdout loop → process is killed → returns -1."""
    mock_proc = _make_popen_mock([])

    with patch("nxc.runner.threading.Timer", _ImmediateTimer):
        with patch("nxc.runner.subprocess.Popen", return_value=mock_proc):
            rc = run_service("smb", _CMD, timeout=5, stream_output=True)

    assert rc == -1
    mock_proc.kill.assert_called_once()


def test_run_service_stream_no_timeout_no_timer():
    """When timeout=None, no timer is created and the process runs to completion."""
    mock_proc = _make_popen_mock(["output\n"], returncode=0)

    with patch("nxc.runner.threading.Timer") as mock_timer_class:
        with patch("nxc.runner.subprocess.Popen", return_value=mock_proc):
            rc = run_service("smb", _CMD, timeout=None, stream_output=True)

    assert rc == 0
    mock_timer_class.assert_not_called()


def test_run_service_stream_force_color_in_env():
    """FORCE_COLOR=1 must be present in the env passed to Popen so nxc keeps colours."""
    mock_proc = _make_popen_mock([], returncode=0)
    captured_env: dict = {}

    def fake_popen(cmd, **kwargs):
        captured_env.update(kwargs.get("env", {}))
        return mock_proc

    with patch("nxc.runner.subprocess.Popen", side_effect=fake_popen):
        run_service("smb", _CMD, timeout=None, stream_output=True)

    assert captured_env.get("FORCE_COLOR") == "1"


def test_run_service_stream_nxc_not_found_exits():
    with patch("nxc.runner.subprocess.Popen") as mock_popen:
        mock_popen.side_effect = FileNotFoundError
        with pytest.raises(SystemExit) as exc_info:
            run_service("smb", _CMD, timeout=None, stream_output=True)
    assert exc_info.value.code == 1
