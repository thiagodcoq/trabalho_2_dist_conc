import json
import os
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
tabela_livros = dynamodb.Table(os.environ["TABELA_LIVROS"])

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


def lambda_handler(event, context):
    print("Evento recebido:", json.dumps(event, default=str))
    metodo = (event.get("requestContext", {}).get("http", {}).get("method")
              or event.get("httpMethod") or "POST")
    if metodo == "OPTIONS":
        return resposta(200, {})

    try:
        body = json.loads(event.get("body") or "{}")
        livro_id = body.get("livro_id")
        quantidade = body.get("quantidade")
        # bool é subclasse de int em Python, então excluímos explicitamente
        if (not livro_id or not isinstance(quantidade, int)
                or isinstance(quantidade, bool) or quantidade <= 0):
            return resposta(400, {"erro": "'livro_id' e 'quantidade' (inteiro > 0) são obrigatórios"})

        # Soma a quantidade; só se o livro existir (senão 404)
        try:
            r = tabela_livros.update_item(
                Key={"livro_id": livro_id},
                UpdateExpression="SET quantidade = quantidade + :q",
                ConditionExpression="attribute_exists(livro_id)",
                ExpressionAttributeValues={":q": quantidade},
                ReturnValues="UPDATED_NEW",
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return resposta(404, {"erro": "livro não encontrado"})
            raise

        nova = r["Attributes"]["quantidade"]
        print(f"Chegada registrada: {livro_id} +{quantidade} -> {nova}")
        return resposta(200, {"livro_id": livro_id, "quantidade": nova})

    except json.JSONDecodeError:
        return resposta(400, {"erro": "body não é um JSON válido"})
    except Exception as e:
        print("Erro inesperado:", repr(e))
        return resposta(500, {"erro": "erro interno"})
