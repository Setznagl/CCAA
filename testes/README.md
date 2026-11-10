# CCAA — páginas de teste HTML

Ambiente local, sem transporte de email, macros, Outlook ou refresh. Os quatro módulos em `testes/` seguem `preview_<NOME_EXATO_DO_FLUXO>.py`:

- `preview_AGENDA_SEMANAL_AUDITORIAS.py`
- `preview_AGENDA_REGULARIZACAO_AUDITORIA_ACADEMICA.py`
- `preview_AGENDA_FAST_TRACK_INFRA_2026.py`
- `preview_AGENDA_AUDITORIA_E_SITUACAO_REGULARIZACAO_DOS_POLOS.py`

`preview_server.py` é o único ponto de inicialização HTTP; os módulos de fluxo não abrem servidores próprios. O nome técnico aparece nos controles de cada página.

## Instalar e abrir

Na raiz do clone, com as exportações em `databases/09-11-26`:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r testes/requirements.txt
.venv/bin/python testes/preview_server.py --port 8876
```

Windows: use `.\.venv\Scripts\python.exe`. Não é necessário Excel ou pyxlsb para a bancada.

O endereço base é `http://127.0.0.1:8876/`; navegue pelas páginas:

| Página | Rota |
|---|---|
| Agenda Semanal de Auditorias | `/mari` |
| Agenda de Regularização da Auditoria Acadêmica | `/aulas-praticas` |
| Agenda Fast Track Infra 2026 | `/fast-track-infra-2026` |
| Agenda de Auditoria e Situação de Regularização dos Polos | `/auditoria-situacao-polos` |

A inicialização anuncia uma URL. Porta ocupada encerra a tentativa sem procurar outra porta nem encerrar processos alheios. O serviço é loopback: não publicar dados pessoais. Acesso de outra máquina depende do encaminhamento autorizado do ambiente.

## Fontes e suplementos

### Agenda Semanal de Auditorias

Lê timeline e as duas bases gerenciais da pasta nova, não XLSM/Master. Mantém todas as linhas de laboratório e datas disponíveis para seleção explícita; não filtra automaticamente a semana corrente. O contador distingue polos únicos e linhas de laboratório.

Agrupa os polos pelo nome e email do **gestor do polo destinatário**, não pelo GO. Nome, email e grupo econômico vêm de `auditoria-base-gerencial.xlsx`. Homônimos com emails diferentes continuam separados e são identificados no seletor. Revise as linhas/datas e confirme o período antes de gerar. A data de referência afeta avisos de data passada, não substitui as datas das auditorias. No email, o rótulo do destinatário passa a ser Gestor do Polo, mantendo a arte.

Nas três páginas dinâmicas, `gerencial.py` cruza o nome completo do polo (sem fuzzy match) com a gerencial e resolve emails dos papéis de cópia por nome normalizado em `auditoria-base-gerencial-contatos.xlsx`. Não infere destinatários pelo GO nem equipara papéis diferentes. Conflitos de emails no cadastro não são resolvidos escolhendo o primeiro.

O painel de destinatários apresenta contatos preenchidos sem repetir a mesma pessoa em cada polo. Somente lacunas geram campos de complemento. Quando não há vínculo acadêmico, **escolha um auditor cadastrado para cada polo**; a aba `AUDITORES` da gerencial contém os nomes e emails autorizados, incluindo os novos sem vínculo. A escolha só vale para a geração atual, não altera bases nem o auditor do checklist. Negócios/infra sem dados continuam identificados como não informados e podem ser complementados; nomes e email do destinatário e escolha acadêmica são validados no servidor. Excluir um polo remove suas exigências e contatos da revisão.

### Agenda de Regularização da Auditoria Acadêmica

Renderer próprio, sem AST/exec do disparador legado. Lê `auditoria-apps-prazo.xlsx` e `auditoria-timeline-262.xlsx`. As práticas são agregadas por polo; não há sequências inventadas. Laboratórios/pareceres e suplementos são revisados antes da geração; prazos sem fonte são informados manualmente, não herdados das datas históricas do modelo.

Ausência de linha na timeline não comprova ausência de auditoria. Contagens ausentes não viram zero. O corpo HTML não lê destinatários nem a planilha intermediária de emails.

### Agenda Fast Track Infra 2026

