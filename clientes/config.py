import os
import sys


def url(nome):
    """Lê a URL da variável de ambiente (ex.: URL_PEDIDO) ou sai com erro claro."""
    v = os.environ.get(nome)
    if not v:
        sys.exit(f"Variável de ambiente {nome} não definida. Copie .env.exemplo para .env e rode: source .env")
    return v.rstrip("/")
