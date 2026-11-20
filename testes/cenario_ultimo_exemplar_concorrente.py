import threading

from comum import *

seed([livro("T1", 1)])
respostas = []


def pede(email):
    respostas.append(pedir(email, "T1"))


# Duas threads pedem o último exemplar ao mesmo tempo
ts = [threading.Thread(target=pede, args=(e,)) for e in (EMAIL_A, EMAIL_B)]
for t in ts:
    t.start()
for t in ts:
    t.join()

assert all(r.status_code == 200 for r in respostas), [r.text for r in respostas]
status = sorted(r.json()["status"] for r in respostas)
assert status == ["AGUARDANDO", "RESERVADO"], status
assert estoque("T1") == 0
print("  >> Um dos clientes (o que reservou) deve receber e-mail; o outro não")
print("OK")
