import subprocess

from typer.testing import CliRunner
from kubeforge.cli import app

runner = CliRunner()


def test_up_command(tmp_path, monkeypatch):
    config_file = tmp_path / "kubeforge.yaml"

    config_file.write_text("""
cluster:
  name: dev-cluster
  provider: local
  workers: 2
""")

    monkeypatch.chdir(tmp_path)

    calls = []

    def fake_create_cluster(provider, name, workers):
        calls.append((provider, name, workers))

    monkeypatch.setattr(
        "kubeforge.cli.create_cluster",
        fake_create_cluster
    )

    result = runner.invoke(app, ["up"])

    assert result.exit_code == 0
    assert calls == [("local", "dev-cluster", 2)]

def test_cli_overrides_config(tmp_path, monkeypatch):
    config_file = tmp_path / "kubeforge.yaml"

    config_file.write_text("""
cluster:
  name: dev-cluster
  provider: local
  workers: 2
""")

    monkeypatch.chdir(tmp_path)

    calls = []

    def fake_create_cluster(provider, name, workers):
        calls.append((provider, name, workers))

    monkeypatch.setattr(
        "kubeforge.cli.create_cluster",
        fake_create_cluster
    )

    result = runner.invoke(
        app,
        ["up", "--name", "production", "--provider", "aws"]
    )

    assert result.exit_code == 0
    assert calls == [("aws", "production", 2)]

def test_status_command(monkeypatch):
    calls = []

    def fake_get_cluster_status(provider, name):
        calls.append((provider, name))

    monkeypatch.setattr(
        "kubeforge.cli.get_cluster_status",
        fake_get_cluster_status
    )

    result = runner.invoke(
        app,
        ["status", "--provider", "local", "--name", "dev-cluster"]
    )

    assert result.exit_code == 0
    assert calls == [("local", "dev-cluster")]

def test_down_cancelled(monkeypatch):
    calls = []

    def fake_delete_cluster(provider, name):
        calls.append((provider, name))

    monkeypatch.setattr(
        "kubeforge.cli.delete_cluster",
        fake_delete_cluster
    )

    result = runner.invoke(
        app,
        ["down", "--name", "dev-cluster"],
        input="n\n"
    )

    assert result.exit_code == 0
    assert calls == []
    assert "Operation cancelled." in result.output

def test_down_confirmed(monkeypatch):
    calls = []

    def fake_delete_cluster(provider, name):
        calls.append((provider, name))

    monkeypatch.setattr(
        "kubeforge.cli.delete_cluster",
        fake_delete_cluster
    )

    result = runner.invoke(
        app,
        ["down", "--provider", "local", "--name", "dev-cluster"],
        input="y\n"
    )

    assert result.exit_code == 0
    assert calls == [("local", "dev-cluster")]

def test_up_docker_error(tmp_path, monkeypatch):
    config_file = tmp_path / "kubeforge.yaml"

    config_file.write_text("""
cluster:
  name: test-cluster
  provider: local
  workers: 2
""")

    monkeypatch.chdir(tmp_path)

    def fake_create_cluster(provider, name, workers):
        raise RuntimeError("Docker daemon is unavailable.")

    monkeypatch.setattr(
        "kubeforge.cli.create_cluster",
        fake_create_cluster
    )

    result = runner.invoke(app, ["up"])

    assert result.exit_code == 1
    assert "Docker daemon is unavailable." in result.output
    assert "Traceback" not in result.output

def test_up_kind_error(tmp_path, monkeypatch):
    config_file = tmp_path / "kubeforge.yaml"

    config_file.write_text("""
cluster:
  name: test-cluster
  provider: local
  workers: 2
""")

    monkeypatch.chdir(tmp_path)

    def fake_create_cluster(provider, name, workers):
        raise subprocess.CalledProcessError(
            1,
            ["kind", "create", "cluster"]
        )

    monkeypatch.setattr(
        "kubeforge.cli.create_cluster",
        fake_create_cluster
    )

    result = runner.invoke(app, ["up"])

    assert result.exit_code == 1
    assert "Command failed with exit code 1" in result.output
    assert "Traceback" not in result.output

def test_kind_not_installed(tmp_path, monkeypatch):
    config_file = tmp_path / "kubeforge.yaml"

    config_file.write_text("""
cluster:
  name: test-cluster
  provider: local
  workers: 2
""")

    monkeypatch.chdir(tmp_path)

    def fake_create_cluster(provider, name, workers):
        raise FileNotFoundError(
            2,
            "No such file or directory",
            "kind"
        )

    monkeypatch.setattr(
        "kubeforge.cli.create_cluster",
        fake_create_cluster
    )

    result = runner.invoke(app, ["up"])

    assert result.exit_code == 1
    assert "Required executable not found: kind" in result.output
    assert "Traceback" not in result.output

def test_status_uses_yaml_config(tmp_path, monkeypatch):
    config_file = tmp_path / "kubeforge.yaml"

    config_file.write_text("""
cluster:
  name: test-cluster
  provider: local
  workers: 2
""")

    monkeypatch.chdir(tmp_path)

    calls = []

    def fake_get_cluster_status(provider, name):
        calls.append((provider, name))

    monkeypatch.setattr(
        "kubeforge.cli.get_cluster_status",
        fake_get_cluster_status
    )

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert calls == [("local", "test-cluster")]

