from kubeforge.providers.vps import get_vps_cluster_status
from kubeforge.providers.local import create_local_cluster
from kubeforge.providers.local import delete_local_cluster
from kubeforge.providers.local import get_local_cluster_status

def create_cluster(provider: str, cluster_name: str, workers: int):
    if provider == "local":
        create_local_cluster(cluster_name, workers)
    else:
        print(f"Provider '{provider}' is not implemented yet")

def delete_cluster(provider: str, cluster_name: str):
    if provider == "local":
        delete_local_cluster(cluster_name)
    else:
        print(f"Provider '{provider}' is not implemented yet")

def get_cluster_status(
    provider: str,
    cluster_name: str,
    vps_config: dict | None = None
):
    if provider == "local":
        return get_local_cluster_status(cluster_name)

    if provider == "vps":
        if vps_config is None:
            raise ValueError("Missing VPS configuration")

        control_plane = vps_config["control_plane"]

        return get_vps_cluster_status(
            host=control_plane["host"],
            user=control_plane["user"],
            port=control_plane["port"]
        )

    raise ValueError(f"Unsupported provider: {provider}")
