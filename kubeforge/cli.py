import typer
from kubeforge.core.manager import create_cluster
from kubeforge.core.manager import delete_cluster
from kubeforge.core.manager import get_cluster_status
from kubeforge.core.config import load_config

app = typer.Typer()

@app.command()
def status(provider: str = "local", name: str = "kubeforge"):
    get_cluster_status(provider, name)

@app.command()
def up(provider: str | None = None, name: str | None = None):
    config = load_config()

    cluster = config["cluster"]

    provider = provider or cluster["provider"]
    name = name or cluster["name"]
    workers = cluster["workers"]

    create_cluster(provider, name, workers)

@app.command()
def down(provider: str = "local", name: str = "kubeforge"):
    confirm = typer.confirm(
        f"Are you sure you want to delete cluster '{name}'?"
    )

    if confirm:
        delete_cluster(provider, name)
    else:
        typer.echo("Operation cancelled.")

if __name__ == "__main__":
    app()

