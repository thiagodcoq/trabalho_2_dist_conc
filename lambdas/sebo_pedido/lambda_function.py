import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

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


def _num(o):
    # Decimal do DynamoDB -> int/float para o json.dumps
    if isinstance(o, Decimal):
        return int(o) if o == o.to_integral_value() else float(o)
    return str(o)


def resposta(codigo, corpo):
    return {"statusCode": codigo, "headers": CORS, "body": json.dumps(corpo, default=_num)}


def lambda_handler(event, context):
    print("Evento recebido:", json.dumps(event, default=str))
    metodo = (event.get("requestContext", {}).get("http", {}).get("method")
              or event.get("httpMethod") or "POST")
    if metodo == "OPTIONS":
        return resposta(200, {})

    try:
        body = json.loads(event.get("body") or "{}")
        email = body.get("email")
        livro_id = body.get("livro_id")
        if not email or not livro_id:
            return resposta(400, {"erro": "campos 'email' e 'livro_id' são obrigatórios"})

        # Cliente precisa estar cadastrado
        if "Item" not in tabela_clientes.get_item(Key={"email": email}):
            return resposta(404, {"erro": "cliente não cadastrado"})

        # Livro precisa existir
        if "Item" not in tabela_livros.get_item(Key={"livro_id": livro_id}):
            return resposta(404, {"erro": "livro não encontrado"})

        pedido_id = str(uuid.uuid4())
        agora = datetime.now(timezone.utc).isoformat()

        # Reserva atômica: só baixa o estoque se quantidade > 0
        # (evita a condição de corrida no último exemplar)
        try:
            tabela_livros.update_item(
                Key={"livro_id": livro_id},
                UpdateExpression="SET quantidade = quantidade - :um",
                ConditionExpression="quantidade > :zero",
                ExpressionAttributeValues={":um": 1, ":zero": 0},
            )
            reservado = True
        except ClientError as e:
            if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise
            reservado = False

        pedido = {
            "pedido_id": pedido_id,
            "email": email,
            "livro_id": livro_id,
            "status": "RESERVADO" if reservado else "AGUARDANDO",
            "criado_em": agora,
        }
        if reservado:
            pedido["reservado_em"] = agora
        tabela_pedidos.put_item(Item=pedido)

        if reservado:
            msg = "Livro reservado. Você receberá um e-mail para efetivar a compra na livraria."
        else:
            msg = "Livro indisponível. Você será avisado por e-mail quando ele chegar."
        print("Pedido criado:", pedido)
        return resposta(200, {"pedido_id": pedido_id, "status": pedido["status"], "mensagem": msg})

    except json.JSONDecodeError:
        return resposta(400, {"erro": "body não é um JSON válido"})
    except Exception as e:
        print("Erro inesperado:", repr(e))
        return resposta(500, {"erro": "erro interno"})
