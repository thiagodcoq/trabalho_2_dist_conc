import json
import os
from decimal import Decimal

import boto3

dynamodb = boto3.resource("dynamodb")
tabela_livros = dynamodb.Table(os.environ["TABELA_LIVROS"])
tabela_clientes = dynamodb.Table(os.environ["TABELA_CLIENTES"])
tabela_pedidos = dynamodb.Table(os.environ["TABELA_PEDIDOS"])

CORS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "content-type",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}


def resposta(codigo, corpo):
    return {"statusCode": codigo, "headers": CORS, "body": json.dumps(corpo, default=str)}


def esvaziar(tabela, chave):
    """Apaga todos os itens da tabela (scan paginado + delete_item)."""
    total = 0
    r = tabela.scan(ProjectionExpression=chave)
    while True:
        for item in r["Items"]:
            tabela.delete_item(Key={chave: item[chave]})
            total += 1
        if "LastEvaluatedKey" not in r:
            return total
        r = tabela.scan(ProjectionExpression=chave, ExclusiveStartKey=r["LastEvaluatedKey"])


def lambda_handler(event, context):
    print("Evento recebido:", json.dumps(event, default=str))
    metodo = (event.get("requestContext", {}).get("http", {}).get("method")
              or event.get("httpMethod") or "POST")
    if metodo == "OPTIONS":
        return resposta(200, {})

    try:
        # parse_float=Decimal porque o DynamoDB não aceita float (preço)
        body = json.loads(event.get("body") or "{}", parse_float=Decimal)
        acao = body.get("acao")
        if acao not in ("reset", "seed"):
            return resposta(400, {"erro": "'acao' deve ser 'reset' ou 'seed'"})

        # 'reset' apaga só os pedidos; 'seed' apaga tudo e recarrega livros e clientes
        apagados = {"pedidos": esvaziar(tabela_pedidos, "pedido_id")}
        if acao == "seed":
            apagados["livros"] = esvaziar(tabela_livros, "livro_id")
            apagados["clientes"] = esvaziar(tabela_clientes, "email")
        carregados = {"livros": 0, "clientes": 0}
        if acao == "seed":
            livros = body.get("livros")
            clientes = body.get("clientes")
            if not isinstance(livros, list) or not isinstance(clientes, list):
                return resposta(400, {"erro": "'livros' e 'clientes' devem ser listas"})
            for livro in livros:
                tabela_livros.put_item(Item=livro)
                carregados["livros"] += 1
            for cliente in clientes:
                tabela_clientes.put_item(Item=cliente)
                carregados["clientes"] += 1

        print("Carga concluída:", apagados, carregados)
        return resposta(200, {"acao": acao, "apagados": apagados, "carregados": carregados})

    except json.JSONDecodeError:
        return resposta(400, {"erro": "body não é um JSON válido"})
    except Exception as e:
        print("Erro inesperado:", repr(e))
        return resposta(500, {"erro": "erro interno"})
