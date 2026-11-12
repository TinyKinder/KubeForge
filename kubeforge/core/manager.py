from kubeforge.providers.local import create_local_cluster
from kubeforge.providers.local import delete_local_cluster

def create_cluster(provider: str):
    if provider == "local":
        create_local_cluster()
    else:
        print(f"Provider '{provider}' is not implemented yet")

def delete_cluster(provider: str):
    if provider == "local":
        delete_local_cluster()
    else:
        print(f"Provider '{provider}' is not implemented yet")
