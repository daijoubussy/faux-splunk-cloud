"""
Faux Splunk Cloud CLI.

Command-line interface for managing ephemeral Splunk Cloud Victoria instances.

Usage:
    faux-splunk create my-instance --topology standalone
    faux-splunk list
    faux-splunk start my-instance-id
    faux-splunk stop my-instance-id
    faux-splunk destroy my-instance-id
    faux-splunk serve  # Start the API server
"""

import asyncio
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from faux_splunk_cloud import __version__
from faux_splunk_cloud.config import settings
from faux_splunk_cloud.models.instance import (
    InstanceConfig,
    InstanceCreate,
    InstanceStatus,
    InstanceTopology,
)
from faux_splunk_cloud.services.instance_manager import instance_manager

app = typer.Typer(
    name="faux-splunk",
    help="Ephemeral Splunk Cloud Victoria instances for development and testing.",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"Faux Splunk Cloud v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = None,
):
    """Faux Splunk Cloud - Ephemeral Splunk instances for development."""
    pass


# =============================================================================
# Instance Management Commands
# =============================================================================


@app.command()
def create(
    name: Annotated[str, typer.Argument(help="Instance name (DNS-safe)")],
    topology: Annotated[
        InstanceTopology,
        typer.Option("--topology", "-t", help="Deployment topology"),
    ] = InstanceTopology.STANDALONE,
    ttl: Annotated[
        int,
        typer.Option("--ttl", help="Time-to-live in hours"),
    ] = 24,
    memory: Annotated[
        int,
        typer.Option("--memory", "-m", help="Memory per container in MB"),
    ] = 2048,
    cpu: Annotated[
        float,
        typer.Option("--cpu", "-c", help="CPU cores per container"),
    ] = 1.0,
    no_hec: Annotated[
        bool,
        typer.Option("--no-hec", help="Disable HTTP Event Collector"),
    ] = False,
    start: Annotated[
        bool,
        typer.Option("--start", "-s", help="Start the instance after creation"),
    ] = False,
    wait: Annotated[
        bool,
        typer.Option("--wait", "-w", help="Wait for instance to be ready (implies --start)"),
    ] = False,
    label: Annotated[
        Optional[list[str]],
        typer.Option("--label", "-l", help="Labels as key=value"),
    ] = None,
):
    """Create a new ephemeral Splunk instance."""
    # Parse labels
    labels = {}
    if label:
        for l in label:
            if "=" in l:
                k, v = l.split("=", 1)
                labels[k] = v

    config = InstanceConfig(
        topology=topology,
        memory_mb=memory,
        cpu_cores=cpu,
        enable_hec=not no_hec,
    )

    request = InstanceCreate(
        name=name,
        config=config,
        ttl_hours=ttl,
        labels=labels,
    )

    async def _create():
        await instance_manager.start()
        try:
            with console.status(f"Creating instance [bold]{name}[/bold]..."):
                instance = await instance_manager.create_instance(request)

            console.print(f"[green]✓[/green] Instance created: [bold]{instance.id}[/bold]")

            if wait or start:
                with console.status("Starting instance..."):
                    instance = await instance_manager.start_instance(instance.id)

            if wait:
                with console.status("Waiting for instance to be ready..."):
                    instance = await instance_manager.wait_for_ready(instance.id)
                console.print("[green]✓[/green] Instance is ready!")

            # Display instance details
            _print_instance_details(instance)

        finally:
            await instance_manager.stop()

    asyncio.run(_create())


