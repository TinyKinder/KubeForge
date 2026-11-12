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
