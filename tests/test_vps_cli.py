from typer.testing import CliRunner

from kubeforge.cli import app


runner = CliRunner()


def test_init_plan_rejects_initialized_node(monkeypatch):
    monkeypatch.setattr(
        "kubeforge.cli.get_kubernetes_node_state",
        lambda **kwargs: "INITIALIZED",
    )

    result = runner.invoke(
        app,
        [
            "vps",
            "init-plan",
            "--host", "192.168.0.104",
            "--user", "kforge",
            "--api-address", "192.168.0.104",
        ],
    )

    assert result.exit_code == 1
    assert "Bootstrap refused" in result.output
    assert "Bootstrap planning failed" not in result.output


def test_init_plan_allows_fresh_node(monkeypatch):
    monkeypatch.setattr(
        "kubeforge.cli.get_kubernetes_node_state",
        lambda **kwargs: "FRESH",
    )

    result = runner.invoke(
        app,
        [
            "vps",
            "init-plan",
            "--host", "192.168.0.200",
            "--user", "kforge",
            "--api-address", "192.168.0.200",
        ],
    )

    assert result.exit_code == 0
    assert "Kubernetes state: FRESH" in result.output
    assert "kubeadm init" in result.output
    assert "No changes were made" in result.output


def test_init_plan_rejects_invalid_ip(monkeypatch):
    def unexpected_ssh(**kwargs):
        raise AssertionError("SSH should not be called")

    monkeypatch.setattr(
        "kubeforge.cli.get_kubernetes_node_state",
        unexpected_ssh,
    )

    result = runner.invoke(
        app,
        [
            "vps",
            "init-plan",
            "--host", "192.168.0.104",
            "--user", "kforge",
            "--api-address", "invalid-ip",
        ],
    )

    assert result.exit_code == 1
    assert "Bootstrap planning failed" in result.output
