# Relatório — Trabalho 2: Livraria "Sebo" na AWS

## 1. Identificação

- **Disciplina:** Distribuição e Concorrência (2026.2)
- **Integrantes:** Felipe Peixoto, Guilherme Gratz e Thiago Coqueiro
- **Conta AWS Academy com a implementação:** thiagodamicoc@gmail.com

## 2. Visão geral e decisões de projeto

O comprador informa o livro desejado. Havendo estoque, o livro é **reservado** e o cliente recebe e-mail para efetivar a compra na livraria. Não havendo, o pedido fica `AGUARDANDO` e o cliente é avisado por e-mail quando o livro chega. Estoque, clientes e pedidos ficam no DynamoDB.

| Tema | Decisão | Justificativa |
|---|---|---|
| Linguagem | Python 3.12 | Padrão das aulas |
| Nuvem | Learner Lab, `us-east-1`, `LabRole` | Restrição do ambiente |
| Banco | DynamoDB + Streams (`NEW_AND_OLD_IMAGES`) | Mesmo padrão do lab Inventory / Check-Stock |
| E-mail | SNS, tópico único `sebo-avisos`, filter policy `{"email": [...]}` por inscrição | Um tópico atende todos os clientes; cada um só recebe o seu |
| HTTP | Lambda Function URL, Auth NONE, CORS | Padrão dos slides |
| Pedido disponível | Reserva: baixa estoque e pedido `RESERVADO` | Evita vender o mesmo exemplar duas vezes |
| Fila de espera | FIFO por `criado_em` | Justiça com os clientes mais antigos |
| Clientes | Tabela `sebo-clientes` pré-carregada; e-mail desconhecido é recusado | Conforme enunciado (cliente já inscrito) |
| UI colaborador | Mínima: chegada de livros e listar estoque | Cenários cobertos por scripts |
| Interfaces | CLI Python + página HTML+JS | Estilo do frontend do somador e do `start.sh` |
| Testes | Cenários Python contra as Function URLs reais + `testes.sh` | Prova o comportamento ponta a ponta |
| Infraestrutura | Console, com roteiro no README | Como nos slides |


## 3. Diagrama de blocos

```mermaid
flowchart LR
    CP[CLI/HTML Comprador] -->|POST| P(λ sebo-pedido)
    CC[CLI/HTML Colaborador] -->|POST| CH(λ sebo-chegada)
    CT[CLI / HTML / testes] -->|GET| CO(λ sebo-consulta)
    SD[seed / testes] -->|POST| CA(λ sebo-carga)

    P --> CLI[(sebo-clientes)]
    P --> LIV[(sebo-livros)]
    P --> PED[(sebo-pedidos)]
    CH -->|qtd +| LIV
    CO --> LIV
    CO --> PED
    CA --> CLI
    CA --> LIV
    CA --> PED

    LIV -->|Stream: qtd aumentou| PE(λ sebo-processa-espera)
    PE -->|FIFO: reserva AGUARDANDO| PED
    PE -->|baixa estoque| LIV
    PED -->|Stream: virou RESERVADO| N(λ sebo-notifica)
    N -->|publish c/ atributo email| SNS{{SNS sebo-avisos}}
    SNS -->|filter policy| EM[E-mail do cliente]
```

## 4. Diagramas UML de sequência

### (a) Compra com livro disponível

```mermaid
sequenceDiagram
    actor C as Comprador
    participant P as λ sebo-pedido
    participant L as sebo-livros
    participant PD as sebo-pedidos
    participant N as λ sebo-notifica
    participant S as SNS sebo-avisos
    C->>P: POST {email, livro_id}
    P->>L: update qtd-1 (condição qtd>0)
    L-->>P: ok
    P->>PD: put_item status=RESERVADO
    P-->>C: 200 {pedido_id, RESERVADO}
    PD-)N: Stream (INSERT RESERVADO)
    N->>L: get_item (título)
    N->>S: publish (MessageAttributes email)
    S-->>C: e-mail (via filter policy)
```