@app.command("list")
def list_instances(
    status: Annotated[
        Optional[InstanceStatus],
        typer.Option("--status", "-s", help="Filter by status"),
    ] = None,
    label: Annotated[
        Optional[list[str]],
        typer.Option("--label", "-l", help="Filter by labels as key=value"),
    ] = None,
):
    """List all instances."""
    # Parse labels
    labels = {}
    if label:
        for l in label:
            if "=" in l:
                k, v = l.split("=", 1)
                labels[k] = v

    async def _list():
        await instance_manager.start()
        try:
            instances = await instance_manager.list_instances(
                status=status,
                labels=labels or None,
            )

            if not instances:
                console.print("No instances found.")
                return

            table = Table(title="Instances")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Status")
            table.add_column("Topology")
            table.add_column("Web URL")
            table.add_column("Expires")

            for instance in instances:
                status_color = {
                    InstanceStatus.RUNNING: "green",
                    InstanceStatus.STARTING: "yellow",
                    InstanceStatus.STOPPED: "red",
                    InstanceStatus.ERROR: "red bold",
                }.get(instance.status, "white")

                table.add_row(
                    instance.id,
                    instance.name,
                    f"[{status_color}]{instance.status.value}[/{status_color}]",
                    instance.config.topology.value,
                    instance.endpoints.web_url or "-",
                    instance.expires_at.strftime("%Y-%m-%d %H:%M") if instance.expires_at else "-",
                )

            console.print(table)

        finally:
            await instance_manager.stop()

    asyncio.run(_list())


@app.command()
def show(
    instance_id: Annotated[str, typer.Argument(help="Instance ID")],
):
    """Show details for a specific instance."""
    async def _show():
        await instance_manager.start()
        try:
            instance = await instance_manager.get_instance(instance_id)
            if not instance:
                console.print(f"[red]Instance {instance_id} not found[/red]")
                raise typer.Exit(1)

            _print_instance_details(instance)

        finally:
            await instance_manager.stop()

    asyncio.run(_show())


@app.command()
def start(
    instance_id: Annotated[str, typer.Argument(help="Instance ID")],
    wait: Annotated[
        bool,
        typer.Option("--wait", "-w", help="Wait for instance to be ready"),
    ] = False,
):
    """Start an instance."""
    async def _start():
        await instance_manager.start()
        try:
            with console.status(f"Starting instance [bold]{instance_id}[/bold]..."):
                instance = await instance_manager.start_instance(instance_id)

            console.print(f"[green]✓[/green] Instance starting: [bold]{instance.id}[/bold]")

            if wait:
                with console.status("Waiting for instance to be ready..."):
                    instance = await instance_manager.wait_for_ready(instance.id)
                console.print("[green]✓[/green] Instance is ready!")

            _print_instance_details(instance)

        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)
        finally:
            await instance_manager.stop()

    asyncio.run(_start())


@app.command()
def stop(
    instance_id: Annotated[str, typer.Argument(help="Instance ID")],
):
    """Stop an instance."""
    async def _stop():
        await instance_manager.start()
        try:
            with console.status(f"Stopping instance [bold]{instance_id}[/bold]..."):
                instance = await instance_manager.stop_instance(instance_id)

            console.print(f"[green]✓[/green] Instance stopped: [bold]{instance.id}[/bold]")

        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)
        finally:
            await instance_manager.stop()

    asyncio.run(_stop())


@app.command()
def destroy(
    instance_id: Annotated[str, typer.Argument(help="Instance ID")],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation"),
    ] = False,
):
    """Destroy an instance and all its resources."""
    if not force:
        confirm = typer.confirm(f"Are you sure you want to destroy instance {instance_id}?")
        if not confirm:
            raise typer.Exit()

    async def _destroy():
        await instance_manager.start()
        try:
            with console.status(f"Destroying instance [bold]{instance_id}[/bold]..."):
                await instance_manager.destroy_instance(instance_id)

            console.print(f"[green]✓[/green] Instance destroyed: [bold]{instance_id}[/bold]")

        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)
        finally:
            await instance_manager.stop()

    asyncio.run(_destroy())


@app.command()
def logs(
    instance_id: Annotated[str, typer.Argument(help="Instance ID")],
    container: Annotated[
        Optional[str],
        typer.Option("--container", "-c", help="Specific container name"),
    ] = None,
    tail: Annotated[
        int,
        typer.Option("--tail", "-n", help="Number of lines to show"),
    ] = 100,
):
    """Show logs from an instance's containers."""
    async def _logs():
        await instance_manager.start()
        try:
            logs = await instance_manager.get_instance_logs(instance_id, container, tail)
            console.print(logs)

        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)
        finally:
            await instance_manager.stop()

    asyncio.run(_logs())