O módulo de mesmo nome lê os bytes de `fluxos/AGENDA_FAST_TRACK_INFRA_2026/modelo_email.html`. Não lê planilhas, não converte PDF em runtime e não possui campos. O texto atual é o **Comunicado CLFT_13.11.pdf**, com prazo **20/11/2026, sem prorrogações**; imagens incorporadas, fontes, cores e estrutura institucional foram preservadas. Rodapés editoriais do PDF não fazem parte do corpo. O nome antigo da pasta continua aceito para o modelo estático.

#### DIsparo em lote — ponte para Outlook clássico

Guia do operador: [CCAA — instruções de disparo em lote](../docs/CCAA-disparo-em-lote-outlook.md).

O botão abaixo do download abre `/fast-track-infra-2026/lote`, uma preparação separada da prévia estática. O corpo revisado é o mesmo em todas as mensagens; a prévia isolada continua sem leitura de planilhas. Nesta página:

1. Clique em **Carregar polos com checklist pendente**. Inclui a união dos polos com `Data Checklist de Laboratório` vazia em `databases/acompamento/polos-irregulares-fasttrack.xlsx` e `DATA CL` vazia em `databases/acompamento/auditoria-infraestrutura-fasttrack.xlsx`. Basta um critério, sem veto por status da outra base. Somente nulo/espaços são vazios; não zero, fórmula ou erro. Abas auxiliares são ignoradas. Uma opção por nome completo normalizado, com os motivos visíveis. O corpo é o modelo atual byte-intacto com prazo 20/11/2026, sem inputs de conteúdo.
2. Para vem do gestor na gerencial; CC é negócios/infra dos cadastros de `databases/09-11-26`, mais o acadêmico em seletor separado. Se faltar vínculo acadêmico, escolha manualmente um cadastrado na aba AUDITORES por polo selecionado. Sem escolha ou Para válido, não exporta. Não cria vínculos nem persiste alterações.
3. Busque por polo/gestor, selecione os polos e revise Para, CC, CCO e assuntos. **Selecionar visíveis** respeita o filtro; seleções anteriores fora dele permanecem. Uma mensagem por polo, sem agrupamento por gestor. Nenhum polo começa selecionado. Assunto automático: `[ PREENCHIMENTO OBRIGATÓRIO - CL INSUMOS e CL REVENUE SHARE] Novo prazo máximo para preenchimento - <nome do polo>`, revisável por linha; vazio recompõe esse padrão. Registros de expansão sem identificação segura ficam com contatos em branco, sem associação por cidade. Conta remetente vazia usa a conta padrão do Outlook; conta explícita precisa estar configurada nele. A alternativa manual de HTML/DESTINATARIOS permanece disponível em bloco separado.
4. Confira a prévia isolada e confirme a revisão de conteúdo, prazo e destinatários. Baixe o ZIP.
5. No Windows com **Outlook clássico configurado**, extraia o ZIP e abra `abrir.cmd`. A ponte oferece rascunhos por padrão, teste isolado (sem CC/CCO do lote) e envio com confirmação própria. Leia `LEIA-ME.txt` antes de operar. Não há envio pelo servidor.

Limites: 500 linhas, 1 MiB por HTML/planilha e 4 MiB por requisição de lote. Endereços devem ser explícitos, separados por `;`; nomes do catálogo Outlook não são resolvidos automaticamente. No lote mapeado, polos repetidos são rejeitados; polos diferentes com contatos iguais permanecem mensagens separadas. No importador manual, mensagens duplicadas idênticas continuam rejeitadas. Imagens locais, anexos e assinaturas não são empacotados automaticamente. Verifique a renderização por teste no Outlook.

O ZIP contém dados pessoais: proteja o download. A página não grava uploads nas bases, no disco do servidor ou no localStorage; as últimas 16 prévias compartilhadas ficam em memória. O histórico da ponte é **local ao Windows**, separado das fontes e preservado entre downloads do mesmo lote. Ele reduz reenvio acidental, mas não comprova entrega nem substitui a conferência no Outlook. Mudar conteúdo, destinatários ou remetente gera outro lote. Não apague o histórico para contornar uma falha incerta. Se a política corporativa bloquear scripts, solicite liberação à TI, sem alterar a política pelo pacote.

Teste da página com servidor temporário próprio:

```sh
CCAA_PLAYWRIGHT_MODULE=/caminho/playwright/index.mjs .venv/bin/python testes/run_lote_e2e.py
```

Os testes locais não certificam automação COM nem entrega em um Outlook real; essa homologação deve ser feita no Windows, primeiro em rascunhos e depois com teste isolado.

