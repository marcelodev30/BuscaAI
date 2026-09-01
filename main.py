from litellm.exceptions import ServiceUnavailableError, RateLimitError, APIError
import argparse

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()

def main():
    parser = argparse.ArgumentParser(prog="buscaai")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_search = sub.add_parser("search", help="Busca no índice e responde")
    p_search.add_argument("pergunta")
    p_search.add_argument("-k", type=int, default=10, help="Nº de documentos")

    args = parser.parse_args()

    if args.comando == "search":
        with console.status("[bold cyan]Carregando..."):
            from rag import buscar, gerar

        with console.status("[bold cyan]Buscando no índice..."):
            docs = buscar(args.pergunta, k=args.k)

        console.print(f"[dim]{len(docs)} documentos encontrados[/dim]")
        
        try:
            with console.status("[bold cyan]Gerando resposta..."):
                resposta = gerar(args.pergunta, docs)

        except (ServiceUnavailableError) as e:
            console.print("[bold red]O modelo está sobrecarregado no momento.[/bold red]")
            console.print("[dim]Tente novamente em alguns instantes.[/dim]")
            raise SystemExit(1)

        console.print()
        console.print(f"[bold]❯[/bold] [italic]{args.pergunta}[/italic]\n")
        console.print(
            Panel(
                Markdown(resposta),
                border_style="cyan",
                padding=(1, 2),
            )
        )
        fontes = {d.metadata.get("filename", "?") for d in docs}
        console.print(f"\n[dim]Fontes: {', '.join(sorted(fontes))}[/dim]")


if __name__ == "__main__":
    main()