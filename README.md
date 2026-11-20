# Sebo — livraria na AWS (Trabalho 2, Distribuição e Concorrência 2026/2)

Aplicação de livraria estilo sebo com 6 Lambdas, 3 tabelas DynamoDB (2 com Streams), SNS para e-mail e duas interfaces (CLI Python e página HTML+JS).

Tudo é criado **manualmente pelo console** do AWS Academy Learner Lab, região **us-east-1**, role **LabRole**.

## 1. Instalação (roteiro de console)

### 1.1 Iniciar o Learner Lab
Inicie o laboratório, abra o console AWS e confirme a região **us-east-1**.

### 1.2 DynamoDB
Crie as tabelas com capacidade **On-demand**:

| Tabela | Partition key |
|---|---|
| `sebo-livros` | `livro_id` (String) |
| `sebo-clientes` | `email` (String) |
| `sebo-pedidos` | `pedido_id` (String) |

Em `sebo-livros` e `sebo-pedidos`: *Exports and streams → DynamoDB stream details → Turn on → **New and old images***.

### 1.3 SNS
1. Crie o tópico **Standard** `sebo-avisos` e anote o ARN.
2. Para **cada e-mail de cliente** do `dados/seed.json`: *Create subscription*, protocolo **Email**, endpoint = o e-mail, e em *Subscription filter policy* (escopo **Message attributes**):
   ```json
   {"email": ["<o mesmo e-mail>"]}
   ```
3. Confirme cada inscrição pelo link recebido no e-mail (status deve ficar *Confirmed*).

> O enunciado supõe que o cliente já se inscreveu no tópico; este passo documenta como fazê-lo. A filter policy não foi vista em aula (ver RELATORIO.md).

### 1.4 Lambdas
Para cada pasta de `lambdas/`: *Create function → Author from scratch*, runtime **Python 3.12**, arquitetura **x86_64**, *Use an existing role* → **LabRole**. Cole o `lambda_function.py`, clique **Deploy** e configure as variáveis de ambiente (*Configuration → Environment variables*):

| Lambda | Variáveis |
|---|---|
| `sebo-pedido` | `TABELA_LIVROS`, `TABELA_CLIENTES`, `TABELA_PEDIDOS` |
| `sebo-chegada` | `TABELA_LIVROS` |
| `sebo-processa-espera` | `TABELA_LIVROS`, `TABELA_PEDIDOS` |
| `sebo-notifica` | `TABELA_LIVROS`, `TABELA_CLIENTES`, `SNS_TOPIC_ARN` |
| `sebo-consulta` | `TABELA_LIVROS`, `TABELA_PEDIDOS` |
| `sebo-carga` | `TABELA_LIVROS`, `TABELA_CLIENTES`, `TABELA_PEDIDOS` |

Valores: `TABELA_LIVROS=sebo-livros`, `TABELA_CLIENTES=sebo-clientes`, `TABELA_PEDIDOS=sebo-pedidos`, `SNS_TOPIC_ARN=<ARN do sebo-avisos>`.

Teste cada uma com o evento correspondente de `lambdas/eventos_teste/` (*Test → Create new event → colar o JSON*) e confira os `print` no CloudWatch Logs.

### 1.5 Function URLs
Em `sebo-pedido`, `sebo-chegada`, `sebo-consulta` e `sebo-carga`: *Configuration → Function URL → Create*, Auth **NONE**, habilite **CORS** (origin `*`, methods `GET, POST`, headers `content-type`). Copie as URLs.

### 1.6 Triggers (DynamoDB Streams)
- `sebo-processa-espera` ← tabela `sebo-livros` (batch size 1–10, starting position **Latest**).
- `sebo-notifica` ← tabela `sebo-pedidos` (batch size 1–10, starting position **Latest**).

### 1.7 Configurar e testar
```bash
cp .env.exemplo .env          # preencher as 4 URLs (sem barra final)
cp web/config.exemplo.js web/config.js   # preencher as 3 URLs
./seed.sh                     # carrega livros e clientes
./testes.sh                   # roda todos os cenários
```

## 2. Operação

**CLI** (a partir da raiz, com `source .env` e `pip install -r clientes/requirements.txt`):
```bash
cd clientes
python3 comprador_cli.py
python3 colaborador_cli.py
```

**Web:** `./web.sh` e abrir <http://localhost:8000>.

**Testes:** `./testes.sh` (todos) ou `./testes.sh <cenario>`. Cenários: `compra_disponivel`, `compra_indisponivel`, `compra_indisponivel_depois_chega`, `fila_fifo`, `chegada_maior_que_fila`, `ultimo_exemplar_concorrente`, `cliente_nao_cadastrado`, `livro_inexistente`, `entrada_invalida`. Cada um imprime quais e-mails devem chegar e a quem.

## 3. curl equivalentes
```bash
source .env
curl -s "$URL_CONSULTA?tipo=livros" | json_pp
curl -s "$URL_CONSULTA?tipo=pedidos&email=EMAIL" | json_pp
curl -s "$URL_CONSULTA?tipo=pedido&pedido_id=ID" | json_pp
curl -s -X POST "$URL_PEDIDO" -H 'Content-Type: application/json' \
  -d '{"email":"EMAIL","livro_id":"L001"}' | json_pp
curl -s -X POST "$URL_CHEGADA" -H 'Content-Type: application/json' \
  -d '{"livro_id":"L001","quantidade":1}' | json_pp
curl -s -X POST "$URL_CARGA" -H 'Content-Type: application/json' -d '{"acao":"reset"}' | json_pp
curl -s -X POST "$URL_CARGA" -H 'Content-Type: application/json' -d @dados/seed.json | json_pp
```

## 4. Troubleshooting
- **Logs:** CloudWatch Logs → grupo `/aws/lambda/<nome>`.
- **CORS duplicado:** se o navegador acusar `Access-Control-Allow-Origin` duplicado, deixe o CORS só na configuração da Function URL e retire os cabeçalhos CORS do código (ou vice-versa).
- **Nada acontece após pedido/chegada:** o Stream está sem trigger, ou o trigger está desabilitado, ou o Stream não está habilitado na tabela.
- **E-mail não chega:** inscrição em *Pending confirmation*, filter policy com e-mail diferente do usado no pedido (diferencia maiúsculas), ou `SNS_TOPIC_ARN` errado. Verifique também a caixa de spam.
- **Erro 500 na Lambda:** confira as variáveis de ambiente e a role `LabRole`.
- **Sessão do Learner Lab expirou:** os recursos podem ser mantidos, mas as URLs/ARNs devem ser conferidas ao reiniciar.

## 5. Limpeza
Após a nota: desative/apague as Function URLs (principalmente `sebo-carga`, que é pública e apaga dados), apague as Lambdas, as tabelas DynamoDB e o tópico SNS.
