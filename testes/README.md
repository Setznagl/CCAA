# CCAA — páginas de teste de HTML

Ambiente local de inspeção, sem integração com serviços de email e sem executar macros ou Outlook.

## Abrir as páginas

Na raiz do seu clone, com os arquivos em `fluxos/`, execute:

```sh
.venv/bin/python testes/preview_server.py --port 8876
```

- Agenda Semanal de Auditorias: `http://127.0.0.1:8876/mari`
- Agenda de Regularização da Auditoria Acadêmica: `http://127.0.0.1:8876/aulas-praticas`
- Agenda Fast Track Infra 2026: `http://127.0.0.1:8876/fast-track-infra-2026`
- Agenda de Auditoria e Situação de Regularização dos Polos: `http://127.0.0.1:8876/auditoria-situacao-polos`

O servidor escuta apenas no loopback da máquina em que foi iniciado. Se Hermes e navegador estiverem em máquinas diferentes, use o acesso local/encaminhamento autorizado do seu ambiente; não publique esta porta, pois as bases contêm dados pessoais.

Em Mari/Aulas, selecione um gerente/grupo ou polo. Em Fast Track, não há campos para preencher. Clique em **Gerar HTML de teste**, confira a prévia e use **Baixar HTML gerado**. Trocar a seleção invalida o download anterior até gerar novamente.

No consolidado, selecione um gestor para carregar os dados locais ou escolha preenchimento manual. Revise a carteira e complete os campos antes da geração. Qualquer edição invalida o download anterior, inclusive durante uma requisição pendente. O formulário não é salvo automaticamente: conserve o HTML baixado antes de sair ou trocar de gestor.

A primeira leitura da Master pode demorar; os gestores ficam disponíveis após essa carga e as consultas seguintes usam o cache em memória. Na verificação deste ambiente, a primeira carga levou cerca de 104 segundos. O formulário e a prévia ficam em sequência para permitir leitura integral do email no desktop; tabelas de edição podem ter rolagem própria em telas menores.

O arquivo baixado contém somente o HTML do email. A página de controle não é incluída. A prévia conserva estilos inline e bloqueia scripts, formulários e carregamento de recursos externos. As tabelas de largura fixa do email podem exigir rolagem dentro da prévia no celular; o layout do email não é redesenhado pelo painel.

## Instalação em uma cópia nova

