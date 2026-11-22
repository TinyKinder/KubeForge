import subprocess
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/kubeforge-admin"


def create_fake_command(path, body):
    path.write_text("#!/bin/sh\n" + body + "\n")
    path.chmod(0o755)


def prepare_test_environment(tmp_path, fail_first=False):
    config_dir = tmp_path / "containerd"
    backup_dir = tmp_path / "backups"
    lock_dir = tmp_path / "lock"

    for directory in (config_dir, backup_dir, lock_dir):
        directory.mkdir()

    config = config_dir / "config.toml"
    config.write_text("old configuration\n")

    backup = backup_dir / "config.toml.ABC12345"
    backup.write_text("new configuration\n")

    fake_stat = tmp_path / "stat"
    fake_containerd = tmp_path / "containerd-command"
    fake_systemctl = tmp_path / "systemctl"

    create_fake_command(fake_stat, "printf '0\\n'")
    create_fake_command(
        fake_containerd,
        'test "$1" = "--config" && test -s "$2"'
    )

    if fail_first:
        marker = tmp_path / "restart-attempted"

        systemctl_body = f"""
if [ "$1" = "restart" ] && [ ! -f "{marker}" ]; then
    touch "{marker}"
    exit 1
fi
exit 0
"""
    else:
        systemctl_body = "exit 0"

    create_fake_command(fake_systemctl, systemctl_body)

    script_text = SCRIPT.read_text()

    replacements = {
        "/etc/containerd": str(config_dir),
        "/var/backups/kubeforge/containerd": str(backup_dir),
	"/run/kubeforge": str(lock_dir),
        "/usr/bin/containerd": str(fake_containerd),
        "/usr/bin/systemctl": str(fake_systemctl),
        "/usr/bin/stat": str(fake_stat),
    }

    for original, replacement in replacements.items():
        assert original in script_text
        script_text = script_text.replace(original, replacement)

    isolated_script = tmp_path / "kubeforge-admin"
    isolated_script.write_text(script_text)

    return isolated_script, config


@pytest.mark.parametrize(
    "fail_first,expected_config,expected_code",
    [
        (False, "new configuration\n", 0),
        (True, "old configuration\n", 1),
    ]
)
def test_containerd_restore_isolated(
    tmp_path, fail_first, expected_config, expected_code
):
    script, config = prepare_test_environment(
        tmp_path,
        fail_first=fail_first
    )

    result = subprocess.run(
        ["sh", str(script), "containerd-restore"],
        input="ABC12345\n",
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == expected_code
    assert config.read_text() == expected_config

    if fail_first:
        assert "ROLLBACK_OK" in result.stderr
    else:
        assert "RESTORE_OK" in result.stdout

def test_restore_preserves_previous_on_failed_rollback(tmp_path):
    script, config = prepare_test_environment(tmp_path)

    create_fake_command(
        tmp_path / "systemctl",
        '[ "$1" != "restart" ]'
    )

    result = subprocess.run(
        ["sh", str(script), "containerd-restore"],
        input="ABC12345\n",
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 1
    assert "CRITICAL: Automatic rollback failed" in result.stderr
    assert config.read_text() == "old configuration\n"

    previous_files = list(
        (tmp_path / "containerd").glob(".kubeforge-prev.*")
    )

    assert len(previous_files) == 1
    assert previous_files[0].read_text() == "old configuration\n"

def test_restore_rejects_empty_backup(tmp_path):
    script, config = prepare_test_environment(tmp_path)

    backup = tmp_path / "backups" / "config.toml.ABC12345"
    backup.write_text("")

    result = subprocess.run(
        ["sh", str(script), "containerd-restore"],
        input="ABC12345\n",
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 1
    assert "Invalid backup file" in result.stderr
    assert config.read_text() == "old configuration\n"

def test_restore_rejects_invalid_config(tmp_path):
    script, config = prepare_test_environment(tmp_path)

    create_fake_command(
        tmp_path / "containerd-command",
        "exit 1"
    )

    result = subprocess.run(
        ["sh", str(script), "containerd-restore"],
        input="ABC12345\n",
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 1
    assert "Invalid containerd configuration" in result.stderr
    assert config.read_text() == "old configuration\n"


def test_restore_fails_to_save_current_config(tmp_path):
    script, config = prepare_test_environment(tmp_path)

    fake_cp = tmp_path / "fake-cp"
    create_fake_command(fake_cp, "exit 1")

    script.write_text(
        script.read_text().replace(
            "/usr/bin/cp",
            str(fake_cp)
        )
    )

    result = subprocess.run(
        ["sh", str(script), "containerd-restore"],
        input="ABC12345\n",
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 1
    assert "Failed to save current configuration" in result.stderr
    assert config.read_text() == "old configuration\n"

def test_restore_rejects_symlink_backup(tmp_path):
    script, config = prepare_test_environment(tmp_path)

    backup = tmp_path / "backups" / "config.toml.ABC12345"
    target = tmp_path / "other-config.toml"

    target.write_text("new configuration\n")
    backup.unlink()
    backup.symlink_to(target)

    result = subprocess.run(
        ["sh", str(script), "containerd-restore"],
        input="ABC12345\n",
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 1
    assert "Invalid backup file" in result.stderr
    assert config.read_text() == "old configuration\n"


def test_restore_rejects_busy_lock(tmp_path):
    script, config = prepare_test_environment(tmp_path)

    fake_flock = tmp_path / "fake-flock"
    create_fake_command(fake_flock, "exit 1")

    script.write_text(
        script.read_text().replace(
            "/usr/bin/flock", str(fake_flock)
        )
    )

    result = subprocess.run(
        ["sh", str(script), "containerd-restore"],
        input="ABC12345\n",
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 1
    assert "Another restore is running" in result.stderr
    assert config.read_text() == "old configuration\n"


def test_restore_fails_to_prepare_candidate(tmp_path):
    script, config = prepare_test_environment(tmp_path)

    marker = tmp_path / "first-copy-done"
    fake_cp = tmp_path / "fake-cp"

    create_fake_command(
        fake_cp,
        f'''
if [ ! -f "{marker}" ]; then
    touch "{marker}"
    exec /usr/bin/cp "$@"
fi
exit 1
'''
    )

    script.write_text(
        script.read_text().replace(
            "/usr/bin/cp", str(fake_cp)
        )
    )

    result = subprocess.run(
        ["sh", str(script), "containerd-restore"],
        input="ABC12345\n",
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 1
    assert "Failed to prepare restore" in result.stderr
    assert config.read_text() == "old configuration\n"

def test_restore_creates_persistent_safety_backup(tmp_path):
    script, config = prepare_test_environment(tmp_path)

    result = subprocess.run(
        ["sh", str(script), "containerd-restore"],
        input="ABC12345\n",
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0
    assert config.read_text() == "new configuration\n"

    backups = list(
        (tmp_path / "backups").glob("config.toml.*")
    )

    safety_backups = [
        backup for backup in backups
        if backup.name != "config.toml.ABC12345"
    ]

    assert len(safety_backups) == 1
    assert safety_backups[0].read_text() == "old configuration\n"


def test_restore_preserves_config_permissions(tmp_path):
    import stat

    script, config = prepare_test_environment(tmp_path)

    config.chmod(0o640)

    backup = tmp_path / "backups" / "config.toml.ABC12345"
    backup.chmod(0o600)

    result = subprocess.run(
        ["sh", str(script), "containerd-restore"],
        input="ABC12345\n",
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0

    permissions = stat.S_IMODE(config.stat().st_mode)

    assert permissions == 0o640
    assert config.read_text() == "new configuration\n"
