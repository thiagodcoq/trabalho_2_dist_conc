from comum import *

seed([livro("T1", 2)])
r = pedir(EMAIL_A, "T1")
assert r.status_code == 200, r.text
assert r.json()["status"] == "RESERVADO", r.text
assert estoque("T1") == 1, "estoque deveria ser 1"
esperado_email(EMAIL_A)
print("OK")
