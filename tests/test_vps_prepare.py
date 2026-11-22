import pytest
from typer.testing import CliRunner

from kubeforge.cli import app
from kubeforge.providers.vps_prepare import (
    get_vps_host_facts,
    build_vps_prepare_plan,
)


FRESH_FACTS = {
    "OS_ID": "ubuntu",
    "VERSION_ID": "26.04",
    "ARCH": "x86_64",
    "KUBEADM": "no",
    "CONTAINERD": "no",
    "SWAP": "no",
    "NODE": "fresh",
}


def test_prepare_plan_for_fresh_ubuntu():
    plan = build_vps_prepare_plan(FRESH_FACTS)

    assert len(plan) == 10
    assert any("pkgs.k8s.io" in step for step in plan)
    assert any("containerd" in step for step in plan)


def test_prepare_rejects_initialized_node():
    facts = {**FRESH_FACTS, "NODE": "initialized"}

    with pytest.raises(RuntimeError, match="initialized"):
        build_vps_prepare_plan(facts)


def test_prepare_rejects_unsupported_os():
    facts = {**FRESH_FACTS, "OS_ID": "debian"}

    with pytest.raises(ValueError, match="Ubuntu"):
        build_vps_prepare_plan(facts)


def test_prepare_rejects_existing_containerd():
    facts = {**FRESH_FACTS, "CONTAINERD": "yes"}

    with pytest.raises(RuntimeError, match="Existing"):
        build_vps_prepare_plan(facts)


def test_vps_host_inspection(monkeypatch):
    output = "\n".join(
        f"{key}={value}"
        for key, value in FRESH_FACTS.items()
    )

    monkeypatch.setattr(
        "kubeforge.providers.vps_prepare.run_ssh",
        lambda **kwargs: output,
    )

    result = get_vps_host_facts(
        "192.168.0.200",
        "kforge",
    )

    assert result == FRESH_FACTS


def test_prepare_cli_refuses_initialized_node(monkeypatch):
    facts = {**FRESH_FACTS, "NODE": "initialized"}

    monkeypatch.setattr(
        "kubeforge.cli.get_vps_host_facts",
        lambda **kwargs: facts,
    )

    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "vps", "prepare-plan",
            "--host", "192.168.0.104",
            "--user", "kforge",
        ],
    )

    assert result.exit_code == 1
    assert "preparation refused" in result.output
