import typer
import yaml
import subprocess
from kubeforge.core.manager import create_cluster
from kubeforge.core.manager import delete_cluster
from kubeforge.core.manager import get_cluster_status
from kubeforge.core.config import load_config
from pydantic import ValidationError
from kubeforge.core.doctor import run_doctor

app = typer.Typer()

@app.command()
def status(provider: str = "local", name: str = "kubeforge"):
    get_cluster_status(provider, name)

@app.command()
def up(provider: str | None = None, name: str | None = None):
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

    provider = provider or cluster["provider"]
    name = name or cluster["name"]
    workers = cluster["workers"]

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
def down(provider: str = "local", name: str = "kubeforge"):
    confirm = typer.confirm(
        f"Are you sure you want to delete cluster '{name}'?"
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

