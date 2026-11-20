#!/bin/bash
# Envia dados/seed.json para a Lambda sebo-carga
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q -r clientes/requirements.txt
source .env
python3 -c "
import os, requests, sys
r = requests.post(os.environ['URL_CARGA'], data=open('dados/seed.json','rb').read(),
                  headers={'Content-Type': 'application/json'}, timeout=60)
print(r.status_code, r.text)
sys.exit(0 if r.status_code == 200 else 1)
"
