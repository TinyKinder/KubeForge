import subprocess
from pathlib import Path

import pytest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "kubeforge-vps-prepare"
)


def run_installer(*args):
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_installer_syntax():
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0


def test_installer_help():
    result = run_installer("--help")

    assert result.returncode == 0
    assert "--check" in result.stdout
    assert "--apply" in result.stdout


@pytest.mark.parametrize(
    "arguments",
    [
        ("--unknown",),
        ("--apply", "v1.99"),
        ("--check", "invalid"),
        ("--apply", "v1.37", "extra"),
    ],
)
def test_installer_rejects_invalid_arguments(arguments):
    result = run_installer(*arguments)

    assert result.returncode == 2
