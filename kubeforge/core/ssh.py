import subprocess


def run_ssh(
    host: str,
    user: str,
    command: str,
    port: int = 22
):
    result = subprocess.run(
        [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=10",
            "-p", str(port),
            f"{user}@{host}",
            command
        ],
        capture_output=True,
        text=True,
        check=True
    )

    return result.stdout
