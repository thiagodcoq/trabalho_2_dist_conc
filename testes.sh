#!/bin/bash
# ./testes.sh              -> roda todos os cenários
# ./testes.sh <cenario>    -> roda um (ex.: compra_disponivel)
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q -r clientes/requirements.txt
source .env

if [ -n "$1" ]; then
  CENARIOS=("$1")
else
  CENARIOS=($(ls testes/cenario_*.py | sed 's#testes/cenario_##; s#\.py##'))
fi

ok=0; falhou=0
for c in "${CENARIOS[@]}"; do
  echo "=== $c ==="
  if (cd testes && python3 "cenario_$c.py"); then
    echo "--> OK: $c"; ok=$((ok+1))
  else
    echo "--> FALHOU: $c"; falhou=$((falhou+1))
  fi
done
echo; echo "Resumo: $ok OK, $falhou FALHOU"
[ "$falhou" -eq 0 ]
