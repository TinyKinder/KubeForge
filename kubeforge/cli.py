import typer
import yaml
import subprocess
from kubeforge.providers.vps import is_vps_cluster_initialized
from kubeforge.providers.vps import run_vps_preflight
from kubeforge.core.manager import create_cluster
from kubeforge.core.manager import delete_cluster
from kubeforge.core.manager import get_cluster_status
from kubeforge.core.config import load_config
from pydantic import ValidationError
from kubeforge.core.doctor import run_doctor

app = typer.Typer()

def resolve_cluster_config(provider: str | None, name: str | None):
    try:
        config = load_config()

    except ValidationError as error:
        typer.secho(
            "Error: Invalid KubeForge configuration",
            fg=typer.colors.RED
        )

        for issue in error.errors():
            field = ".".join(str(part) for part in issue["loc"])
            typer.echo(f"{field}: {issue['msg']}")

        raise typer.Exit(code=1) from None

    except (ValueError, OSError, yaml.YAMLError) as error:
        typer.secho(f"Configuration error: {error}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from None

    cluster = config["cluster"]

    return (
        provider if provider is not None else cluster["provider"],
        name if name is not None else cluster["name"],
        cluster["workers"]
    )

@app.command()
def status(provider: str | None = None, name: str | None = None):
    provider, name, _ = resolve_cluster_config(provider, name)

    if provider == "vps":
        try:
            config = load_config()

            if "vps" not in config:
                raise ValueError("Missing VPS configuration")

            result = get_cluster_status(
                provider,
                name,
                config["vps"]
            )

            typer.echo(result)

        except (ValueError, OSError, subprocess.CalledProcessError) as error:
            typer.secho(f"Error: {error}", fg=typer.colors.RED)
            raise typer.Exit(code=1) from None

        return

    get_cluster_status(provider, name)


@app.command()
def up(provider: str | None = None, name: str | None = None):
    provider, name, workers = resolve_cluster_config(provider, name)

    if provider == "vps":
        try:
            config = load_config()

            if "vps" not in config:
                raise ValueError("Missing VPS configuration")

            results = run_vps_preflight(config["vps"])

            has_errors = False

            for host, result in results.items():
                typer.echo(f"\n{result['role']} — {host}")
                typer.echo(f"Resources: {result['resources']}")

                if result["errors"]:
                    has_errors = True
                    for error in result["errors"]:
                        typer.secho(
                            f"[FAIL] {error}",
                            fg=typer.colors.RED
                        )
                else:
                    typer.secho(
                        "[OK] Preflight passed",
                        fg=typer.colors.GREEN
                    )

            if has_errors:
                raise typer.Exit(code=1)

            typer.echo("\nVPS preflight completed.")

            control_plane = config["vps"]["control_plane"]

            initialized = is_vps_cluster_initialized(
                host=control_plane["host"],
                user=control_plane["user"],
                port=control_plane["port"]
            )

            if initialized:
                typer.secho(
                    "Kubernetes is already initialized. Deployment skipped.",
                    fg=typer.colors.YELLOW
                )
                return

            typer.echo("Deployment not implemented yet.")
            return

        except (ValueError, OSError, subprocess.CalledProcessError) as error:
            typer.secho(
                f"Error: {error}",
                fg=typer.colors.RED
            )
            raise typer.Exit(code=1) from None

    try:
        create_cluster(provider, name, workers)

    except RuntimeError as error:
        typer.secho(
            f"Error: {error}",
            fg=typer.colors.RED
        )
        raise typer.Exit(code=1) from None

    except subprocess.CalledProcessError as error:
        typer.secho(
            f"Error: Command failed with exit code {error.returncode}",
            fg=typer.colors.RED
        )
        raise typer.Exit(code=1) from None

    except FileNotFoundError as error:
        typer.secho(
            f"Error: Required executable not found: {error.filename}",
            fg=typer.colors.RED
        )
        raise typer.Exit(code=1) from None


@app.command()
def down(provider: str | None = None, name: str | None = None):
    provider, name, _ = resolve_cluster_config(provider, name)

    confirm = typer.confirm(
        f"Are you sure you want to delete cluster '{name}' "
        f"using provider '{provider}'?"
    )

    if confirm:
        delete_cluster(provider, name)
    else:
        typer.echo("Operation cancelled.")


@app.command()
def doctor():
    if not run_doctor():
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()

