from comum import *

seed([livro("T1", 1)])
r = requests.post(URL_PEDIDO, json={}, timeout=30)
assert r.status_code == 400, f"pedido sem campos: {r.status_code}"
r = requests.post(URL_CHEGADA, json={}, timeout=30)
assert r.status_code == 400, f"chegada sem campos: {r.status_code}"
for q in (0, -1):
    r = chegada("T1", q)
    assert r.status_code == 400, f"chegada qtd {q}: {r.status_code}"
assert estoque("T1") == 1
print("OK")
