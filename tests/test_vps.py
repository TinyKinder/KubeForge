import pytest


@pytest.mark.parametrize(
    "ssh_output, expected",
    [
        ("initialized\n", True),
        ("not_initialized\n", False),
    ]
)
def test_vps_cluster_initialized(
    monkeypatch, ssh_output, expected
):
    from kubeforge.providers import vps

    monkeypatch.setattr(
        vps,
        "run_ssh",
        lambda **kwargs: ssh_output
    )

    result = vps.is_vps_cluster_initialized(
        host="192.168.0.104",
        user="kforge"
    )

    assert result is expected

@pytest.mark.parametrize(
    "ssh_output, expected",
    [
        ("ok\n", True),
        ("not ready\n", False),
    ]
)
def test_vps_api_ready(monkeypatch, ssh_output, expected):
    from kubeforge.providers import vps

    monkeypatch.setattr(
        vps,
        "run_ssh",
        lambda **kwargs: ssh_output
    )

    result = vps.is_vps_api_ready(
        host="192.168.0.104",
        user="kforge"
    )

    assert result is expected


def test_get_vps_resources(monkeypatch):
    from kubeforge.providers import vps

    monkeypatch.setattr(
        vps,
        "run_ssh",
        lambda **kwargs: "2\n3145728\n10485760\n"
    )

    result = vps.get_vps_resources(
        host="192.168.0.104",
        user="kforge"
    )

    assert result["cpu"] == 2
    assert result["ram_gib"] == 3.0
    assert result["disk_free_gib"] == 10.0


def test_vps_preflight_success():
    from kubeforge.providers.vps import check_vps_preflight

    resources = {
        "cpu": 2,
        "ram_gib": 3.0,
        "disk_free_gib": 10.0
    }

    errors = check_vps_preflight(resources, "control-plane")

    assert errors == []


def test_vps_preflight_failure():
    from kubeforge.providers.vps import check_vps_preflight

    resources = {
        "cpu": 1,
        "ram_gib": 1.0,
        "disk_free_gib": 2.0
    }

    errors = check_vps_preflight(resources, "control-plane")

    assert len(errors) == 3

def test_run_vps_preflight(monkeypatch):
    from kubeforge.providers import vps

    config = {
        "control_plane": {
            "host": "192.168.0.104",
            "user": "kforge",
            "port": 22
        },
        "workers": [
            {
                "host": "192.168.0.108",
                "user": "kforge",
                "port": 22
            }
        ]
    }

    def fake_resources(host, user, port):
        return {
            "cpu": 2,
            "ram_gib": 3.0,
            "disk_free_gib": 10.0
        }

    monkeypatch.setattr(vps, "get_vps_resources", fake_resources)

    results = vps.run_vps_preflight(config)

    assert len(results) == 2
    assert results["192.168.0.104"]["role"] == "control-plane"
    assert results["192.168.0.108"]["role"] == "worker"
    assert results["192.168.0.104"]["errors"] == []
    assert results["192.168.0.108"]["errors"] == []


def test_vps_containerd_status(monkeypatch):
    from kubeforge.providers import vps

    def fake_ssh(host, user, command, port):
        assert host == "192.168.0.104"
        assert user == "kforge"
        assert port == 22
        assert command == (
            "sudo -n /usr/local/sbin/kubeforge-admin "
            "containerd-status"
        )

        return "active\n"

    monkeypatch.setattr(vps, "run_ssh", fake_ssh)

    result = vps.get_vps_containerd_status(
        host="192.168.0.104",
        user="kforge"
    )

    assert result == "active"

def test_vps_containerd_backup(monkeypatch):
    from kubeforge.providers import vps

    def fake_ssh(host, user, command, port):
        assert host == "192.168.0.104"
        assert user == "kforge"
        assert port == 22
        assert command == (
            "sudo -n /usr/local/sbin/kubeforge-admin "
            "containerd-backup"
        )

        return (
            "Backup created: "
            "/var/backups/kubeforge/containerd/"
            "config.toml.ABC12345\n"
        )

    monkeypatch.setattr(vps, "run_ssh", fake_ssh)

    result = vps.backup_vps_containerd(
        host="192.168.0.104",
        user="kforge"
    )

    assert result == (
        "/var/backups/kubeforge/containerd/"
        "config.toml.ABC12345"
    )


