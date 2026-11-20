from comum import *

seed([livro("T1", 0)])
pid = pedir(EMAIL_A, "T1").json()["pedido_id"]
assert status_pedido(pid) == "AGUARDANDO"
assert chegada("T1", 1).status_code == 200
esperar(lambda: status_pedido(pid) == "RESERVADO", "pedido virar RESERVADO")
esperar(lambda: estoque("T1") == 0, "estoque voltar a 0")
esperado_email(EMAIL_A)
print("OK")
