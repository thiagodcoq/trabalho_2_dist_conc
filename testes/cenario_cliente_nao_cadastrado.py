from comum import *

seed([livro("T1", 1)])
r = pedir("desconhecido@exemplo.com", "T1")
assert r.status_code == 404, f"esperado 404, veio {r.status_code}"
assert todos_pedidos() == [], "nenhum pedido deveria ter sido criado"
assert estoque("T1") == 1
sem_email()
print("OK")
