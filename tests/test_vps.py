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
