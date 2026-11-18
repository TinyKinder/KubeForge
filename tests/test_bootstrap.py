import pytest

from kubeforge.providers.bootstrap import build_containerd_install_plan


def test_containerd_install_plan():
    commands = build_containerd_install_plan()

    assert len(commands) == 2
    assert commands[0] == "sudo -n apt-get update"
    assert commands[1] == "sudo -n apt-get install -y containerd"


def test_execute_remote_plan_dry_run(monkeypatch):
    from kubeforge.providers import bootstrap

    def forbidden_ssh(**kwargs):
        raise AssertionError("SSH must not be executed")

    monkeypatch.setattr(
        bootstrap,
        "run_ssh",
        forbidden_ssh
    )

    commands = [
        "sudo -n apt-get update",
        "sudo -n apt-get install -y containerd"
    ]

    results = bootstrap.execute_remote_plan(
        host="192.168.0.104",
        user="kforge",
        commands=commands
    )

    assert len(results) == 2
    assert results[0] == "[DRY-RUN] sudo -n apt-get update"
    assert results[1] == "[DRY-RUN] sudo -n apt-get install -y containerd"


def test_execute_remote_plan(monkeypatch):
    from kubeforge.providers import bootstrap

    calls = []

    def fake_ssh(host, user, command, port):
        calls.append(command)
        return f"Executed: {command}"

    monkeypatch.setattr(
        bootstrap,
        "run_ssh",
        fake_ssh
    )

    commands = [
        "sudo -n apt-get update",
        "sudo -n apt-get install -y containerd"
    ]

    results = bootstrap.execute_remote_plan(
        host="192.168.0.104",
        user="kforge",
        commands=commands,
        dry_run=False
    )

    assert calls == commands
    assert len(results) == 2
    assert results[0] == "Executed: sudo -n apt-get update"
    assert results[1] == "Executed: sudo -n apt-get install -y containerd"


def test_execute_remote_plan_stops_on_error(monkeypatch):
    import subprocess
    import pytest
    from kubeforge.providers import bootstrap

    calls = []

    def fake_ssh(host, user, command, port):
        calls.append(command)

        if "install" in command:
            raise subprocess.CalledProcessError(
                returncode=100,
                cmd=command
            )

        return "OK"

    monkeypatch.setattr(
        bootstrap,
        "run_ssh",
        fake_ssh
    )

    commands = [
        "sudo -n apt-get update",
        "sudo -n apt-get install -y containerd",
        "sudo -n systemctl restart containerd"
    ]

    with pytest.raises(subprocess.CalledProcessError):
        bootstrap.execute_remote_plan(
            host="192.168.0.104",
            user="kforge",
            commands=commands,
            dry_run=False
        )

    assert calls == commands[:2]


def test_kubeadm_install_plan():
    from kubeforge.providers.bootstrap import (
        build_kubeadm_install_plan,
        execute_remote_plan
    )

    commands = build_kubeadm_install_plan()

    assert len(commands) == 8
    assert "v1.37" in commands[3]
    assert commands[-1] == (
        "sudo -n apt-mark hold kubelet kubeadm kubectl"
    )

    results = execute_remote_plan(
        host="192.168.0.104",
        user="kforge",
        commands=commands,
        dry_run=True
    )

    assert len(results) == len(commands)
    assert all(
        result.startswith("[DRY-RUN]")
        for result in results
    )


def test_k8s_network_plan():
    from kubeforge.providers.bootstrap import (
        build_k8s_network_plan,
        execute_remote_plan
    )

    commands = build_k8s_network_plan()

    assert len(commands) == 5
    assert "modprobe overlay" in commands[0]
    assert "br_netfilter" in commands[1]
    assert "ip_forward = 1" in commands[3]

    results = execute_remote_plan(
        host="192.168.0.104",
        user="kforge",
        commands=commands,
        dry_run=True
    )

    assert len(results) == 5
    assert all(
        result.startswith("[DRY-RUN]")
        for result in results
    )


