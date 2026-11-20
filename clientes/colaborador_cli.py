import requests

from config import url

URL_CHEGADA = url("URL_CHEGADA")
URL_CONSULTA = url("URL_CONSULTA")


def listar_estoque():
    r = requests.get(URL_CONSULTA, params={"tipo": "livros"}, timeout=30)
    if r.status_code != 200:
        print("Erro:", r.status_code, r.text)
        return
    for l in r.json()["livros"]:
        print(f"{l['livro_id']}  {l['titulo']}  estoque: {l['quantidade']}")


def registrar_chegada():
    livro_id = input("ID do livro: ").strip()
    quantidade = int(input("Quantidade que chegou: "))
    r = requests.post(URL_CHEGADA, json={"livro_id": livro_id, "quantidade": quantidade}, timeout=30)
    if r.status_code == 200:
        d = r.json()
        print(f"Chegada registrada. Estoque de {d['livro_id']}: {d['quantidade']}")
    else:
        print("Erro:", r.status_code, r.json().get("erro", r.text))


def main():
    while True:
        print("\n1) Listar estoque  2) Registrar chegada  3) Sair")
        try:
            op = int(input("Opção: "))
            if op == 1:
                listar_estoque()
            elif op == 2:
                registrar_chegada()
            elif op == 3:
                break
            else:
                print("Opção inválida")
        except ValueError:
            print("Digite um número válido")
        except requests.RequestException as e:
            print("Falha de comunicação:", e)


if __name__ == "__main__":
    main()
