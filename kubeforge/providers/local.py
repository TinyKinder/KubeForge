import subprocess

def cluster_exists(cluster_name: str) -> bool:
    result = subprocess.run(
        ["kind", "get", "clusters"],
        capture_output=True,
        text=True,
        check=True
    )

    clusters = result.stdout.splitlines()

    return cluster_name in clusters

def create_local_cluster(cluster_name: str):

    if cluster_exists(cluster_name):
        print(f"Cluster '{cluster_name}' already exists.")
        return

    print(f"Creating cluster '{cluster_name}'...")

    subprocess.run(
        ["kind", "create", "cluster", "--name", cluster_name, "--wait", "5m"],
        check=True
    )

    print("Cluster created successfully!")

def get_local_cluster_status(cluster_name: str):
    result = subprocess.run(
        [
            "kubectl",
            "--context", f"kind-{cluster_name}", 
            "get", "nodes"
        ],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(result.stdout)
    else:
        print("Cannot connect to the Kubernetes cluster.")
        print(result.stderr)

def delete_local_cluster(cluster_name: str):

    if not cluster_exists(cluster_name):
        print(f"Cluster '{cluster_name}' does not exist.")
        return

    subprocess.run(
        ["kind", "delete", "cluster", "--name", cluster_name],
        check=True
    )

    print(f"Cluster '{cluster_name}' deleted successfully!")
