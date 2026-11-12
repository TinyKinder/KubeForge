import shutil
import psutil

from kubeforge.providers.local import check_docker, check_kind

def check_kubectl():
    if shutil.which("kubectl") is None:
        raise RuntimeError("kubectl is not installed.")

def check_memory():
    memory = psutil.virtual_memory()

    total = memory.total / (1024 ** 3)
    available = memory.available / (1024 ** 3)

    print(f"[INFO] RAM: {available:.2f} GiB available / {total:.2f} GiB total")

    if available < 1.5:
        print("[WARN] Low available RAM. Kubernetes cluster creation may fail.")

def check_disk():
    disk = psutil.disk_usage("/")

    total = disk.total / (1024 ** 3)
    free = disk.free / (1024 ** 3)

    print(f"[INFO] Disk: {free:.2f} GiB free / {total:.2f} GiB total")

    if free < 5:
        print("[WARN] Low disk space. Kubernetes cluster creation may fail.")

def check_cpu():
    cores = psutil.cpu_count(logical=True)
    usage = psutil.cpu_percent(interval=1)

    print(f"[INFO] CPU: {cores} logical cores")
    print(f"[INFO] CPU usage: {usage:.1f}%")

def run_doctor() -> bool:
    checks = [
        ("Docker", check_docker),
        ("kind", check_kind),
        ("kubectl", check_kubectl),
    ]
    all_ok = True

    for name, check in checks:
        try:
            check()
            print(f"[OK] {name}")
        except (RuntimeError, OSError) as error:
            print(f"[FAIL] {name}: {error}")
            all_ok = False

    check_memory()
    check_disk()
    check_cpu()
    return all_ok
