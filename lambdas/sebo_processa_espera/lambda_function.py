import os
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
tabela_livros = dynamodb.Table(os.environ["TABELA_LIVROS"])
tabela_pedidos = dynamodb.Table(os.environ["TABELA_PEDIDOS"])


def pedidos_aguardando(livro_id):
    """Scan com filtro (com paginação), ordenado por criado_em (FIFO)."""
    filtro = Attr("livro_id").eq(livro_id) & Attr("status").eq("AGUARDANDO")
    r = tabela_pedidos.scan(FilterExpression=filtro)
    itens = r["Items"]
    while "LastEvaluatedKey" in r:
        r = tabela_pedidos.scan(FilterExpression=filtro, ExclusiveStartKey=r["LastEvaluatedKey"])
        itens.extend(r["Items"])
    return sorted(itens, key=lambda p: p["criado_em"])


def baixar_estoque(livro_id):
    """Mesma escrita condicional da sebo-pedido. False se não há estoque."""
    try:
        tabela_livros.update_item(
            Key={"livro_id": livro_id},
            UpdateExpression="SET quantidade = quantidade - :um",
            ConditionExpression="quantidade > :zero",
            ExpressionAttributeValues={":um": 1, ":zero": 0},
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise


def estoque_aumentou(record):
    """True se o record é um INSERT com qtd > 0 ou um MODIFY em que a qtd subiu."""
    tipo = record.get("eventName")
    novo = record.get("dynamodb", {}).get("NewImage")
    if tipo not in ("INSERT", "MODIFY") or not novo:
        return False
    nova_qtd = int(novo["quantidade"]["N"])
    if tipo == "INSERT":
        return nova_qtd > 0
    antiga = int(record["dynamodb"]["OldImage"]["quantidade"]["N"])
    return nova_qtd > antiga


def lambda_handler(event, context):
    print("Evento recebido:", event)
    try:
        for record in event.get("Records", []):
            if not estoque_aumentou(record):
                # diminuição (reservas) é ignorada, evita loop
                continue
            livro_id = record["dynamodb"]["NewImage"]["livro_id"]["S"]
            print("Estoque aumentou para", livro_id)

            for pedido in pedidos_aguardando(livro_id):  # FIFO
                if not baixar_estoque(livro_id):
                    print("Sem mais estoque; demais pedidos continuam AGUARDANDO")
                    break
                try:
                    tabela_pedidos.update_item(
                        Key={"pedido_id": pedido["pedido_id"]},
                        UpdateExpression="SET #s = :novo, reservado_em = :agora",
                        ConditionExpression="#s = :antigo",
                        ExpressionAttributeNames={"#s": "status"},
                        ExpressionAttributeValues={
                            ":novo": "RESERVADO",
                            ":antigo": "AGUARDANDO",
                            ":agora": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    print("Pedido reservado:", pedido["pedido_id"])
                except ClientError as e:
                    if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                        raise
                    # pedido já tratado por outra execução: devolve o exemplar baixado
                    tabela_livros.update_item(
                        Key={"livro_id": livro_id},
                        UpdateExpression="SET quantidade = quantidade + :um",
                        ExpressionAttributeValues={":um": 1},
                    )
                    print("Pedido já tratado, estoque devolvido:", pedido["pedido_id"])
    except Exception as e:
        print("Erro inesperado:", repr(e))
        raise  # o Stream refaz a tentativa
    return {"ok": True}
