import re

from kubeforge.core.ssh import run_ssh

def get_vps_cluster_status(
    host: str,
    user: str,
    port: int = 22
):
    return run_ssh(
        host=host,
        user=user,
        command="kubectl get nodes -o wide",
        port=port
    )

def is_vps_cluster_initialized(
    host: str,
    user: str,
    port: int = 22
) -> bool:
    result = run_ssh(
        host=host,
        user=user,
        command=(
            "if test -f /etc/kubernetes/admin.conf; "
            "then echo initialized; "
            "else echo not_initialized; fi"
        ),
        port=port
    )

    return result.strip() == "initialized"

def is_vps_api_ready(
    host: str,
    user: str,
    port: int = 22
) -> bool:
    result = run_ssh(
        host=host,
        user=user,
        command="kubectl get --raw=/readyz",
        port=port
    )

    return result.strip() == "ok"


def get_vps_resources(
    host: str,
    user: str,
    port: int = 22
) -> dict:
    output = run_ssh(
        host=host,
        user=user,
        command=(
            "nproc; "
            "awk '/MemTotal:/ {print $2}' /proc/meminfo; "
            "df -Pk / | awk 'NR==2 {print $4}'"
        ),
        port=port
    )

    cpu, ram_kib, disk_kib = map(
        int, output.strip().splitlines()
    )

    return {
        "cpu": cpu,
        "ram_gib": round(ram_kib / 1024**2, 2),
        "disk_free_gib": round(disk_kib / 1024**2, 2)
    }


def check_vps_preflight(resources: dict, role: str) -> list[str]:
    errors = []

    min_cpu = 2 if role == "control-plane" else 1

    if resources["cpu"] < min_cpu:
        errors.append(
            f"Not enough CPU: minimum {min_cpu} required"
        )

    if resources["ram_gib"] < 2:
        errors.append(
            "Not enough RAM: minimum 2 GiB required"
        )

    if resources["disk_free_gib"] < 5:
        errors.append(
            "Not enough disk space: minimum 5 GiB free required"
        )

    return errors

def run_vps_preflight(vps_config: dict) -> dict:
    results = {}

    nodes = [
        ("control-plane", vps_config["control_plane"])
    ]

    for worker in vps_config.get("workers", []):
        nodes.append(("worker", worker))

    for role, node in nodes:
        resources = get_vps_resources(
            host=node["host"],
            user=node["user"],
            port=node["port"]
        )

        errors = check_vps_preflight(resources, role)

        results[node["host"]] = {
            "role": role,
            "resources": resources,
            "errors": errors
        }

    return results


def get_vps_containerd_status(
    host: str,
    user: str,
    port: int = 22
) -> str:
    output = run_ssh(
        host=host,
        user=user,
        command=(
            "sudo -n /usr/local/sbin/kubeforge-admin "
            "containerd-status"
        ),
        port=port
    )

    return output.strip()

def backup_vps_containerd(
    host: str,
    user: str,
    port: int = 22
) -> str:
    output = run_ssh(
        host=host,
        user=user,
        command=(
            "sudo -n /usr/local/sbin/kubeforge-admin "
            "containerd-backup"
        ),
        port=port
    ).strip()

    prefix = "Backup created: "
    expected_dir = "/var/backups/kubeforge/containerd/config.toml."

    if not output.startswith(prefix + expected_dir):
        raise RuntimeError(
            f"Unexpected containerd backup response: {output}"
        )

    return validate_containerd_backup_path(
        output.removeprefix(prefix)
    )

def prepare_vps_containerd_update(
    host: str,
    user: str,
    port: int = 22
) -> str:
    status = get_vps_containerd_status(
        host=host,
        user=user,
        port=port
    )

    if status != "active":
        raise RuntimeError(
            f"containerd is not active on {host}"
        )

    backup_path = backup_vps_containerd(
        host=host,
        user=user,
        port=port
    )

    return backup_path

def validate_containerd_backup_path(path: str) -> str:
    pattern = (
        r"/var/backups/kubeforge/containerd/"
        r"config\.toml\.[A-Za-z0-9]{8}"
    )

    if not re.fullmatch(pattern, path):
        raise ValueError("Invalid containerd backup path")

    return path

def verify_vps_containerd_backup(
    host: str,
    user: str,
    backup_path: str,
    port: int = 22
) -> bool:
    validated_path = validate_containerd_backup_path(
        backup_path
    )

    backup_id = validated_path.rsplit(".", 1)[-1]

    output = run_ssh(
        host=host,
        user=user,
        command=(
            f"printf '%s\\n' {backup_id} | "
            "sudo -n /usr/local/sbin/kubeforge-admin "
            "containerd-verify"
        ),
        port=port
    )

    if output.strip() != "BACKUP_OK":
        raise RuntimeError("Containerd backup verification failed")

    return True