### (b) Compra indisponível → chegada → notificação

```mermaid
sequenceDiagram
    actor C as Comprador
    actor K as Colaborador
    participant P as λ sebo-pedido
    participant CH as λ sebo-chegada
    participant L as sebo-livros
    participant PD as sebo-pedidos
    participant PE as λ sebo-processa-espera
    participant N as λ sebo-notifica
    participant S as SNS sebo-avisos
    C->>P: POST {email, livro_id}
    P->>L: update qtd-1 (condição qtd>0)
    L-->>P: ConditionalCheckFailed
    P->>PD: put_item status=AGUARDANDO
    P-->>C: 200 {AGUARDANDO}
    K->>CH: POST {livro_id, quantidade}
    CH->>L: update qtd+q
    L-)PE: Stream (MODIFY, qtd aumentou)
    PE->>PD: scan AGUARDANDO (FIFO)
    PE->>L: update qtd-1 (condição qtd>0)
    PE->>PD: update status=RESERVADO
    PD-)N: Stream (AGUARDANDO→RESERVADO)
    N->>S: publish (MessageAttributes email)
    S-->>C: e-mail (via filter policy)
```

## 5. Modelo de dados

| Tabela | Partition key | Atributos | Stream |
|---|---|---|---|
| `sebo-livros` | `livro_id` (S) | `titulo`, `autor`, `preco` (N), `quantidade` (N) | Sim |
| `sebo-clientes` | `email` (S) | `nome` | Não |
| `sebo-pedidos` | `pedido_id` (S, uuid4) | `email`, `livro_id`, `status` (`AGUARDANDO`/`RESERVADO`), `criado_em`, `reservado_em` | Sim |

Todas em capacidade On-demand.

## 6. Descrição das Lambdas

| Lambda | Gatilho | Responsabilidade |
|---|---|---|
| `sebo-pedido` | Function URL POST | Valida entrada (400), cliente e livro (404); reserva com `update_item` condicional; grava pedido `RESERVADO` ou `AGUARDANDO`. Não envia e-mail |
| `sebo-chegada` | Function URL POST | Soma a quantidade recebida ao estoque (404 se livro inexistente, 400 se qtd ≤ 0) |
| `sebo-processa-espera` | Stream `sebo-livros` | Quando o estoque aumenta, atende pedidos `AGUARDANDO` em FIFO enquanto houver estoque |
| `sebo-notifica` | Stream `sebo-pedidos` | Quando um pedido vira `RESERVADO`, publica no SNS com o atributo `email` |
| `sebo-consulta` | Function URL GET | Lista livros, pedidos de um e-mail ou um pedido |
| `sebo-carga` | Function URL POST | `reset` (apaga pedidos) e `seed` (recarrega livros e clientes); usada por seed e testes |

## 7. Instalação e operação

Roteiro completo de console, operação (CLI e web), `curl` e troubleshooting no [README.md](README.md).

## 8. Testes realizados

Executados com `./testes.sh` contra as Function URLs reais, no Learner Lab (us-east-1), em 20/11/2026. Resumo da execução: **9 OK, 0 FALHOU**. As asserções de cada cenário (status HTTP, status do pedido e quantidade em estoque) passaram. A chegada dos e-mails foi conferida manualmente na caixa de entrada.

