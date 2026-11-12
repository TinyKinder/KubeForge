import yaml
import pytest

from subprocess import CompletedProcess
from kubeforge.providers.local import (
    generate_kind_config,
    check_docker,
    check_kind,
)

def test_generate_kind_config():
    config_yaml = generate_kind_config(2)

    config = yaml.safe_load(config_yaml)

    assert len(config["nodes"]) == 3
    assert config["nodes"][0]["role"] == "control-plane"
    assert config["nodes"][1]["role"] == "worker"
    assert config["nodes"][2]["role"] == "worker"

@pytest.mark.parametrize("workers, expected_nodes", [
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
])
def test_worker_count(workers, expected_nodes):
    config_yaml = generate_kind_config(workers)
    config = yaml.safe_load(config_yaml)

    assert len(config["nodes"]) == expected_nodes

def test_negative_workers():
    with pytest.raises(ValueError):
        generate_kind_config(-1)

def test_docker_not_installed(monkeypatch):
    monkeypatch.setattr(
        "kubeforge.providers.local.shutil.which",
        lambda name: None
    )

    with pytest.raises(
        RuntimeError,
        match="Docker is not installed"
    ):
        check_docker()

def test_docker_daemon_unavailable(monkeypatch):
    monkeypatch.setattr(
        "kubeforge.providers.local.shutil.which",
        lambda name: "/usr/bin/docker"
    )

    def fake_run(command, **kwargs):
        assert command == ["docker", "info"]

        return CompletedProcess(
            command,
            returncode=1,
            stdout="",
            stderr="Cannot connect to Docker daemon"
        )

    monkeypatch.setattr(
        "kubeforge.providers.local.subprocess.run",
        fake_run
    )

    with pytest.raises(
        RuntimeError,
        match="Docker daemon is unavailable"
    ):
        check_docker()

def test_kind_not_installed(monkeypatch):
    monkeypatch.setattr(
        "kubeforge.providers.local.shutil.which",
        lambda name: None
    )

    with pytest.raises(
        RuntimeError,
        match="kind is not installed"
    ):
        check_kind()
