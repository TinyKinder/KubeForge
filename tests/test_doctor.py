from kubeforge.core import doctor
from types import SimpleNamespace

def test_doctor_success(monkeypatch, capsys):
    monkeypatch.setattr(
        doctor, "check_docker", lambda: None
    )

    monkeypatch.setattr(
        doctor, "check_kind", lambda: None
    )

    monkeypatch.setattr(
        doctor, "check_kubectl", lambda: None
    )

    result = doctor.run_doctor()
    output = capsys.readouterr().out

    assert result is True
    assert "[OK] Docker" in output
    assert "[OK] kind" in output
    assert "[OK] kubectl" in output

def test_doctor_failure(monkeypatch, capsys):

    def fake_check_docker():
        raise RuntimeError("Docker daemon unavailable")

    monkeypatch.setattr(
        doctor, "check_docker", fake_check_docker
    )

    monkeypatch.setattr(
        doctor, "check_kind", lambda: None
    )

    monkeypatch.setattr(
        doctor, "check_kubectl", lambda: None
    )

    result = doctor.run_doctor()
    output = capsys.readouterr().out

    assert result is False
    assert "[FAIL] Docker" in output
    assert "[OK] kind" in output
    assert "[OK] kubectl" in output

def test_low_memory_warning(monkeypatch, capsys):
    fake_memory = SimpleNamespace(
        total=4 * 1024**3,
        available=1 * 1024**3
    )

    monkeypatch.setattr(
        doctor.psutil,
        "virtual_memory",
        lambda: fake_memory
    )

    doctor.check_memory()

    output = capsys.readouterr().out

    assert "[INFO] RAM:" in output
    assert "[WARN] Low available RAM" in output

def test_low_disk_warning(monkeypatch, capsys):
    fake_disk = SimpleNamespace(
        total=20 * 1024**3,
        free=2 * 1024**3
    )

    monkeypatch.setattr(
        doctor.psutil,
        "disk_usage",
        lambda path: fake_disk
    )

    doctor.check_disk()

    output = capsys.readouterr().out

    assert "[INFO] Disk:" in output
    assert "[WARN] Low disk space" in output

def test_enough_disk_space(monkeypatch, capsys):
    fake_disk = SimpleNamespace(
        total=20 * 1024**3,
        free=10 * 1024**3
    )

    monkeypatch.setattr(
        doctor.psutil,
        "disk_usage",
        lambda path: fake_disk
    )

    doctor.check_disk()

    output = capsys.readouterr().out

    assert "[INFO] Disk:" in output
    assert "[WARN] Low disk space" not in output
