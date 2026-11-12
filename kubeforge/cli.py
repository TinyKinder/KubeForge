import typer
from kubeforge.core.manager import create_cluster
from kubeforge.core.manager import delete_cluster
from kubeforge.core.manager import get_cluster_status

app = typer.Typer()

@app.command()
def status(provider: str = "local", name: str = "kubeforge"):
    get_cluster_status(provider, name)

@app.command()
def up(provider: str = "local", name: str = "kubeforge"):
    create_cluster(provider, name)

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

