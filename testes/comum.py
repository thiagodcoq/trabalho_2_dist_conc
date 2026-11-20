"""Helpers dos cenários: seed, chamadas HTTP e polling dos passos assíncronos (Streams)."""
import json
import os
import sys
import time

import requests

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "clientes"))
from config import url  # noqa: E402

URL_PEDIDO = url("URL_PEDIDO")
URL_CHEGADA = url("URL_CHEGADA")
URL_CONSULTA = url("URL_CONSULTA")
URL_CARGA = url("URL_CARGA")

SEED = json.load(open(os.path.join(RAIZ, "dados", "seed.json"), encoding="utf-8"))
EMAIL_A = SEED["clientes"][0]["email"]
EMAIL_B = SEED["clientes"][1]["email"]
TIMEOUT_POLLING = 30


def seed(livros=None):
    """Reset + seed. 'livros' permite sobrescrever os livros do seed.json."""
    corpo = dict(SEED)
    if livros is not None:
        corpo["livros"] = livros
    r = requests.post(URL_CARGA, json=corpo, timeout=60)
    assert r.status_code == 200, f"seed falhou: {r.status_code} {r.text}"
    time.sleep(3)  # deixa os Streams do INSERT dos livros passarem


def livro(livro_id, quantidade):
    return {"livro_id": livro_id, "titulo": f"Livro {livro_id}", "autor": "Autor",
            "preco": 10, "quantidade": quantidade}


def pedir(email, livro_id):
    return requests.post(URL_PEDIDO, json={"email": email, "livro_id": livro_id}, timeout=30)


def chegada(livro_id, quantidade):
    return requests.post(URL_CHEGADA, json={"livro_id": livro_id, "quantidade": quantidade}, timeout=30)


def estoque(livro_id):
    r = requests.get(URL_CONSULTA, params={"tipo": "livros"}, timeout=30)
    for l in r.json()["livros"]:
        if l["livro_id"] == livro_id:
            return l["quantidade"]
    return None


def status_pedido(pedido_id):
    r = requests.get(URL_CONSULTA, params={"tipo": "pedido", "pedido_id": pedido_id}, timeout=30)
    return r.json()["pedido"]["status"] if r.status_code == 200 else None


def todos_pedidos():
    """Todos os pedidos de todos os clientes do seed, ordenados por criado_em."""
    out = []
    for c in SEED["clientes"]:
        r = requests.get(URL_CONSULTA, params={"tipo": "pedidos", "email": c["email"]}, timeout=30)
        out.extend(r.json()["pedidos"])
    return sorted(out, key=lambda p: p["criado_em"])


def esperar(condicao, descricao):
    """Polling até a condição ser verdadeira (timeout ~30 s)."""
    fim = time.time() + TIMEOUT_POLLING
    while time.time() < fim:
        if condicao():
            return
        time.sleep(1)
    raise AssertionError(f"timeout esperando: {descricao}")


def esperado_email(*destinos):
    for d in destinos:
        print(f"  >> E-mail esperado na caixa de entrada de: {d}")


def sem_email():
    print("  >> Nenhum e-mail deve ser enviado neste cenário")
