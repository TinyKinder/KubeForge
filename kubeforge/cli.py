import typer
from kubeforge.core.manager import create_cluster
from kubeforge.providers.local import get_local_cluster_status
from kubeforge.core.manager import delete_cluster

app = typer.Typer()

@app.command()
def status():
    get_local_cluster_status()

@app.command()
def up(provider: str = "local"):
    create_cluster(provider)

@app.command()
def down(provider: str = "local"):
    confirm = typer.confirm("Are you sure you want to delete the cluster?")

    if confirm:
        delete_cluster(provider)
    else:
        typer.echo("Operation cancelled.")


if __name__ == "__main__":
    app()

