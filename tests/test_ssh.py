import subprocess
from types import SimpleNamespace

import pytest

from kubeforge.core.ssh import run_ssh


def test_ssh_success(monkeypatch):
    def fake_run(command, **kwargs):
        assert command == [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=10",
            "-p", "22",
            "ubuntu@192.168.1.100",
            "whoami"
        ]

        assert kwargs["check"] is True

        return SimpleNamespace(stdout="ubuntu\n")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_ssh(
        host="192.168.1.100",
        user="ubuntu",
        command="whoami"
    )

    assert result == "ubuntu\n"


def test_ssh_failure(monkeypatch):
    def fake_run(command, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=255,
            cmd=command
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(subprocess.CalledProcessError):
        run_ssh(
            host="192.168.1.100",
            user="ubuntu",
            command="whoami"
        )
