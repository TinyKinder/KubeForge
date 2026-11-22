from ipaddress import IPv4Address, IPv4Network

from kubeforge.core.ssh import run_ssh


def get_kubernetes_node_state(
    host: str,
    user: str,
    port: int = 22,
) -> str:
    command = (
        "if [ -f /etc/kubernetes/admin.conf ] || "
        "[ -f /etc/kubernetes/kubelet.conf ] || "
        "[ -d /var/lib/etcd/member ]; then "
        "printf 'INITIALIZED\\n'; "
        "else printf 'FRESH\\n'; fi"
    )

    output = run_ssh(
        host=host,
        user=user,
        command=command,
        port=port,
    ).strip()

    if output not in {"INITIALIZED", "FRESH"}:
        raise RuntimeError(
            f"Unexpected Kubernetes node state: {output}"
        )

    return output


def build_kubeadm_init_command(
    api_address: str,
    pod_cidr: str = "10.244.0.0/16",
) -> str:
    address = IPv4Address(api_address)
    network = IPv4Network(pod_cidr, strict=False)

    if address in network:
        raise ValueError(
            "Pod network overlaps the Control Plane address"
        )

    return (
        "kubeadm init "
        f"--apiserver-advertise-address={address} "
        f"--pod-network-cidr={network}"
    )