def test_k8s_swap_plan():
    from kubeforge.providers.bootstrap import (
        build_k8s_swap_plan,
        execute_remote_plan
    )

    commands = build_k8s_swap_plan()

    assert len(commands) == 4
    assert commands[0] == "sudo -n swapoff -a"
    assert "fstab.kubeforge.bak" in commands[1]
    assert "swap" in commands[2]
    assert commands[3] == "swapon --show"

    results = execute_remote_plan(
        host="192.168.0.104",
        user="kforge",
        commands=commands,
        dry_run=True
    )

    assert len(results) == 4
    assert all(
        result.startswith("[DRY-RUN]")
        for result in results
    )


def test_vps_bootstrap_plan():
    from kubeforge.providers.bootstrap import (
        build_vps_bootstrap_plan,
        build_k8s_swap_plan,
        build_k8s_network_plan,
        build_containerd_install_plan,
        build_kubeadm_install_plan
    )

    commands = build_vps_bootstrap_plan()

    expected = (
        build_k8s_swap_plan()
        + build_k8s_network_plan()
        + build_containerd_install_plan()
        + build_kubeadm_install_plan()
    )

    assert commands == expected
    assert len(commands) == 19


def test_containerd_cgroup(monkeypatch):
    from kubeforge.providers import bootstrap

    monkeypatch.setattr(
        bootstrap,
        "run_ssh",
        lambda **kwargs: "SystemdCgroup = true\n"
    )

    assert bootstrap.check_containerd_cgroup(
        "192.168.0.104",
        "kforge"
    ) is True


def test_enable_systemd_cgroup():
    from kubeforge.providers.bootstrap import enable_systemd_cgroup

    section = (
        "[plugins.'io.containerd.cri.v1.runtime'"
        ".containerd.runtimes.runc.options]"
    )

    for setting in [
        "  SystemdCgroup = false\n",
        ""
    ]:
        config = f"{section}\n{setting}"

        result = enable_systemd_cgroup(config)

        assert "SystemdCgroup = true" in result
        assert "SystemdCgroup = false" not in result

        repeated = enable_systemd_cgroup(result)
        assert repeated.count("SystemdCgroup = true") == 1


def test_validate_containerd_config():
    import pytest
    from kubeforge.providers.bootstrap import (
        validate_containerd_config
    )

    section = (
        "[plugins.'io.containerd.cri.v1.runtime'"
        ".containerd.runtimes.runc.options]"
    )

    valid_config = f"{section}\nSystemdCgroup = true\n"
    invalid_config = f"{section}\nSystemdCgroup = True\n"

    assert validate_containerd_config(valid_config) is True

    with pytest.raises(ValueError):
        validate_containerd_config(invalid_config)


def test_prepare_containerd_config():
    from kubeforge.providers.bootstrap import prepare_containerd_config

    config = """
[plugins.'io.containerd.cri.v1.runtime'.containerd.runtimes.runc.options]
SystemdCgroup = false
"""

    result = prepare_containerd_config(config)

    assert "SystemdCgroup = true" in result

    assert prepare_containerd_config(result) == result


def test_prepare_containerd_invalid_toml():
    import pytest
    from kubeforge.providers.bootstrap import prepare_containerd_config

    config = """
broken = ???
[plugins.'io.containerd.cri.v1.runtime'.containerd.runtimes.runc.options]
SystemdCgroup = false
"""

    with pytest.raises(ValueError):
        prepare_containerd_config(config)


def test_prepare_remote_containerd_config(monkeypatch):
    from kubeforge.providers import bootstrap

    original_config = """
[plugins.'io.containerd.cri.v1.runtime'.containerd.runtimes.runc.options]
SystemdCgroup = false
"""

    calls = []

    def fake_ssh(host, user, command, port):
        calls.append(command)
        return original_config

    monkeypatch.setattr(
        bootstrap,
        "run_ssh",
        fake_ssh
    )

    original, updated = (
        bootstrap.prepare_remote_containerd_config(
            host="192.168.0.104",
            user="kforge"
        )
    )

    assert original == original_config
    assert "SystemdCgroup = true" in updated
    assert "SystemdCgroup = false" in original

    assert calls == [
        "cat /etc/containerd/config.toml"
    ]


