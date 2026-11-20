from comum import *

seed([livro("T1", 1)])
r = pedir(EMAIL_A, "NAO_EXISTE")
assert r.status_code == 404, f"esperado 404, veio {r.status_code}"
sem_email()
print("OK")
