import pytest
from pydantic import ValidationError

from kubeforge.core.config import load_config


def test_invalid_workers(tmp_path, monkeypatch):
    config_file = tmp_path / "kubeforge.yaml"

    config_file.write_text("""
cluster:
  name: test-cluster
  provider: local
  workers: -5
""")

    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValidationError):
        load_config()

def test_valid_config(tmp_path, monkeypatch):
    config_file = tmp_path / "kubeforge.yaml"

    config_file.write_text("""
cluster:
  name: dev-cluster
  provider: local
  workers: 2
""")

    monkeypatch.chdir(tmp_path)

    config = load_config()

    assert config["cluster"]["name"] == "dev-cluster"
    assert config["cluster"]["provider"] == "local"
    assert config["cluster"]["workers"] == 2