def test_down_uses_yaml_config(tmp_path, monkeypatch):
    config_file = tmp_path / "kubeforge.yaml"

    config_file.write_text("""
cluster:
  name: test-cluster
  provider: local
  workers: 2
""")

    monkeypatch.chdir(tmp_path)

    calls = []

    def fake_delete_cluster(provider, name):
        calls.append((provider, name))

    monkeypatch.setattr(
        "kubeforge.cli.delete_cluster",
        fake_delete_cluster
    )

    result = runner.invoke(
        app,
        ["down"],
        input="y\n"
    )

    assert result.exit_code == 0
    assert calls == [("local", "test-cluster")]
    assert "test-cluster" in result.output

def test_status_invalid_config(tmp_path, monkeypatch):
    config_file = tmp_path / "kubeforge.yaml"

    config_file.write_text("""
cluster:
  name: test-cluster
  provider: local
  workers: -1
""")

    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 1
    assert "Invalid KubeForge configuration" in result.output

def test_up_invalid_config(tmp_path, monkeypatch):
    config_file = tmp_path / "kubeforge.yaml"

    config_file.write_text("""
cluster:
  name: test-cluster
  provider: local
  workers: -5
""")

    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["up"])

    assert result.exit_code == 1
    assert "Invalid KubeForge configuration" in result.output

def test_down_invalid_config(tmp_path, monkeypatch):
    config_file = tmp_path / "kubeforge.yaml"

    config_file.write_text("""
cluster:
  name: test-cluster
  provider: local
  workers: -2
""")

    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["down"])

    assert result.exit_code == 1
    assert "Invalid KubeForge configuration" in result.output

def test_vps_status_command(tmp_path, monkeypatch):
    config_file = tmp_path / "kubeforge.yaml"

    config_file.write_text("""
cluster:
  name: kubeforge
  provider: local
  workers: 2

vps:
  control_plane:
    host: 192.168.0.104
    user: kforge
    port: 22
  workers:
    - host: 192.168.0.108
      user: kforge
      port: 22
""")

    monkeypatch.chdir(tmp_path)

    calls = []

    def fake_get_status(provider, name, vps_config):
        calls.append((provider, name, vps_config))
        return "k8s-control-plane Ready\nk8s-worker-1 Ready"

    monkeypatch.setattr(
        "kubeforge.cli.get_cluster_status",
        fake_get_status
    )

    result = runner.invoke(
        app,
        ["status", "--provider", "vps"]
    )

    assert result.exit_code == 0
    assert "k8s-control-plane Ready" in result.output
    assert "k8s-worker-1 Ready" in result.output

    assert calls[0][0] == "vps"
    assert calls[0][2]["control_plane"]["host"] == "192.168.0.104"


def test_vps_up_preflight_failure(tmp_path, monkeypatch):
    config_file = tmp_path / "kubeforge.yaml"

    config_file.write_text("""
cluster:
  name: kubeforge
  provider: vps
  workers: 0

vps:
  control_plane:
    host: 192.168.0.104
    user: kforge
    port: 22
""")

    monkeypatch.chdir(tmp_path)

    def fake_preflight(config):
        return {
            "192.168.0.104": {
                "role": "control-plane",
                "resources": {
                    "cpu": 1,
                    "ram_gib": 1.0,
                    "disk_free_gib": 2.0
                },
                "errors": ["Not enough CPU"]
            }
        }

    monkeypatch.setattr(
        "kubeforge.cli.run_vps_preflight",
        fake_preflight
    )

    result = runner.invoke(app, ["up"])

    assert result.exit_code == 1
    assert "[FAIL] Not enough CPU" in result.output


def test_vps_up_already_initialized(tmp_path, monkeypatch):
    config_file = tmp_path / "kubeforge.yaml"

    config_file.write_text("""
cluster:
  name: kubeforge
  provider: vps
  workers: 1

vps:
  control_plane:
    host: 192.168.0.104
    user: kforge
    port: 22
  workers:
    - host: 192.168.0.108
      user: kforge
      port: 22
""")

    monkeypatch.chdir(tmp_path)

    def fake_preflight(config):
        return {
            "192.168.0.104": {
                "role": "control-plane",
                "resources": {
                    "cpu": 2,
                    "ram_gib": 3.0,
                    "disk_free_gib": 10.0
                },
                "errors": []
            }
        }

    monkeypatch.setattr(
        "kubeforge.cli.run_vps_preflight",
        fake_preflight
    )

    monkeypatch.setattr(
        "kubeforge.cli.is_vps_cluster_initialized",
        lambda **kwargs: True
    )

    def forbidden_create(*args, **kwargs):
        raise AssertionError("Cluster creation must be skipped")

    monkeypatch.setattr(
        "kubeforge.cli.create_cluster",
        forbidden_create
    )

    result = runner.invoke(app, ["up"])

    assert result.exit_code == 0
    assert "Kubernetes is already initialized" in result.output
    assert "Deployment skipped" in result.output

