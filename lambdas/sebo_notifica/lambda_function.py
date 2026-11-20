import os

import boto3

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")
tabela_livros = dynamodb.Table(os.environ["TABELA_LIVROS"])
tabela_clientes = dynamodb.Table(os.environ["TABELA_CLIENTES"])
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]


def virou_reservado(record):
    """True se o pedido passou a RESERVADO (INSERT já reservado, ou AGUARDANDO -> RESERVADO)."""
    tipo = record.get("eventName")
    novo = record.get("dynamodb", {}).get("NewImage")
    if not novo or novo.get("status", {}).get("S") != "RESERVADO":
        return False
    if tipo == "INSERT":
        return True
    if tipo == "MODIFY":
        antigo = record["dynamodb"].get("OldImage", {})
        return antigo.get("status", {}).get("S") == "AGUARDANDO"
    return False


def lambda_handler(event, context):
    print("Evento recebido:", event)
    for record in event.get("Records", []):
        if not virou_reservado(record):
            continue
        pedido = record["dynamodb"]["NewImage"]
        email = pedido["email"]["S"]
        livro_id = pedido["livro_id"]["S"]
        pedido_id = pedido["pedido_id"]["S"]

        livro = tabela_livros.get_item(Key={"livro_id": livro_id}).get("Item", {})
        cliente = tabela_clientes.get_item(Key={"email": email}).get("Item", {})
        titulo = livro.get("titulo", livro_id)
        nome = cliente.get("nome", email)

        mensagem = (f"Olá {nome}, o livro '{titulo}' está reservado para você. "
                    f"Compareça à livraria para efetivar a compra. Pedido {pedido_id}.")
        # MessageAttribute 'email' casa com a filter policy da inscrição do cliente
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="Sebo: seu livro está reservado",
            Message=mensagem,
            MessageAttributes={"email": {"DataType": "String", "StringValue": email}},
        )
        print(f"E-mail publicado para {email} (pedido {pedido_id})")
    return {"ok": True}
