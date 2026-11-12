from kubeforge.providers.local import create_local_cluster
from kubeforge.providers.local import delete_local_cluster
from kubeforge.providers.local import get_local_cluster_status

def create_cluster(provider: str, cluster_name: str):
    if provider == "local":
        create_local_cluster(cluster_name)
    else:
        print(f"Provider '{provider}' is not implemented yet")

def delete_cluster(provider: str, cluster_name: str):
    if provider == "local":
        delete_local_cluster(cluster_name)
    else:
        print(f"Provider '{provider}' is not implemented yet")

def get_cluster_status(provider: str, cluster_name: str):
    if provider == "local":
        get_local_cluster_status(cluster_name)
    else:
        print(f"Provider '{provider}' is not implemented yet")
