import shutil

from kubeforge.providers.local import check_docker, check_kind

def check_kubectl():
    if shutil.which("kubectl") is None:
        raise RuntimeError("kubectl is not installed.")

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

    return all_ok
