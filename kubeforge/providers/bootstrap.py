import tempfile
import tomllib
import re
import subprocess
from pathlib import Path
from kubeforge.core.ssh import run_ssh

def build_containerd_install_plan() -> list[str]:
    return [
        "sudo -n apt-get update",
        "sudo -n apt-get install -y containerd"
    ]


def execute_remote_plan(
    host: str,
    user: str,
    commands: list[str],
    port: int = 22,
    dry_run: bool = True
) -> list[str]:

    results = []

    for command in commands:

        if dry_run:
            results.append(f"[DRY-RUN] {command}")
            continue

        output = run_ssh(
            host=host,
            user=user,
            command=command,
            port=port
        )

        results.append(output)

    return results


def build_kubeadm_install_plan() -> list[str]:
    repo = "https://pkgs.k8s.io/core:/stable:/v1.37/deb/"
    keyring = "/etc/apt/keyrings/kubernetes-apt-keyring.gpg"

    return [
        "sudo -n apt-get update",
        "sudo -n apt-get install -y ca-certificates curl gpg",
        "sudo -n mkdir -p -m 755 /etc/apt/keyrings",
        (
            f"curl -fsSL {repo}Release.key | "
            f"sudo -n gpg --batch --yes --dearmor -o {keyring}"
        ),
        (
            f"echo 'deb [signed-by={keyring}] {repo} /' | "
            "sudo -n tee /etc/apt/sources.list.d/kubernetes.list"
        ),
        "sudo -n apt-get update",
        "sudo -n apt-get install -y kubelet kubeadm kubectl",
        "sudo -n apt-mark hold kubelet kubeadm kubectl"
    ]


def build_k8s_network_plan() -> list[str]:
    return [
        "sudo -n modprobe overlay",
        "sudo -n modprobe br_netfilter",
        (
            "printf 'overlay\\nbr_netfilter\\n' | "
            "sudo -n tee /etc/modules-load.d/k8s.conf"
        ),
        (
            "printf 'net.bridge.bridge-nf-call-iptables = 1\\n"
            "net.ipv4.ip_forward = 1\\n' | "
            "sudo -n tee /etc/sysctl.d/99-kubernetes.conf"
        ),
        "sudo -n sysctl --system"
    ]


def build_k8s_swap_plan() -> list[str]:
    return [
        "sudo -n swapoff -a",
        "sudo -n cp -n /etc/fstab /etc/fstab.kubeforge.bak",
        (
            "sudo -n sed -i -E "
            "'/^[[:space:]]*[^#[:space:]]+[[:space:]]+"
            "[^[:space:]]+[[:space:]]+swap[[:space:]]/ "
            "s/^/# /' /etc/fstab"
        ),
        "swapon --show"
    ]


def build_vps_bootstrap_plan() -> list[str]:
    return [
        *build_k8s_swap_plan(),
        *build_k8s_network_plan(),
        *build_containerd_install_plan(),
        *build_kubeadm_install_plan()
    ]


def check_containerd_cgroup(
    host: str,
    user: str,
    port: int = 22
) -> bool:
    output = run_ssh(
        host=host,
        user=user,
        command="containerd config dump",
        port=port
    )

    return bool(
        re.search(
            r"(?m)^\s*SystemdCgroup\s*=\s*true\s*$",
            output
        )
    )


def enable_systemd_cgroup(config_text: str) -> str:
    section = (
        "[plugins.'io.containerd.cri.v1.runtime'"
        ".containerd.runtimes.runc.options]"
    )

    lines = config_text.splitlines()

    try:
        start = next(
            i for i, line in enumerate(lines)
            if line.strip() == section
        )
    except StopIteration:
        raise ValueError(
            "containerd 2.x runc options section not found"
        ) from None

    end = next(
        (
            i for i in range(start + 1, len(lines))
            if lines[i].strip().startswith("[")
        ),
        len(lines)
    )

    for i in range(start + 1, end):
        if lines[i].strip().startswith("SystemdCgroup ="):
            lines[i] = "  SystemdCgroup = true"
            break
    else:
        lines.insert(end, "  SystemdCgroup = true")

    return "\n".join(lines) + "\n"


def validate_containerd_config(config_text: str) -> bool:
    try:
        config = tomllib.loads(config_text)

        options = (
            config["plugins"]
            ["io.containerd.cri.v1.runtime"]
            ["containerd"]
            ["runtimes"]
            ["runc"]
            ["options"]
        )

        if options.get("SystemdCgroup") is not True:
            raise ValueError(
                "SystemdCgroup must be true"
            )

    except (tomllib.TOMLDecodeError, KeyError, TypeError) as error:
        raise ValueError(
            f"Invalid containerd configuration: {error}"
        ) from error

    return True


def prepare_containerd_config(config_text: str) -> str:
    try:
        tomllib.loads(config_text)
    except tomllib.TOMLDecodeError as error:
        raise ValueError(
            f"Invalid original containerd configuration: {error}"
        ) from error

    updated_config = enable_systemd_cgroup(config_text)

    validate_containerd_config(updated_config)

    return updated_config


def prepare_remote_containerd_config(
    host: str,
    user: str,
    port: int = 22
) -> tuple[str, str]:

    original = run_ssh(
        host=host,
        user=user,
        command="cat /etc/containerd/config.toml",
        port=port
    )

    updated = prepare_containerd_config(original)

    return original, updated