def test_vps_containerd_backup_invalid_response(monkeypatch):
    import pytest
    from kubeforge.providers import vps

    monkeypatch.setattr(
        vps,
        "run_ssh",
        lambda **kwargs: "Unexpected output\n"
    )

    with pytest.raises(RuntimeError):
        vps.backup_vps_containerd(
            host="192.168.0.104",
            user="kforge"
        )

def test_prepare_containerd_update_success(monkeypatch):
    from kubeforge.providers import vps

    calls = []

    def fake_status(host, user, port):
        calls.append("status")
        return "active"

    def fake_backup(host, user, port):
        calls.append("backup")
        return "/var/backups/kubeforge/containerd/config.toml.ABC12345"

    monkeypatch.setattr(
        vps, "get_vps_containerd_status", fake_status
    )
    monkeypatch.setattr(
        vps, "backup_vps_containerd", fake_backup
    )

    result = vps.prepare_vps_containerd_update(
        "192.168.0.104", "kforge"
    )

    assert result.endswith("config.toml.ABC12345")
    assert calls == ["status", "backup"]


def test_prepare_containerd_update_inactive(monkeypatch):
    import pytest
    from kubeforge.providers import vps

    monkeypatch.setattr(
        vps,
        "get_vps_containerd_status",
        lambda **kwargs: "inactive"
    )

    def forbidden_backup(**kwargs):
        pytest.fail("Backup must not run when containerd is inactive")

    monkeypatch.setattr(
        vps, "backup_vps_containerd", forbidden_backup
    )

    with pytest.raises(RuntimeError):
        vps.prepare_vps_containerd_update(
            "192.168.0.104", "kforge"
        )

def test_containerd_backup_path_valid():
    from kubeforge.providers.vps import (
        validate_containerd_backup_path
    )

    path = (
        "/var/backups/kubeforge/containerd/"
        "config.toml.ABC12345"
    )

    assert validate_containerd_backup_path(path) == path


def test_containerd_backup_path_invalid():
    import pytest
    from kubeforge.providers.vps import (
        validate_containerd_backup_path
    )

    with pytest.raises(ValueError):
        validate_containerd_backup_path(
            "/var/backups/kubeforge/containerd/"
            "../../etc/passwd"
        )

def test_verify_vps_containerd_backup_success(monkeypatch):
    from kubeforge.providers import vps

    def fake_ssh(host, user, command, port):
        assert host == "192.168.0.104"
        assert user == "kforge"
        assert port == 22
        assert command == (
            "printf '%s\\n' ABC12345 | "
            "sudo -n /usr/local/sbin/kubeforge-admin "
            "containerd-verify"
        )
        return "BACKUP_OK\n"

    monkeypatch.setattr(vps, "run_ssh", fake_ssh)

    result = vps.verify_vps_containerd_backup(
        "192.168.0.104",
        "kforge",
        "/var/backups/kubeforge/containerd/config.toml.ABC12345"
    )

    assert result is True


def test_verify_vps_containerd_backup_invalid_path(monkeypatch):
    import pytest
    from kubeforge.providers import vps

    def forbidden_ssh(**kwargs):
        pytest.fail("SSH must not run for an invalid path")

    monkeypatch.setattr(vps, "run_ssh", forbidden_ssh)

    with pytest.raises(ValueError):
        vps.verify_vps_containerd_backup(
            "192.168.0.104",
            "kforge",
            "/etc/passwd"
        )


def test_verify_vps_containerd_backup_failure(monkeypatch):
    import pytest
    from kubeforge.providers import vps

    monkeypatch.setattr(
        vps,
        "run_ssh",
        lambda **kwargs: "BACKUP_INVALID\n"
    )

    with pytest.raises(RuntimeError):
        vps.verify_vps_containerd_backup(
            "192.168.0.104",
            "kforge",
            "/var/backups/kubeforge/containerd/config.toml.ABC12345"
        )
