from comum import *

seed([livro("T1", 0)])
pa = pedir(EMAIL_A, "T1").json()["pedido_id"]
time.sleep(1)  # garante criado_em diferente
pb = pedir(EMAIL_B, "T1").json()["pedido_id"]

assert chegada("T1", 1).status_code == 200
esperar(lambda: status_pedido(pa) == "RESERVADO", "A RESERVADO")
time.sleep(3)  # confirma que B continua esperando
assert status_pedido(pb) == "AGUARDANDO", "B deveria continuar AGUARDANDO"

assert chegada("T1", 1).status_code == 200
esperar(lambda: status_pedido(pb) == "RESERVADO", "B RESERVADO")
esperado_email(EMAIL_A + " (primeiro)", EMAIL_B + " (depois)")
print("OK")
