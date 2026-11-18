
import yaml

from kubeforge.core.models import ClusterConfig, VPSConfig


def load_config():
    with open("kubeforge.yaml", "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict) or not isinstance(config.get("cluster"), dict):
        raise ValueError("Missing or invalid 'cluster' section")

    cluster = ClusterConfig.model_validate(config["cluster"])
    config["cluster"] = cluster.model_dump()

    if "vps" in config:
        vps = VPSConfig.model_validate(config["vps"])
        config["vps"] = vps.model_dump()

    return config