@app.command()
def extend(
    instance_id: Annotated[str, typer.Argument(help="Instance ID")],
    hours: Annotated[
        int,
        typer.Argument(help="Hours to extend"),
    ],
):
    """Extend an instance's time-to-live."""
    async def _extend():
        await instance_manager.start()
        try:
            instance = await instance_manager.extend_ttl(instance_id, hours)
            console.print(
                f"[green]✓[/green] Extended TTL. New expiration: "
                f"[bold]{instance.expires_at.strftime('%Y-%m-%d %H:%M')}[/bold]"
            )

        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)
        finally:
            await instance_manager.stop()

    asyncio.run(_extend())


# =============================================================================
# Server Command
# =============================================================================


@app.command()
def serve(
    host: Annotated[
        str,
        typer.Option("--host", "-h", help="Host to bind to"),
    ] = settings.host,
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="Port to bind to"),
    ] = settings.port,
    reload: Annotated[
        bool,
        typer.Option("--reload", help="Enable auto-reload for development"),
    ] = False,
):
    """Start the Faux Splunk Cloud API server."""
    import uvicorn

    console.print(f"Starting Faux Splunk Cloud API server on [bold]{host}:{port}[/bold]")
    console.print(f"API docs: http://{host}:{port}/docs")

    uvicorn.run(
        "faux_splunk_cloud.api.app:app",
        host=host,
        port=port,
        reload=reload,
    )


# =============================================================================
# Infrastructure Commands
# =============================================================================


@app.command("infra")
def infrastructure(
    action: Annotated[
        str,
        typer.Argument(help="Action: up, down, status"),
    ],
):
    """Manage infrastructure services (Vault, Traefik, etc.)."""
    import subprocess
    from pathlib import Path

    infra_compose = Path(__file__).parent / "templates" / "docker-compose.infrastructure.yml"

    if action == "up":
        console.print("Starting infrastructure services...")
        subprocess.run(
            ["docker", "compose", "-f", str(infra_compose), "up", "-d"],
            check=True,
        )
        console.print("[green]✓[/green] Infrastructure services started")
        console.print("  Vault: http://localhost:8200")
        console.print("  Traefik Dashboard: http://localhost:8080")
        console.print("  Step CA: https://localhost:9000")
        console.print("  Registry: http://localhost:5000")

    elif action == "down":
        console.print("Stopping infrastructure services...")
        subprocess.run(
            ["docker", "compose", "-f", str(infra_compose), "down"],
            check=True,
        )
        console.print("[green]✓[/green] Infrastructure services stopped")

    elif action == "status":
        subprocess.run(
            ["docker", "compose", "-f", str(infra_compose), "ps"],
            check=True,
        )

    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("Valid actions: up, down, status")
        raise typer.Exit(1)


# =============================================================================
# Helper Functions
# =============================================================================


def _print_instance_details(instance):
    """Print formatted instance details."""
    console.print()
    console.print(f"[bold]Instance: {instance.id}[/bold]")
    console.print(f"  Name: {instance.name}")
    console.print(f"  Status: {instance.status.value}")
    console.print(f"  Topology: {instance.config.topology.value}")
    console.print(f"  Experience: {instance.config.experience}")
    console.print()

    if instance.endpoints.web_url:
        console.print("[bold]Endpoints:[/bold]")
        console.print(f"  Web UI: {instance.endpoints.web_url}")
        console.print(f"  REST API: {instance.endpoints.api_url}")
        if instance.endpoints.hec_url:
            console.print(f"  HEC: {instance.endpoints.hec_url}")
        if instance.endpoints.acs_url:
            console.print(f"  ACS API: {instance.endpoints.acs_url}")
        console.print()

    if instance.credentials:
        console.print("[bold]Credentials:[/bold]")
        console.print(f"  Username: {instance.credentials.admin_username}")
        console.print(f"  Password: {instance.credentials.admin_password}")
        if instance.credentials.hec_token:
            console.print(f"  HEC Token: {instance.credentials.hec_token}")
        console.print()

    console.print(f"[dim]Created: {instance.created_at.strftime('%Y-%m-%d %H:%M')}[/dim]")
    console.print(f"[dim]Expires: {instance.expires_at.strftime('%Y-%m-%d %H:%M')}[/dim]")


if __name__ == "__main__":
    app()