def test_containerd_backup_plan():
    from kubeforge.providers.bootstrap import (
        build_containerd_backup_plan,
        execute_remote_plan
    )

    commands = build_containerd_backup_plan()

    assert len(commands) == 2
    assert "test -f" in commands[0]
    assert "cp -p -n" in commands[1]
    assert "config.toml.kubeforge.bak" in commands[1]

    results = execute_remote_plan(
        host="192.168.0.104",
        user="kforge",
        commands=commands,
        dry_run=True
    )

    assert len(results) == 2
    assert all(
        result.startswith("[DRY-RUN]")
        for result in results
    )


def test_create_containerd_staging_file():
    from pathlib import Path
    from kubeforge.providers.bootstrap import (
        create_containerd_staging_file,
        validate_containerd_config
    )

    config = """
[plugins.'io.containerd.cri.v1.runtime'.containerd.runtimes.runc.options]
SystemdCgroup = false
"""

    temp_path = Path(create_containerd_staging_file(config))

    try:
        assert temp_path.exists()
        assert temp_path.suffix == ".toml"

        content = temp_path.read_text(encoding="utf-8")

        assert validate_containerd_config(content) is True
        assert "SystemdCgroup = true" in content

    finally:
        temp_path.unlink(missing_ok=True)


def test_upload_containerd_staging_dry_run(tmp_path, monkeypatch):
    from kubeforge.providers import bootstrap

    staging_file = tmp_path / "kubeforge-containerd-test.toml"
    staging_file.write_text("SystemdCgroup = true\n")

    def forbidden_run(*args, **kwargs):
        raise AssertionError("SCP must not execute in dry-run")

    monkeypatch.setattr(
        bootstrap.subprocess,
        "run",
        forbidden_run
    )

    result = bootstrap.upload_containerd_staging_file(
        host="192.168.0.104",
        user="kforge",
        local_path=str(staging_file)
    )

    assert result.startswith("[DRY-RUN]")
    assert "scp" in result
    assert "192.168.0.104" in result
    assert staging_file.name in result


def test_upload_containerd_staging_execution(tmp_path, monkeypatch):
    from kubeforge.providers import bootstrap

    staging_file = tmp_path / "kubeforge-containerd-test.toml"
    staging_file.write_text("SystemdCgroup = true\n")

    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))

    monkeypatch.setattr(
        bootstrap.subprocess,
        "run",
        fake_run
    )

    result = bootstrap.upload_containerd_staging_file(
        host="192.168.0.104",
        user="kforge",
        local_path=str(staging_file),
        port=2222,
        dry_run=False
    )

    assert len(calls) == 1

    command, options = calls[0]

    assert command[0] == "scp"
    assert command[command.index("-P") + 1] == "2222"
    assert command[-2] == str(staging_file)
    assert command[-1] == (
        "kforge@192.168.0.104:~/kubeforge-containerd-test.toml"
    )

    assert options["check"] is True
    assert "Uploaded to" in result


def test_upload_containerd_staging_failure(tmp_path, monkeypatch):
    import subprocess
    import pytest
    from kubeforge.providers import bootstrap

    staging_file = tmp_path / "containerd.toml"
    staging_file.write_text("SystemdCgroup = true\n")

    def fake_run(command, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=255,
            cmd=command,
            stderr="SSH connection failed"
        )

    monkeypatch.setattr(
        bootstrap.subprocess,
        "run",
        fake_run
    )

    with pytest.raises(subprocess.CalledProcessError) as error:
        bootstrap.upload_containerd_staging_file(
            host="192.168.0.104",
            user="kforge",
            local_path=str(staging_file),
            dry_run=False
        )

    assert error.value.returncode == 255
    assert "SSH connection failed" in error.value.stderr


