from kubeforge.core.ssh import run_ssh


SUPPORTED_UBUNTU = {"22.04", "24.04", "26.04"}
SUPPORTED_K8S = {"v1.35", "v1.36", "v1.37"}


def get_vps_host_facts(
    host: str,
    user: str,
    port: int = 22,
) -> dict[str, str]:
    command = (
        ". /etc/os-release; "
        'printf "OS_ID=%s\\nVERSION_ID=%s\\n" "$ID" "$VERSION_ID"; '
        'printf "ARCH=%s\\n" "$(uname -m)"; '
        'if command -v kubeadm >/dev/null 2>&1; '
        'then echo "KUBEADM=yes"; else echo "KUBEADM=no"; fi; '
        'if command -v containerd >/dev/null 2>&1; '
        'then echo "CONTAINERD=yes"; else echo "CONTAINERD=no"; fi; '
        'if [ "$(wc -l </proc/swaps)" -gt 1 ]; '
        'then echo "SWAP=yes"; else echo "SWAP=no"; fi; '
        'if [ -f /etc/kubernetes/admin.conf ] || '
        '[ -f /etc/kubernetes/kubelet.conf ] || '
        '[ -d /var/lib/etcd/member ]; '
        'then echo "NODE=initialized"; else echo "NODE=fresh"; fi'
    )

    output = run_ssh(
        host=host,
        user=user,
        command=command,
        port=port,
    )

    required = {
        "OS_ID", "VERSION_ID", "ARCH",
        "KUBEADM", "CONTAINERD", "SWAP", "NODE",
    }

    facts = {}

    for line in output.splitlines():
        key, separator, value = line.partition("=")

        if separator and key in required:
            if key in facts:
                raise RuntimeError(f"Duplicate host fact: {key}")

            facts[key] = value.strip()

    if set(facts) != required:
        raise RuntimeError("Incomplete VPS inspection results")

    return facts


def build_vps_prepare_plan(
    facts: dict[str, str],
    kubernetes_version: str = "v1.37",
) -> list[str]:
    if facts["OS_ID"] != "ubuntu":
        raise ValueError("Only Ubuntu is supported")

    if facts["VERSION_ID"] not in SUPPORTED_UBUNTU:
        raise ValueError("Unsupported Ubuntu version")

    if facts["ARCH"] not in {"x86_64", "aarch64"}:
        raise ValueError("Unsupported CPU architecture")

    if kubernetes_version not in SUPPORTED_K8S:
        raise ValueError("Unsupported Kubernetes version")

    if facts["NODE"] != "fresh":
        raise RuntimeError(
            "Node is already initialized. Preparation refused."
        )

    if (
        facts["KUBEADM"] != "no"
        or facts["CONTAINERD"] != "no"
    ):
        raise RuntimeError(
            "Existing Kubernetes components detected. "
            "Manual inspection required."
        )

    return [
        "Check required CPU, memory and disk resources",
        "Install ca-certificates, curl, gpg and containerd",
        "Load overlay and br_netfilter kernel modules",
        "Configure persistent IPv4 forwarding",
        "Configure containerd with the systemd cgroup driver",
        "Disable swap and its automatic activation",
        (
            "Configure Kubernetes package repository: "
            "https://pkgs.k8s.io/core:/stable:/"
            f"{kubernetes_version}/deb/"
        ),
        "Install kubelet, kubeadm and kubectl",
        "Hold Kubernetes package versions",
        "Validate containerd, CRI and kubelet prerequisites",
    ]