| # | Cenário | Esperado | Resultado |
|---|---|---|---|
| 1 | `compra_disponivel` | Pedido `RESERVADO`, qtd 2→1, e-mail ao cliente A | OK. E-mail recebido pelo cliente A |
| 2 | `compra_indisponivel` | Pedido `AGUARDANDO`, sem e-mail | OK. Asserções passaram |
| 3 | `compra_indisponivel_depois_chega` | Chegada +1 → `RESERVADO`, qtd 0, e-mail ao A | OK. E-mail recebido pelo cliente A |
| 4 | `fila_fifo` | A reservado primeiro, B depois; dois e-mails em ordem | OK nas asserções (ordem FIFO dos status). E-mail do A recebido; recebimento do B e ordem das mensagens não conferidos |
| 5 | `chegada_maior_que_fila` | 1 esperando, chegam 3 → 1 reservado, qtd final 2 | OK. Asserções passaram |
| 6 | `ultimo_exemplar_concorrente` | 2 threads, qtd 1 → 1 `RESERVADO` e 1 `AGUARDANDO`, qtd 0 | OK. A escrita condicional impediu a venda dupla do último exemplar |
| 7 | `cliente_nao_cadastrado` | 404, nenhum pedido criado | OK |
| 8 | `livro_inexistente` | 404 | OK |
| 9 | `entrada_invalida` | 400 | OK |

Além dos cenários automatizados, o fluxo foi repetido manualmente pela página web: pedido do livro L002 (sem estoque) → `AGUARDANDO`; chegada de 1 exemplar pelo bloco Colaborador → pedido passou a `RESERVADO` e o e-mail chegou ao cliente.

## 9. O que funcionou / o que não funcionou

| Item | Funcionou? | Observações |
|---|---|---|
| Criação das tabelas e Streams | Sim | 3 tabelas On-demand; Streams `NEW_AND_OLD_IMAGES` ativos em `sebo-livros` e `sebo-pedidos` |
| Inscrições SNS com filter policy | Parcial | As 4 inscrições foram criadas com a filter policy. Duas ficaram `Confirmado` e duas ficaram em `Confirmação pendente` (dependem de o dono do e-mail clicar no link). O e-mail do cliente A chegou à sua caixa. Não foi verificado que o cliente B **não** recebe o e-mail do A |
| Lambdas | Sim | As 6 Lambdas foram criadas (Python 3.12, `LabRole`), com código por upload de `.zip` e variáveis de ambiente. Os eventos de `lambdas/eventos_teste/` **não** foram executados no console; a validação foi feita pelos cenários e pela página web |
| Triggers de Stream | Sim | `sebo-processa-espera` ← `sebo-livros` e `sebo-notifica` ← `sebo-pedidos` (lote 10, posição inicial Latest), ambos habilitados |
| Function URLs / CORS | Sim, com ajuste | Com CORS ativo **na Function URL e no código**, a resposta saiu com `Access-Control-Allow-Origin` duplicado e o navegador falhou ("Failed to fetch"). Solução: CORS desligado na Function URL de `sebo-pedido`, `sebo-chegada` e `sebo-consulta`, mantendo só o do código, que também responde ao preflight. Cada URL passou a devolver um único cabeçalho |
| Cenários automatizados | Sim | 9 OK, 0 FALHOU (seção 8) |
| Página web | Sim | Funcionou após o ajuste de CORS acima (listar, pedir, meus pedidos e registrar chegada) |

**Pontos de atenção observados:**
- As Lambdas ficaram com o timeout padrão de 3 s; não houve falha nos testes.
- A Function URL de `sebo-carga` manteve o CORS ligado na própria URL; ela só é usada por `seed.sh` e pelos testes, não pelo navegador.

## 10. Limitações

- A **subscription filter policy** do SNS não foi vista nos slides; foi escolhida para usar um tópico único com entrega seletiva.
- **Function URLs públicas** (Auth NONE); `sebo-carga` apaga dados e fica exposta. Desativar as URLs após a apresentação.
- Uso de **`scan`** com filtro em vez de índice (GSI não foi visto; volume pequeno).
- Credenciais e sessão do Learner Lab são temporárias.
- Em `sebo-processa-espera`, se o pedido já tiver sido tratado por outra execução, o exemplar baixado é devolvido ao estoque (compensação adicionada para não perder estoque em reentrega do Stream).