@pytest.mark.parametrize(
    "ssh_output, expected",
    [
        ("VALID\n", True),
        ("INVALID\n", False),
    ]
)
def test_validate_remote_containerd_staging(
    monkeypatch, ssh_output, expected
):
    from kubeforge.providers import bootstrap

    calls = []

    def fake_ssh(host, user, command, port):
        calls.append(command)
        return ssh_output

    monkeypatch.setattr(
        bootstrap,
        "run_ssh",
        fake_ssh
    )

    result = bootstrap.validate_remote_containerd_staging(
        host="192.168.0.104",
        user="kforge",
        filename="kubeforge-containerd-test.toml"
    )

    assert result is expected
    assert len(calls) == 1
    assert "config dump" in calls[0]
    assert "systemctl restart" not in calls[0]


def test_containerd_rollback_plan(monkeypatch):
    from kubeforge.providers import bootstrap

    def forbidden_ssh(**kwargs):
        raise AssertionError("SSH must not execute")

    monkeypatch.setattr(
        bootstrap,
        "run_ssh",
        forbidden_ssh
    )

    commands = bootstrap.build_containerd_rollback_plan()

    assert len(commands) == 4
    assert "test -s" in commands[0]
    assert "cp -p" in commands[1]
    assert "systemctl restart containerd" in commands[2]
    assert "systemctl is-active" in commands[3]

    results = bootstrap.execute_remote_plan(
        host="192.168.0.104",
        user="kforge",
        commands=commands,
        dry_run=True
    )

    assert len(results) == 4
    assert all(
        result.startswith("[DRY-RUN]")
        for result in results
    )


def test_verify_containerd_backup_success(monkeypatch):
    from kubeforge.providers import bootstrap

    monkeypatch.setattr(
        bootstrap,
        "run_ssh",
        lambda **kwargs: "BACKUP_OK\n"
    )

    result = bootstrap.verify_containerd_backup(
        host="192.168.0.104",
        user="kforge"
    )

    assert result is True


def test_verify_containerd_backup_failure(monkeypatch):
    import subprocess
    import pytest
    from kubeforge.providers import bootstrap

    def fake_ssh(**kwargs):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=kwargs["command"]
        )

    monkeypatch.setattr(
        bootstrap,
        "run_ssh",
        fake_ssh
    )

    with pytest.raises(subprocess.CalledProcessError):
        bootstrap.verify_containerd_backup(
            host="192.168.0.104",
            user="kforge"
        )


def test_containerd_apply_plan():
    from kubeforge.providers.bootstrap import (
        build_containerd_apply_plan,
        execute_remote_plan
    )

    commands = build_containerd_apply_plan(
        "kubeforge-containerd-test.toml"
    )

    assert len(commands) == 7
    assert "config dump" in commands[0]
    assert "test -s" in commands[1]
    assert "cmp -s" in commands[2]
    assert "install -m 0644" in commands[3]
    assert "mv -f" in commands[4]
    assert "systemctl restart" in commands[5]

    results = execute_remote_plan(
        host="192.168.0.104",
        user="kforge",
        commands=commands,
        dry_run=True
    )

    assert len(results) == 7
    assert all(
        result.startswith("[DRY-RUN]")
        for result in results
    )


def test_containerd_apply_invalid_filename():
    import pytest
    from kubeforge.providers.bootstrap import build_containerd_apply_plan

    with pytest.raises(ValueError):
        build_containerd_apply_plan("../dangerous.toml")


def test_containerd_automatic_rollback(monkeypatch):
    import subprocess
    import pytest
    from kubeforge.providers import bootstrap

    calls = []
    restart_count = 0

    def fake_ssh(host, user, command, port):
        nonlocal restart_count

        calls.append(command)

        if command == "sudo -n systemctl restart containerd":
            restart_count += 1

            if restart_count == 1:
                raise subprocess.CalledProcessError(
                    returncode=1,
                    cmd=command
                )

        return "OK"

    monkeypatch.setattr(
        bootstrap,
        "run_ssh",
        fake_ssh
    )

    with pytest.raises(subprocess.CalledProcessError):
        bootstrap.apply_containerd_config_with_rollback(
            host="192.168.0.104",
            user="kforge",
            filename="kubeforge-containerd-test.toml",
            dry_run=False
        )

    assert restart_count == 2

    assert any(
        "cp -p" in command
        and "kubeforge.bak" in command
        for command in calls
    )


