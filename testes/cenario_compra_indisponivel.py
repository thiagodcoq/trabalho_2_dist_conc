from comum import *

seed([livro("T1", 0)])
r = pedir(EMAIL_A, "T1")
assert r.status_code == 200, r.text
assert r.json()["status"] == "AGUARDANDO", r.text
assert estoque("T1") == 0
sem_email()
print("OK")
