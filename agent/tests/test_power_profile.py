import subprocess

import pytest

from agent.metrics import system


@pytest.mark.parametrize(("responses", "file_value", "expected"), [
    ({"powerprofilesctl": "performance", "tuned-adm": "Current active profile: balanced"},
     "low-power", {"name": "performance", "source": "powerprofilesctl"}),
    ({"tuned-adm": "Current active profile: throughput-performance"},
     "balanced", {"name": "throughput-performance", "source": "tuned"}),
    ({"tuned-adm": "No current active profile."},
     "low-power", {"name": "low-power", "source": "platform_profile"}),
    ({}, None, None),
])
def test_profile_detection(monkeypatch, tmp_path, responses, file_value, expected):
    path = tmp_path / "profile"
    if file_value is not None:
        path.write_text(file_value)
    monkeypatch.setattr(system, "PLATFORM_PROFILE", path)
    monkeypatch.setattr(system, "_command", lambda *args: responses.get(args[0]))
    assert system.detect_power_profile() == expected


@pytest.mark.parametrize("error", [FileNotFoundError(), subprocess.TimeoutExpired("cmd", 1)])
def test_command_failures(monkeypatch, error):
    def run(*args, **kwargs):
        raise error
    monkeypatch.setattr(system.subprocess, "run", run)
    assert system._command("missing") is None


def test_stopped_service(monkeypatch):
    result = subprocess.CompletedProcess(["cmd"], 1, stdout="performance", stderr="stopped")
    monkeypatch.setattr(system.subprocess, "run", lambda *args, **kwargs: result)
    assert system._command("cmd") is None
