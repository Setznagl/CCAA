# CCAA — instruções de disparo em lote no Outlook clássico

## O que esta função faz

No fluxo **AGENDA_FAST_TRACK_INFRA_2026**, o botão **DIsparo em lote**, abaixo do download do HTML, abre uma preparação separada. Clique em **Carregar polos com checklist pendente**, revise os contatos, selecione os polos e baixe um ZIP único compatível com a ponte existente. Não é necessário carregar HTML ou planilha manualmente neste caminho.

**O site não envia emails.** A criação de rascunhos e o envio acontecem no computador do operador, pelo Outlook clássico. O corpo usa os bytes do modelo aprovado, sem preenchimentos nem personalização. O texto foi substituído pelo **Comunicado CLFT_13.11.pdf**, cujo prazo é **20/11/2026, sem prorrogações**, preservando a arte institucional anterior. A confirmação de revisão continua obrigatória antes do download.

## Requisitos

- Página do CCAA em execução pelo servidor único `testes/preview_server.py` (instalação em `testes/README.md`).
- Para executar o pacote: Windows, Windows PowerShell 5.1 e **Outlook clássico** instalado, com perfil e conta configurados. Não usar Novo Outlook ou Outlook Web.
- Não é necessário instalar Python ou Excel no computador que apenas executa o pacote baixado.
- Autorização e políticas da empresa continuam válidas. Se o script for bloqueado, peça apoio à TI; não desative proteções.

## 1. Preparar o lote pelos checklists pendentes

1. Abra a prévia **Agenda Fast Track Infra 2026** e clique em **DIsparo em lote**. A rota é `/fast-track-infra-2026/lote`.
2. Clique em **Carregar polos com checklist pendente**. Entram os polos que satisfaçam **qualquer um** destes critérios independentes:
   - `Data Checklist de Laboratório` vazia na primeira aba de `databases/acompamento/polos-irregulares-fasttrack.xlsx`;
   - `DATA CL` vazia em `Planilha1` de `databases/acompamento/auditoria-infraestrutura-fasttrack.xlsx`.
   Células nulas ou contendo apenas espaços são vazias; zero não é vazio, fórmulas/erros nas colunas de seleção são recusados. Abas `Comments` e `Planilha2` não participam. A união é pelo nome completo normalizado, sem duplicar o mesmo polo. O status Reprovado **não é mais critério de inclusão nem veto global**: um polo reprovado na primeira base ainda entra se satisfizer o critério da segunda.
3. Clique em **Conferir HTML do lote** e revise o comunicado, incluindo o prazo 20/11/2026. O corpo não recebe dados das planilhas nem campos manuais. Os dois links úteis vieram do PDF e exigem login no PAD.
4. Revise o **Assunto do polo**, preenchido automaticamente com o padrão abaixo e o nome completo do registro. Pode ser editado por linha. Se apagado, o servidor recompõe o padrão daquele polo; o campo de assunto padrão global é exclusivo da alternativa manual.
5. Se desejar, informe a **Conta remetente do Outlook**. Ela precisa existir entre as contas configuradas no perfil. Vazio usa a primeira conta da sessão, cujo endereço será mostrado para confirmação no Windows.

O mesmo corpo HTML será usado para todas as mensagens; não há personalização por polo. Assinaturas do Outlook, anexos, imagens locais e arquivos externos não são incorporados automaticamente. A prévia do navegador bloqueia recursos externos e não certifica a aparência no Outlook: confira com o teste isolado antes de operar.

Padrão do assunto (o marcador final é substituído pelo nome do polo):

```text
[ PREENCHIMENTO OBRIGATÓRIO - CL INSUMOS e CL REVENUE SHARE] Novo prazo máximo para preenchimento - COLOCAR NOME DO POLO AQUI
```

## 2. Selecionar e revisar os destinatários

- Os contatos vêm exclusivamente de `databases/09-11-26/auditoria-base-gerencial.xlsx` e `auditoria-base-gerencial-contatos.xlsx`, incluindo a aba `AUDITORES`. Contatos escritos nas duas bases temporárias Fast Track são ignorados.
- **Para** vem do gestor do polo; **CC** é preenchido com negócios e infraestrutura. O **acadêmico em CC** aparece em seletor separado, com nome e email, e é acrescentado ao CC final no pacote.
- Se não houver vínculo acadêmico, escolha manualmente um cadastrado para aquele polo. A exportação é bloqueada se qualquer polo selecionado estiver sem acadêmico ou sem email válido em Para. A escolha vale só para esta preparação; não cria vínculo nem altera as bases.
- Nenhum polo é selecionado automaticamente. Use a busca por polo/gestor, **Selecionar visíveis**, os checkboxes individuais ou **Limpar seleção inteira**. A busca não desmarca seleções fora do filtro: confira o contador total antes de baixar.
- Uma mensagem por polo selecionado, mesmo se dois polos tiverem os mesmos destinatários. Não há agrupamento por gestor. Um polo repetido ou fora da união atual de pendências é recusado pelo servidor. Cada registro mostra qual checklist motivou sua inclusão.
- Para, CC, CCO e assuntos são revisáveis. Um polo não encontrado na gerencial continua visível com contatos em branco para complemento manual. Registros de expansão sem identificação segura não são associados por semelhança de cidade, mesmo se o ID estiver ausente ou `#N/A`. Desmarcar um polo remove suas exigências de preenchimento.
- Recarregar os polos descarta a revisão dos contatos. Saindo da página, as escolhas não são persistidas. Nenhum contato é enviado em parâmetros da URL.

### Alternativa manual anterior

Continua disponível em **Alternativa manual: carregar HTML e planilha próprios**. Esse caminho substitui o cruzamento automático e mantém o contrato anterior; a seleção acadêmica por cadastro é exigida no caminho de checklists pendentes, não no importador genérico.

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
- Na alternativa manual, uma linha selecionada equivale a **uma mensagem**, sem agrupamento automático; mensagens idênticas repetidas são rejeitadas.
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