def test_containerd_failure_before_replacement(monkeypatch):
    import subprocess
    import pytest
    from kubeforge.providers import bootstrap

    calls = []

    def fake_ssh(host, user, command, port):
        calls.append(command)

        if "cmp -s" in command:
            raise subprocess.CalledProcessError(
                returncode=1,
                cmd=command
            )

        return "OK"

    monkeypatch.setattr(
        bootstrap,
        "run_ssh",
        fake_ssh
    )

    with pytest.raises(subprocess.CalledProcessError):
        bootstrap.apply_containerd_config_with_rollback(
            host="192.168.0.104",
            user="kforge",
            filename="kubeforge-containerd-test.toml",
            dry_run=False
        )

    assert not any("mv -f" in cmd for cmd in calls)

    assert not any("cp -p" in cmd for cmd in calls)

    assert not any("systemctl restart" in cmd for cmd in calls)


def test_containerd_rollback_failure(monkeypatch):
    import subprocess
    import pytest
    from kubeforge.providers import bootstrap

    calls = []

    def fake_ssh(host, user, command, port):
        calls.append(command)

        if command == "sudo -n systemctl restart containerd":
            raise subprocess.CalledProcessError(
                returncode=1,
                cmd=command
            )

        return "OK"

    monkeypatch.setattr(
        bootstrap,
        "run_ssh",
        fake_ssh
    )

    with pytest.raises(RuntimeError) as error:
        bootstrap.apply_containerd_config_with_rollback(
            host="192.168.0.104",
            user="kforge",
            filename="kubeforge-containerd-test.toml",
            dry_run=False
        )

    assert "Containerd update failed" in str(error.value)
    assert "Rollback also failed" in str(error.value)

    assert calls.count(
        "sudo -n systemctl restart containerd"
    ) == 2

    assert any(
        "cp -p" in command and "kubeforge.bak" in command
        for command in calls
    )


def test_containerd_apply_success(monkeypatch):
    from kubeforge.providers import bootstrap

    calls = []

    def fake_ssh(host, user, command, port):
        calls.append(command)
        return "OK"

    monkeypatch.setattr(
        bootstrap,
        "run_ssh",
        fake_ssh
    )

    filename = "kubeforge-containerd-test.toml"

    results = bootstrap.apply_containerd_config_with_rollback(
        host="192.168.0.104",
        user="kforge",
        filename=filename,
        dry_run=False
    )

    expected = bootstrap.build_containerd_apply_plan(filename)

    assert calls == expected
    assert len(results) == 7

    assert not any(
        "kubeforge.bak" in cmd and "cp -p" in cmd
        for cmd in calls
    )


def test_preview_containerd_update(tmp_path, monkeypatch):
    from kubeforge.providers import bootstrap

    monkeypatch.setattr(
        bootstrap.tempfile,
        "tempdir",
        str(tmp_path)
    )

    def forbidden_execution(*args, **kwargs):
        raise AssertionError("Remote execution is forbidden")

    monkeypatch.setattr(
        bootstrap,
        "run_ssh",
        forbidden_execution
    )

    monkeypatch.setattr(
        bootstrap.subprocess,
        "run",
        forbidden_execution
    )

    config = """
[plugins.'io.containerd.cri.v1.runtime'.containerd.runtimes.runc.options]
SystemdCgroup = false
"""

    results = bootstrap.preview_containerd_update(
        host="192.168.0.104",
        user="kforge",
        config_text=config
    )

    assert len(results) == 10
    assert all(
        result.startswith("[DRY-RUN]")
        for result in results
    )

    assert "scp" in results[2]
    assert "systemctl restart containerd" in results[-2]

    assert list(tmp_path.glob("kubeforge-containerd-*.toml")) == []
