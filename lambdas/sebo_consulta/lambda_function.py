import json
import os
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource("dynamodb")
tabela_livros = dynamodb.Table(os.environ["TABELA_LIVROS"])
tabela_pedidos = dynamodb.Table(os.environ["TABELA_PEDIDOS"])

CORS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "content-type",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
}


def _num(o):
    if isinstance(o, Decimal):
        return int(o) if o == o.to_integral_value() else float(o)
    return str(o)


def resposta(codigo, corpo):
    return {"statusCode": codigo, "headers": CORS, "body": json.dumps(corpo, default=_num)}


def scan_completo(tabela, **kwargs):
    r = tabela.scan(**kwargs)
    itens = r["Items"]
    while "LastEvaluatedKey" in r:
        r = tabela.scan(ExclusiveStartKey=r["LastEvaluatedKey"], **kwargs)
        itens.extend(r["Items"])
    return itens


def lambda_handler(event, context):
    print("Evento recebido:", json.dumps(event, default=str))
    metodo = (event.get("requestContext", {}).get("http", {}).get("method")
              or event.get("httpMethod") or "GET")
    if metodo == "OPTIONS":
        return resposta(200, {})

    try:
        qs = event.get("queryStringParameters") or {}
        tipo = qs.get("tipo")

        if tipo == "livros":
            return resposta(200, {"livros": scan_completo(tabela_livros)})

        if tipo == "pedidos":
            email = qs.get("email")
            if not email:
                return resposta(400, {"erro": "parâmetro 'email' é obrigatório"})
            itens = scan_completo(tabela_pedidos, FilterExpression=Attr("email").eq(email))
            itens.sort(key=lambda p: p["criado_em"])
            return resposta(200, {"pedidos": itens})

        if tipo == "pedido":
            pedido_id = qs.get("pedido_id")
            if not pedido_id:
                return resposta(400, {"erro": "parâmetro 'pedido_id' é obrigatório"})
            item = tabela_pedidos.get_item(Key={"pedido_id": pedido_id}).get("Item")
            if not item:
                return resposta(404, {"erro": "pedido não encontrado"})
            return resposta(200, {"pedido": item})

        return resposta(400, {"erro": "parâmetro 'tipo' deve ser livros, pedidos ou pedido"})

    except Exception as e:
        print("Erro inesperado:", repr(e))
        return resposta(500, {"erro": "erro interno"})
