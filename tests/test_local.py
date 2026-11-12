import yaml
import pytest

from kubeforge.providers.local import generate_kind_config


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
