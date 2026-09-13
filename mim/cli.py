import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import json
from pathlib import Path

console = Console()

@click.group(invoke_without_command=True)
@click.option('--version', is_flag=True, help='Show version')
@click.pass_context
def cli(ctx, version):
    """MIM - Music Intelligence Manager"""
    if version:
        console.print("[bold cyan]MIM[/bold cyan] v0.2.0")
        return
    if ctx.invoked_subcommand is None:
        console.print(Panel.fit(
            "[bold cyan]MIM - Music Intelligence Manager[/bold cyan]\n"
            "Sistema pessoal de música orientado a Library, Metadata, Discovery, Playback, IA, dispositivos e múltiplas fontes.\n\n"
            "Use [bold]mim --help[/bold] para ver comandos disponíveis.",
            title="🎵 MIM", border_style="cyan"
        ))


@cli.command()
@click.argument('query')
@click.option('--limit', '-l', default=20, help='Limite de resultados')
@click.option('--method', '-m', multiple=True, type=click.Choice(['title', 'artist', 'album', 'isrc', 'acoustic']),
              help='Métodos de busca')
def search(query, limit, method):
    """Busca músicas na biblioteca."""
    console.print(f"[cyan]Buscando:[/cyan] {query}")
    
    # Placeholder - conectar com DiscoveryService
    table = Table(title=f"Resultados para: {query}")
    table.add_column("Título", style="cyan")
    table.add_column("Artista", style="green")
    table.add_column("Álbum", style="yellow")
    table.add_column("Score", justify="right")
    
    # Mock results
    table.add_row("Bohemian Rhapsody", "Queen", "A Night at the Opera", "0.98")
    table.add_row("We Will Rock You", "Queen", "News of the World", "0.85")
    
    console.print(table)


@cli.command()
@click.argument('query')
@click.option('--queue/--play', default=False, help='Apenas adicionar à fila')
def play(query, queue):
    """Toca música (resolve automaticamente)."""
    action = "Adicionando à fila" if queue else "Tocando"
    console.print(f"[green]{action}:[/green] {query}")
    console.print("[dim]Resolvendo versão... → Verificando local... → Enfileirando...[/dim]")
    
    if not queue:
        console.print("🎵 [bold]Reproduzindo...[/bold]")


@cli.command()
def queue():
    """Mostra fila atual."""
    table = Table(title="Fila de Reprodução")
    table.add_column("#", justify="right")
    table.add_column("Título", style="cyan")
    table.add_column("Artista", style="green")
    table.add_column("Duração")
    
    # Mock queue
    table.add_row("1", "Bohemian Rhapsody", "Queen", "5:55")
    table.add_row("2", "We Will Rock You", "Queen", "2:02")
    table.add_row("3", "Don't Stop Me Now", "Queen", "3:30")
    
    console.print(table)


@cli.command()
@click.option('--limit', '-l', default=10, help='Número de eventos')
def history(limit):
    """Mostra histórico de reprodução."""
    console.print(f"[cyan]Histórico recente ({limit} eventos):[/cyan]")
    
    table = Table(title="Histórico de Reprodução")
    table.add_column("Quando", style="dim")
    table.add_column("Evento", style="cyan")
    table.add_column("Música", style="green")
    
    # Mock history
    table.add_row("2 min atrás", "▶ Play", "Bohemian Rhapsody - Queen")
    table.add_row("5 min atrás", "⏭ Skip", "We Will Rock You - Queen")
    table.add_row("10 min atrás", "▶ Play", "Don't Stop Me Now - Queen")
    
    console.print(table)


@cli.command()
def stats():
    """Mostra estatísticas de escuta."""
    console.print("[cyan]Estatísticas de Escuta:[/cyan]")
    
    stats_data = {
        "Total de músicas tocadas": "1,234",
        "Tempo total de escuta": "45h 32min",
        "Artistas únicos": "156",
        "Músicas completas": "1,098 (89%)",
        "Músicas puladas": "136 (11%)",
        "Modo repeat usado": "23%",
        "Modo shuffle usado": "67%",
    }
    
    for key, value in stats_data.items():
        console.print(f"  [bold]{key}:[/bold] {value}")


@cli.command()
@click.option('--for-user', '-u', default='default', help='Usuário para recomendações')
def recommend(for_user):
    """Mostra recomendações personalizadas."""
    console.print(f"[cyan]Recomendações para {for_user}:[/cyan]")
    
    table = Table(title="Recomendações")
    table.add_column("#", justify="right")
    table.add_column("Música", style="cyan")
    table.add_column("Artista", style="green")
    table.add_column("Confiança", justify="right")
    
    # Mock recommendations
    table.add_row("1", "Under Pressure", "Queen & David Bowie", "92%")
    table.add_row("2", "Radio Ga Ga", "Queen", "88%")
    table.add_row("3", "Another One Bites the Dust", "Queen", "85%")
    
    console.print(table)


@cli.command()
@click.argument('query')
def lyrics(query):
    """Busca letras de música."""
    console.print(f"[cyan]Buscando letra:[/cyan] {query}")
    
    panel = Panel(
        "[dim]Is this the real life?[/dim]\n"
        "[dim]Is this just fantasy?[/dim]\n"
        "[dim]Caught in a landslide...[/dim]",
        title="🎵 Bohemian Rhapsody - Queen",
        border_style="green"
    )
    console.print(panel)


@cli.command()
@click.option('--path', '-p', default='/home/miguel/Músicas', help='Diretório de música')
@click.option('--recursive/--no-recursive', default=True)
def scan(path, recursive):
    """Escaneia diretório de música."""
    console.print(f"[cyan]Escaneando:[/cyan] {path}")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Escaneando arquivos...", total=None)
        # Simulate scan
        import time
        time.sleep(1)
        progress.update(task, description="Encontrados 156 arquivos")
        time.sleep(0.5)
        progress.update(task, description="Reconciliando biblioteca...", completed=100)
    
    console.print("[green]✓ Escaneamento completo![/green]")
    console.print(f"  Arquivos encontrados: 156")
    console.print(f"  Novos: 3")
    console.print(f"  Removidos: 1")


@cli.command()
def serve():
    """Inicia servidor API (para integração web/mobile)."""
    console.print("[yellow]Iniciando servidor MIM API...[/yellow]")
    console.print("[dim]Disponível em http://localhost:8080[/dim]")
    console.print("[dim]Pressione Ctrl+C para parar[/dim]")
    
    # Placeholder - implementar FastAPI/uvicorn
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[red]Servidor parado.[/red]")


@cli.command()
def config():
    """Mostra configuração atual."""
    console.print("[cyan]Configuração MIM:[/cyan]")
    
    config_data = {
        "Diretório de música": "/home/miguel/Músicas",
        "Banco de dados": "library.db",
        "Limite de confiança": "0.7",
        "Modo repeat padrão": "OFF",
        "Modo shuffle padrão": "OFF",
        "Volume padrão": "80%",
        "Crossfade": "0ms",
    }
    
    for key, value in config_data.items():
        console.print(f"  [bold]{key}:[/bold] {value}")


if __name__ == '__main__':
    cli()