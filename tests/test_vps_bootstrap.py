import pytest

from kubeforge.providers.vps_bootstrap import (
    build_kubeadm_init_command,
    get_kubernetes_node_state,
)


def test_build_kubeadm_init_command():
    command = build_kubeadm_init_command(
        "192.168.0.104",
        "10.244.0.0/16",
    )

    assert command == (
        "kubeadm init "
        "--apiserver-advertise-address=192.168.0.104 "
        "--pod-network-cidr=10.244.0.0/16"
    )


def test_reject_invalid_api_address():
    with pytest.raises(ValueError):
        build_kubeadm_init_command(
            "invalid-ip",
            "10.244.0.0/16",
        )


def test_reject_overlapping_network():
    with pytest.raises(ValueError):
        build_kubeadm_init_command(
            "192.168.0.104",
            "192.168.0.0/24",
        )


@pytest.mark.parametrize(
    "response",
    ["FRESH\n", "INITIALIZED\n"],
)
def test_get_kubernetes_node_state(monkeypatch, response):
    captured = {}

    def fake_run_ssh(**kwargs):
        captured.update(kwargs)
        return response

    monkeypatch.setattr(
        "kubeforge.providers.vps_bootstrap.run_ssh",
        fake_run_ssh,
    )

    state = get_kubernetes_node_state(
        "192.168.0.104",
        "kforge",
    )

    assert state == response.strip()
    assert captured["host"] == "192.168.0.104"
    assert captured["user"] == "kforge"


def test_reject_unexpected_node_state(monkeypatch):
    monkeypatch.setattr(
        "kubeforge.providers.vps_bootstrap.run_ssh",
        lambda **kwargs: "UNKNOWN\n",
    )

    with pytest.raises(RuntimeError):
        get_kubernetes_node_state(
            "192.168.0.104",
            "kforge",
        )
