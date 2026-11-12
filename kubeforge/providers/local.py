import subprocess
import yaml
import tempfile
import shutil
from pathlib import Path

def cluster_exists(cluster_name: str) -> bool:
    result = subprocess.run(
        ["kind", "get", "clusters"],
        capture_output=True,
        text=True,
        check=True
    )

    clusters = result.stdout.splitlines()

    return cluster_name in clusters

def check_docker():
    if shutil.which("docker") is None:
        raise RuntimeError("Docker is not installed.")

    result = subprocess.run(
        ["docker", "info"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Docker daemon is unavailable or permission denied."
        )

def check_kind():
    if shutil.which("kind") is None:
        raise RuntimeError("kind is not installed.")

def generate_kind_config(workers: int):
    if workers < 0:
        raise ValueError("Workers cannot be negative")

    config = {
        "kind": "Cluster",
        "apiVersion": "kind.x-k8s.io/v1alpha4",
        "nodes": [
            {"role": "control-plane"}
        ]
    }

    for i in range(workers):
        config["nodes"].append({"role": "worker"})

    return yaml.safe_dump(config, sort_keys=False)

def create_local_cluster(cluster_name: str, workers: int):
    
    check_docker()
    check_kind()
    print(f"Requested worker nodes: {workers}")

    if cluster_exists(cluster_name):
        print(f"Cluster '{cluster_name}' already exists.")
        return

    print(f"Creating cluster '{cluster_name}'...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / "kind-config.yaml"

        config_path.write_text(
            generate_kind_config(workers),
            encoding="utf-8"
        )

        subprocess.run(
            [
                "kind", "create", "cluster",
                "--name", cluster_name,
                "--config", str(config_path),
                "--wait", "5m"
            ],
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