Verificado com Python 3.14 e as dependências fixadas em `testes/requirements.txt`:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r testes/requirements.txt
.venv/bin/python testes/preview_server.py
```

No Windows, use `.venv\\Scripts\\python.exe` no lugar de `.venv/bin/python`. O ambiente de teste de Mari não exige Excel: trata-se da reprodução isolada expressamente autorizada, não execução do VBA original.

## O que cada página valida

### Agenda Semanal de Auditorias

Lê somente os valores já armazenados de `fluxos/AGENDA_SEMANAL_AUDITORIAS/Disparador_auditoria_automatizado_FINAL(1).xlsm`, aba `Aba de auditorias`, sem atualizar fórmulas, contatos ou consultas. A montagem HTML é uma reprodução isolada do Módulo1 atual. A data do controle afeta apenas avisos de data passada/próxima no email, não as datas das auditorias.

Para comparar com a prévia salva do grupo Adiel, use a data **11/09/2026**. A equivalência com o arquivo salvo é objeto dos testes de Mari; isso não certifica compilação ou execução das macros no Excel.

### Agenda de Regularização da Auditoria Acadêmica

Reutiliza diretamente, a partir do código recebido, `chave`, `ler_sequencias`, `adicionar_labs` e `gerar_html`, com suas constantes necessárias. Essas funções são selecionadas por AST, sem importar/executar o entrypoint do disparador e sem carregar funções de transporte.

Para inspecionar o corpo HTML, lê as quatro planilhas de sequência e `labs.xlsx`. Não lê `emails.xlsx` ou Master, não resolve destinatários e não aplica autorização/seleção de envio: esses dados não são usados pelo corpo HTML atual. A saída foi comparada à geração com os leitores completos para verificar que essa separação não altera o HTML.

### Agenda Fast Track Infra 2026

Serve diretamente `fluxos/AGENDA_FAST_TRACK_INFRA_2026/modelo_email.html`, reproduzido a partir do corpo de `exemplo_email.pdf`. Sem campos, sem consulta às planilhas e sem processamento do PDF em tempo de execução. Mantém texto, prazo histórico **31/08** e link do book extraído do PDF; não inclui cabeçalho Outlook, assunto personalizado ou contatos do destinatário da impressão. Imagens do modelo são incorporadas ao HTML; o texto do corpo continua selecionável. Não exige dependência de PDF para executar. Aceita também o caminho anterior quando usado num clone legado.

As bases dessa pasta serão usadas somente em etapa futura.

### Agenda de Auditoria e Situação de Regularização dos Polos

- Master: carteira por `GESTOR DE POLO / DIRETOR UNIDADE`, considerando canal PARCEIRO e situação UNIDADE EM OPERACAO/CAPTACAO. Usa somente as colunas necessárias ao cadastro da carteira, não dados pessoais ou contratuais sem uso na prévia.
- Quatro sequências: quantitativos de práticas por polo. `labs.xlsx`: agenda e resultados de laboratórios. `aprovacao.xlsx`: indicador Rep. Sem Retorno, sem equipará-lo à contagem de pareceres Reprovado.
- Os leitores aceitam `AGENDA_REGULARIZACAO_AUDITORIA_ACADEMICA` e o nome anterior. O sample de referência também aceita as nomenclaturas moderna e legada; não é executado como programa nem usado como fonte operacional dos números.
- Campos manuais: gestor/ciclo, carteira, checklist (nota, status, observação e auditor), agenda, práticas, resultados, indicador sem retorno, prazos, links e contatos. Os dados carregados também podem ser revisados; não são gravados nas planilhas.
- As fontes conferidas indicam **261 = 26.1**; **262 = 26.2**. O ciclo inicial acompanha as fontes. Mudar o título para 262 não muda o semestre carregado: o aviso de origem permanece no painel e no HTML.
- Lacunas permanecem em branco/Não informado, sem copiar dados demonstrativos da pessoa do sample ou assumir zero/não comparecimento. Os prazos gerais começam vazios para preenchimento, em vez de reapresentar 04/10 e 06/10 como vigentes.
- Totais de práticas são recalculados das linhas informadas; valores ausentes não viram zero. Ao alterar a carteira, o indicador agregado de reprovados sem retorno é limpo para revisão manual, pois o agregado anterior se referia a outro recorte. Avisos identificadores de polos excluídos não entram no HTML.
- Formulário enviado por POST JSON de até 1 MiB; valores manuais não aparecem na URL. Uma URL opaca de prévia referencia exatamente os bytes retornados para download, com CSP isolada. Só as últimas 16 prévias ficam na memória do servidor; as anteriores expiram e podem ser geradas novamente. Não há persistência das edições em disco ou localStorage.

## Limites deliberados

- Correções de lógica/checagens de negócio continuam adiadas em `docs/CCAA-pontos-de-atencao-adiados.md`.
- Não há envio, rascunhos Outlook, atualização SharePoint nem alteração das fontes recebidas.
- Mari, Aulas e consolidado usam bases locais de `fluxos/`; upload de arquivos não faz parte desta etapa. O consolidado permite digitação manual; Fast Track não lê bases.
- Os dados são carregados na primeira utilização e mantidos em memória. Reinicie o servidor após mudar arquivos para uma nova rodada de teste.
- Os controles usam visual neutro temporário, autorizado pelo usuário. O HTML do email mantém seu estilo atual. A referência final LIRA permanece para a etapa visual posterior.
- Navegador não certifica renderização no Outlook/Gmail nem entrega de email.

## Testes

```sh
cd testes
../.venv/bin/python -m unittest discover -p 'test_*.py' -v
node --test test_app.mjs test_consolidado_app.mjs
```

Os testes Node não exigem pacotes adicionais e verificam também a troca de seleção/data durante uma geração pendente.

Os dois testes de comparação com a prévia Mari dependem de `fluxos/AGENDA_SEMANAL_AUDITORIAS/previews/adiel_martins_cogna_com_br.html`. Essa amostra não veio na reorganização recebida; sem ela, os testes de comparação falham por arquivo ausente, embora a página gere HTML. Os testes Fast Track usam uma fixture HTML temporária e não precisam de bases reais.

O teste de navegador `test_e2e.mjs` exige Playwright e Chromium disponíveis no ambiente de desenvolvimento; aceita `CCAA_PLAYWRIGHT_MODULE`, `AGENT_BROWSER_EXECUTABLE_PATH` e `CCAA_TEST_URL`. Evidências locais ficam em `testes/evidence/`.

`test_consolidado_e2e.mjs` exercita o quarto fluxo com carteira real, edição manual, criação integral manual, exclusão de polo, fonte semestral preservada, proteção contra texto HTML, download idêntico ao snapshot e resposta obsoleta bloqueada. Ambos os E2E verificam desktop/móvel, ausência de requisições externas e erros JavaScript.
