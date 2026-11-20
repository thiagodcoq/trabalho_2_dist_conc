import requests

from config import url

URL_PEDIDO = url("URL_PEDIDO")
URL_CONSULTA = url("URL_CONSULTA")


def listar_livros():
    r = requests.get(URL_CONSULTA, params={"tipo": "livros"}, timeout=30)
    if r.status_code != 200:
        print("Erro:", r.status_code, r.text)
        return
    for l in r.json()["livros"]:
        print(f"{l['livro_id']}  {l['titulo']} - {l['autor']}  R$ {l['preco']}  (estoque: {l['quantidade']})")


def pedir_livro():
    email = input("Seu e-mail: ").strip()
    livro_id = input("ID do livro: ").strip()
    r = requests.post(URL_PEDIDO, json={"email": email, "livro_id": livro_id}, timeout=30)
    if r.status_code == 200:
        d = r.json()
        print(f"Pedido {d['pedido_id']} [{d['status']}]: {d['mensagem']}")
    else:
        print("Erro:", r.status_code, r.json().get("erro", r.text))


def meus_pedidos():
    email = input("Seu e-mail: ").strip()
    r = requests.get(URL_CONSULTA, params={"tipo": "pedidos", "email": email}, timeout=30)
    if r.status_code != 200:
        print("Erro:", r.status_code, r.text)
        return
    for p in r.json()["pedidos"]:
        print(f"{p['pedido_id']}  livro {p['livro_id']}  {p['status']}  ({p['criado_em']})")


def main():
    while True:
        print("\n1) Listar livros  2) Pedir livro  3) Ver meus pedidos  4) Sair")
        try:
            op = int(input("Opção: "))
            if op == 1:
                listar_livros()
            elif op == 2:
                pedir_livro()
            elif op == 3:
                meus_pedidos()
            elif op == 4:
                break
            else:
                print("Opção inválida")
        except ValueError:
            print("Digite um número válido")
        except requests.RequestException as e:
            print("Falha de comunicação:", e)


if __name__ == "__main__":
    main()
