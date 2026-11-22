import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/kubeforge-admin"


def test_admin_script_syntax():
    result = subprocess.run(
        ["sh", "-n", str(SCRIPT)],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0


def test_admin_verify_rejects_invalid_id():
    result = subprocess.run(
        ["sh", str(SCRIPT), "containerd-verify"],
        input="../passwd\n",
        capture_output=True,
        text=True
    )

    assert result.returncode == 2
    assert "Invalid backup ID" in result.stderr

def test_restore_rejects_invalid_id():
    result = subprocess.run(
        ["sh", str(SCRIPT), "containerd-restore"],
        input="../passwd\n",
        capture_output=True,
        text=True
    )

    assert result.returncode == 2
    assert "Invalid backup ID" in result.stderr


def test_restore_not_implemented():
    result = subprocess.run(
        ["sh", str(SCRIPT), "containerd-restore"],
        input="ABC12345\n",
        capture_output=True,
        text=True
    )

    assert result.returncode == 3
    assert "Restore is not implemented yet" in result.stderr
