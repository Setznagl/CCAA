# CCAA — instruções de disparo em lote no Outlook clássico

## O que esta função faz

No fluxo **AGENDA_FAST_TRACK_INFRA_2026**, o botão **DIsparo em lote**, abaixo do download do HTML de exemplo, abre uma preparação separada. Você carrega um HTML aprovado e uma planilha própria, revisa os destinatários e baixa um pacote ZIP.

**O site não envia emails.** A criação de rascunhos e o envio acontecem no computador do operador, pelo Outlook clássico. A prévia estática original continua intacta, com seu prazo histórico **31/08**: esse exemplo não é um comunicado automaticamente aprovado ou atualizado.

## Requisitos

- Página do CCAA em execução pelo servidor único `testes/preview_server.py` (instalação em `testes/README.md`).
- Para executar o pacote: Windows, Windows PowerShell 5.1 e **Outlook clássico** instalado, com perfil e conta configurados. Não usar Novo Outlook ou Outlook Web.
- Não é necessário instalar Python ou Excel no computador que apenas executa o pacote baixado.
- Autorização e políticas da empresa continuam válidas. Se o script for bloqueado, peça apoio à TI; não desative proteções.

## 1. Preparar o conteúdo

1. Abra a prévia **Agenda Fast Track Infra 2026** e clique em **DIsparo em lote**. A rota é `/fast-track-infra-2026/lote`.
2. Em **Arquivo HTML aprovado**, selecione um `.html` em UTF-8, de até **1 MiB**.
3. Clique em **Conferir HTML carregado** e revise texto, datas e prazos.
4. Preencha o **Assunto padrão**, caso as linhas da planilha não tenham assunto próprio.
5. Se desejar, informe a **Conta remetente do Outlook**. Ela precisa existir entre as contas configuradas no perfil. Vazio usa a primeira conta da sessão, cujo endereço será mostrado para confirmação no Windows.

O mesmo corpo HTML será usado para todas as mensagens; não há personalização por polo. Assinaturas do Outlook, anexos, imagens locais e arquivos externos não são incorporados automaticamente. A prévia do navegador bloqueia recursos externos e não certifica a aparência no Outlook: confira com o teste isolado antes de operar.

## 2. Preparar e revisar os destinatários

Baixe **modelo de destinatários (.xlsx)**, preencha a aba `DESTINATARIOS` e importe o arquivo na página. Preserve estes cabeçalhos e sua ordem:

| Coluna | Como preencher |
|---|---|
| Enviar | `SIM` ou `X` pré-seleciona a linha. Vazio, `NAO`, `NÃO` ou `N` não seleciona. |
| Polo | Identificação para revisão na página; não personaliza o HTML. |
| Para | Pelo menos um email explícito em cada linha selecionada. |
| CC | Emails em cópia, opcionais. |
| CCO | Emails em cópia oculta, opcionais. |
| Assunto | Opcional quando houver assunto padrão; se preenchido, prevalece para aquela linha. |

- Separe múltiplos emails com **`;`**. Use apenas os endereços, sem nomes entre `< >` ou nomes do catálogo.
- Não use fórmulas. Limites: **500 linhas** e **1 MiB** para a planilha.
- Uma linha selecionada equivale a **uma mensagem**. Não há agrupamento automático por gestor ou polo; mensagens idênticas repetidas são rejeitadas.
- Depois da importação, revise os campos **Para, CC, CCO e Assunto**, que podem ser editados na tela, e marque/desmarque as mensagens desejadas.
- Os dados não são gravados nas bases ou no navegador. Saindo da página, será necessário carregar novamente os arquivos.

## 3. Baixar o pacote

1. Confira o total de mensagens selecionadas.
2. Marque a confirmação de revisão de conteúdo, prazos, remetente, assuntos e destinatários.
3. Clique em **Baixar pacote para Outlook clássico (.zip)**.
4. Guarde o ZIP em local restrito: ele contém endereços e o comunicado aprovado.

O pacote contém `abrir.cmd`, `executar.ps1`, `lote.json`, `mensagem.html` e `LEIA-ME.txt`. Não altere os arquivos depois de baixar; para corrigir conteúdo ou destinatários, volte à página e gere um novo pacote aprovado.

## 4. Executar no Windows

1. Abra o Outlook clássico e confira a conta/perfil.
2. **Extraia todo o ZIP** para uma pasta local. Não execute de dentro do ZIP.
3. Mantenha os cinco arquivos juntos e abra **`abrir.cmd`**.
4. Leia a conta exibida antes de qualquer confirmação.

| Opção | Resultado e confirmação |
|---|---|
| `R` ou Enter | **Rascunhos — padrão.** Digite `SIM` para criar os rascunhos. Não envia as mensagens. |
| `T` | **Teste real isolado.** Informe um único email e confirme com `ENVIAR 1`. Usa o HTML aprovado, assunto com `[TESTE]`, sem CC/CCO do lote. Não envia aos destinatários da planilha. |
| `E` | **Envio real.** Confira conta e quantidade pendente; digite exatamente `ENVIAR N`, substituindo `N` pelo número exibido. |

Recomendação de primeira utilização: crie rascunhos, confira sua aparência, realize o teste isolado e somente então autorize o lote real.

### Revisão de rascunhos

Ao escolher `E` depois de criar rascunhos, a ponte busca os mesmos itens salvos e **reaplica o HTML, destinatários e assunto aprovados no pacote**. Alterações feitas diretamente nesses rascunhos não são incorporadas; anexos, destinatários de resposta e delegação adicionados são removidos antes do envio pela ponte.

Feche os rascunhos antes de executar a ponte e não os mova entre pastas/caixas. **Não envie manualmente os rascunhos e depois tente enviar o mesmo lote pela ponte.** Para alterar conteúdo/destinos, revise na página e gere outro pacote, conferindo a possível sobreposição com o anterior.

## 5. Histórico, falhas e prevenção de duplicidade

O estado fica no perfil do operador, fora da pasta extraída:

```text
%LOCALAPPDATA%\CCAA\Lotes\<batch_id>\estado.json
```

- `Draft`: rascunho salvo e identificado no Outlook.
- `Submitted`: chamada de envio aceita pelo Outlook; **não comprova entrega**. Confira Caixa de Saída, Itens Enviados e eventuais mensagens de erro.
- `InProgressSave`, `InProgressSend` ou `Uncertain`: resultado pendente/incerto, com retomada automática bloqueada para evitar duplicidade.

Baixar novamente o mesmo lote mantém a proteção **no mesmo usuário e computador**. Ela não é compartilhada com outros operadores ou máquinas e não protege automaticamente contra sobreposição entre lotes diferentes.

Em erro, interrupção ou estado corrompido, confira o Outlook e procure apoio para conciliar o resultado. **Não apague o histórico, não troque identificadores e não repita cegamente o envio.** A ponte não força sincronização global nem fecha o Outlook; mensagens podem aguardar conexão na Caixa de Saída.

## Limitações de homologação

A preparação web e o ZIP foram exercitados em testes locais; a lógica da ponte foi testada com Outlook simulado. A execução real com Windows PowerShell 5.1, COM, perfil corporativo e renderização precisa ser homologada no Windows antes de uso operacional. Nenhum email real foi emitido durante o desenvolvimento.

Para detalhes da ponte, consulte `testes/lote_outlook/LEIA-ME.txt`; para instalação e testes da bancada, consulte `testes/README.md`.