### Agenda de Auditoria e Situação de Regularização dos Polos

- Carteira: gestor do polo da gerencial; somente polos presentes em timeline, apps ou acompanhamento. Agrupa por nome + conjunto de emails, sem fundir homônimos ou nomes diferentes por um email compartilhado. Polos sem associação completa continuam no preenchimento manual.
- Práticas: apps-prazo. Agenda/pareceres: timeline. Indicador Rep. Sem Retorno: acompanhamento, somente com cobertura completa e fonte única por polo.
- Datas da agenda: realizadas/finalizadas priorizam `Data realização`; quando ausente, usam `Data agendada` com a indicação **data agendada como referência** no status do formulário e do email. Agendadas usam a data agendada; sem nenhuma data disponível, o campo fica vazio. Data de referência não comprova realização nem preenche os prazos manuais. Ao alterar uma data manualmente, revise também o status.
- Checklist CL2026 e prazos sem fonte permanecem manuais. Contatos de apoio são preenchidos pelas bases e pelas escolhas acadêmicas; suplementos manuais do corpo são preservados. Vereditos e acadêmicos de cópia não são checklist. Carteira e linhas carregadas podem ser revisadas sem alterar as fontes.
- 262 e 26.2 são sinônimos. Ciclo ausente fica desconhecido; mudar o título não atualiza a origem. Rodapés EN/PT são metadados, não polos.
- Alterar a carteira limpa o indicador agregado para revisão. Totais de práticas são recalculados sem converter ausências em zero. Avisos de polos sem associação ficam na revisão manual, não em carteiras alheias.
- Contatos derivados conservam sua origem mesmo após editar nome/email/telefone: remover o único polo associado também remove o contato do corpo. Contatos novos adicionados manualmente continuam como suplementos independentes.

Na carga do consolidado, `databases/09-11-26/emails.xlsx` é gerada com **Polo | Email | Enviar**: emails dos gestores de polo da gerencial, distintos e concatenados com `;`, Enviar vazio. A escrita é atômica, protegida contra fórmulas e ignorada no Git. Uma falha de escrita vira aviso; o HTML continua usando as fontes originais. Mudança da assinatura das fontes provoca regeneração na próxima carga. O arquivo não é fonte de dados do corpo nem configuração de envio.

## Segurança e comportamento

Dados são carregados e mantidos em memória; reinicie o servidor após substituir bases. Campos manuais não são gravados em planilhas ou localStorage, nem enviados pela URL. A única escrita derivada é emails.xlsx. A geração revisada usa POST JSON limitado a 1 MiB e snapshots opacos; as últimas 16 prévias ficam em memória.

Qualquer edição/seleção invalida prévia e download, inclusive durante requisição. Respostas antigas não podem restaurar um resultado descartado. O HTML no iframe é isolado por sandbox/CSP; download e snapshot têm os mesmos bytes, sem painel de controle. Layouts de email fixos podem exigir rolagem dentro do iframe no celular; não equivalem a validação Outlook/Gmail.

Controles seguem o visual web do LIRA, com fontes locais. Arte dos emails preservada. A exportação de lote Fast Track não habilita serviços de email no servidor; os outros fluxos continuam sem integração de envio.

## Testes

Da raiz:

```sh
.venv/bin/python -m unittest discover -s testes -p 'test_*.py' -v
CCAA_PLAYWRIGHT_MODULE=/caminho/playwright/index.mjs CCAA_TEST_URL=http://127.0.0.1:8878 node testes/test_gerencial_e2e.mjs
CCAA_PLAYWRIGHT_MODULE=/caminho/playwright/index.mjs node testes/test_contact_state.mjs
```

O commit remoto `1.0` removeu a suíte anterior. `test_gerencial.py` cobre esta integração com bases sintéticas (agrupamento, vínculos, validação e exportação derivada), sem restaurar arquivos antigos. Fixtures não são fontes operacionais.

Os E2E exigem Playwright/Chromium e aceitam `CCAA_PLAYWRIGHT_MODULE`, `AGENT_BROWSER_EXECUTABLE_PATH`, `CCAA_TEST_URL` e `CCAA_EVIDENCE`. Inicie antes o servidor de teste na mesma porta. Evidências ficam fora do repositório (padrão `/opt/data/cache/scratch/ccaa-gerencial-evidence`). Use um servidor de teste apenas durante a execução e encerre-o ao terminar.