def build_containerd_backup_plan() -> list[str]:
    config = "/etc/containerd/config.toml"
    backup = "/etc/containerd/config.toml.kubeforge.bak"

    return [
        f"sudo -n test -f {config}",
        f"sudo -n cp -p -n {config} {backup}"
    ]


def create_containerd_staging_file(config_text: str) -> str:
    prepared = prepare_containerd_config(config_text)

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix="kubeforge-containerd-",
        suffix=".toml",
        delete=False
    ) as temp:
        temp.write(prepared)
        return temp.name


def upload_containerd_staging_file(
    host: str,
    user: str,
    local_path: str,
    port: int = 22,
    dry_run: bool = True
) -> str:

    local_file = Path(local_path)

    if not local_file.is_file():
        raise FileNotFoundError(local_path)

    remote_path = f"~/{local_file.name}"

    command = [
        "scp",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=yes",
        "-o", "ConnectTimeout=10",
        "-P", str(port),
        str(local_file),
        f"{user}@{host}:{remote_path}"
    ]

    if dry_run:
        return f"[DRY-RUN] {' '.join(command)}"

    subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True
    )

    return f"Uploaded to {host}:{remote_path}"


def validate_remote_containerd_staging(
    host: str,
    user: str,
    filename: str,
    port: int = 22
) -> bool:

    if not re.fullmatch(
        r"kubeforge-containerd-[A-Za-z0-9._-]+\.toml",
        filename
    ):
        raise ValueError("Invalid staging filename")

    command = (
        f'containerd --config "$HOME/{filename}" '
        'config dump >/dev/null && echo VALID'
    )

    output = run_ssh(
        host=host,
        user=user,
        command=command,
        port=port
    )

    return output.strip() == "VALID"


def build_containerd_rollback_plan() -> list[str]:
    config = "/etc/containerd/config.toml"
    backup = "/etc/containerd/config.toml.kubeforge.bak"

    return [
        f"sudo -n test -s {backup}",
        f"sudo -n cp -p {backup} {config}",
        "sudo -n systemctl restart containerd",
        "sudo -n systemctl is-active --quiet containerd"
    ]


def verify_containerd_backup(
    host: str,
    user: str,
    port: int = 22
) -> bool:
    config = "/etc/containerd/config.toml"
    backup = "/etc/containerd/config.toml.kubeforge.bak"

    command = (
        f"sudo -n test -s {backup} && "
        f"sudo -n cmp -s {config} {backup} && "
        "echo BACKUP_OK"
    )

    output = run_ssh(
        host=host,
        user=user,
        command=command,
        port=port
    )

    return output.strip() == "BACKUP_OK"


def build_containerd_apply_plan(filename: str) -> list[str]:
    if not re.fullmatch(
        r"kubeforge-containerd-[A-Za-z0-9._-]+\.toml",
        filename
    ):
        raise ValueError("Invalid staging filename")

    config = "/etc/containerd/config.toml"
    backup = "/etc/containerd/config.toml.kubeforge.bak"
    staging = "/etc/containerd/config.toml.kubeforge.new"
    remote_file = f'"$HOME/{filename}"'

    return [
        f"containerd --config {remote_file} config dump >/dev/null",
        f"sudo -n test -s {backup}",
        f"sudo -n cmp -s {config} {backup}",
        f"sudo -n install -m 0644 {remote_file} {staging}",
        f"sudo -n mv -f {staging} {config}",
        "sudo -n systemctl restart containerd",
        "sudo -n systemctl is-active --quiet containerd"
    ]


def apply_containerd_config_with_rollback(
    host: str,
    user: str,
    filename: str,
    port: int = 22,
    dry_run: bool = True
) -> list[str]:

    commands = build_containerd_apply_plan(filename)

    if dry_run:
        return [f"[DRY-RUN] {cmd}" for cmd in commands]

    results = []
    replacement_started = False

    try:
        for index, command in enumerate(commands):
            if index == 4:
                replacement_started = True

            output = run_ssh(
                host=host,
                user=user,
                command=command,
                port=port
            )

            results.append(output)

    except (subprocess.CalledProcessError, OSError) as error:
        if replacement_started:
            try:
                execute_remote_plan(
                    host=host,
                    user=user,
                    commands=build_containerd_rollback_plan(),
                    port=port,
                    dry_run=False
                )
            except (subprocess.CalledProcessError, OSError) as rollback_error:
                raise RuntimeError(
                    f"Containerd update failed: {error}. "
                    f"Rollback also failed: {rollback_error}"
                ) from rollback_error

        raise

    return results


def preview_containerd_update(
    host: str,
    user: str,
    config_text: str,
    port: int = 22
) -> list[str]:

    staging_path = Path(
        create_containerd_staging_file(config_text)
    )

    try:
        commands = []

        commands.extend(
            f"[DRY-RUN] {cmd}"
            for cmd in build_containerd_backup_plan()
        )

        commands.append(
            upload_containerd_staging_file(
                host=host,
                user=user,
                local_path=str(staging_path),
                port=port,
                dry_run=True
            )
        )

        commands.extend(
            f"[DRY-RUN] {cmd}"
            for cmd in build_containerd_apply_plan(
                staging_path.name
            )
        )

        return commands

    finally:
        staging_path.unlink(missing_ok=True)
