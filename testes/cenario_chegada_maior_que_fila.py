from comum import *

seed([livro("T1", 0)])
pid = pedir(EMAIL_A, "T1").json()["pedido_id"]
assert chegada("T1", 3).status_code == 200
esperar(lambda: status_pedido(pid) == "RESERVADO", "pedido RESERVADO")
esperar(lambda: estoque("T1") == 2, "estoque final 2")
esperado_email(EMAIL_A)
print("OK")
