# CCAA — campos e fontes dos emails

Este é o mapa do funcionamento atual: VBA embutido em Mari e Python da raiz de AulasPraticas. Não descreve o novo modelo consolidado nem afirma que todo campo seja uma trava obrigatória do código. Entradas auxiliares, campos calculados, configurações e itens ignorados estão identificados.

## Referências de arquivos

- **Mari / XLSM:** `rev/Disparo Auditoria Mari/Disparador_auditoria_automatizado_FINAL(1).xlsm`.
- **Python vigente:** `rev/DisparoAulasPraticas/disparar_emails.py`.
- **Master do Python:** `rev/DisparoAulasPraticas/Base de Polos - Master (1).xlsb`; primeira aba `BASE_DE_UNIDADES` e aba `CONTATOS_PARCEIROS`.
- Abreviação **planilhas de sequência**: `sequenciaa1.xlsx`, `sequenciaa2.xlsx`, `sequencia3.xlsx`, `sequencia4.xlsx`, na pasta de AulasPraticas.

## Campos e proveniência

| Frente | Campo/dado | Origem atual | Uso / observação |
|---|---|---|---|
| Mari | Polo | XLSM → Aba de auditorias!A, desde linha 10; preenchido/colado na lista operacional | Identifica a linha e aparece no email; precisa estar preenchido |
| Mari | ID COLABORAR | Aba de auditorias!B; fórmulas procuram o nome de A em Base_polos!A e retornam Base_polos!D; há exceção fixa em fórmula | Auxiliar da atualização; o disparador não usa B diretamente |
| Mari | Grupo econômico | Aba de auditorias!C ← Base_polos!CI no Módulo2 embutido | Exibido na tabela; CI contém quantidade de unidades. Os exports usam CH, que contém o nome do grupo |
| Mari | Data da auditoria | Aba de auditorias!D; preenchimento da lista operacional | Exibida e usada no período; vazia pode aparecer como A marcar |
| Mari | Nome do gerente/GO | Aba de auditorias!E ← Base_polos!U, localizado pelo ID B ↔ D da base | Personalização; o embutido usa GERENTE OPERACIONAL. O primeiro nome do grupo prevalece |
| Mari | Email principal — Para | Aba de auditorias!F ← Contatos!D, buscando Contatos!A pelo nome em E | Destinatário e chave do agrupamento; email inválido exclui a linha |
| Mari | Cópia oculta — BCC/CCO | Aba de auditorias!H; preenchimento da lista operacional | Opcional; endereços são reunidos por grupo de destinatário |
| Mari | Auditor responsável | Aba de auditorias!G | Existe na entrada, mas é ignorado pelo gerador/envio atual |
| Mari | Quantidade, índice, período e próxima data | Calculados com as linhas agrupadas por F e suas datas D | Quantidade conta linhas; período usa menor/maior data; próxima usa a menor, inclusive se passada |
| Mari | Dia da semana e indicação de data passada | Data D e Date do computador no VBA | Calculados; a data da execução altera o texto/cores de vencimento |
| Mari | Remetente e assunto | Constantes EMAIL_REMETENTE e ASSUNTO em Modulo1 | Fixos no código; remetente requer conta/permissão Outlook correspondente |
| Mari | Área, subárea, título, orientações, fechamento e link de atendimento | Constantes AREA_MACRO, SUB_AREA, LINK_ATEND e textos de MontarHTML/ItemOrientacao | Conteúdo fixo; não vem das bases |
| Mari | Telefone do GO — WhatsApp | Contatos!C; busca por email em D, com fallback por nome em A | Opcional e somente do painel WhatsApp; não é necessário para o email |
| Mari | Mensagem, assinatura e URL do WhatsApp | Nome/polos/datas do grupo + MensagemWhats, WHATS_ASSINATURA e WHATS_URL | Derivado e fixo no VBA; abre texto pronto, não envia automaticamente |
| AulasPraticas | Nome do polo | Coluna Polo das quatro planilhas de sequência | Cria o conjunto inicial de polos e identifica o email |
| AulasPraticas | Chave de junção do polo | Função chave(): último número entre parênteses no nome; fallback para prefixo do nome | Liga sequências, labs, emails e Master; não equivale necessariamente aos outros IDs numéricos |
| AulasPraticas | Número da sequência | ARQUIVOS_SEQ: 1=sequenciaa1.xlsx; 2=sequenciaa2.xlsx; 3=sequencia3.xlsx; 4=sequencia4.xlsx | Configuração fixa por arquivo; não lido de uma coluna |
| AulasPraticas | Aulas previstas | Planilha de sequência → Total de Aulas | Valor por polo/sequência |
| AulasPraticas | Aulas comprovadas | Planilha de sequência → Comprovadas | Valor por polo/sequência |
| AulasPraticas | Aulas pendentes | Planilha de sequência → Pendentes | Importadas; o gerador não recalcula previstas menos comprovadas |
| AulasPraticas | Percentual por sequência e total | Calculado por comprovadas ÷ previstas × 100; totais somam as sequências carregadas | Não lê Comprovação (%) da planilha; quando previstas=0, usa 0 |
| AulasPraticas | Nome do laboratório | labs.xlsx → Laboratório, associado pela coluna Polo | Detalhamento individual; seção é omitida quando não há labs associados |
| AulasPraticas | Parecer do laboratório | labs.xlsx → Parecer Auditoria | Entrada para Aprovado/Reprovado/Pendente/Sem parecer |
| AulasPraticas | Contadores de laboratórios, rótulo e ação recomendada | Calculados de labs_lista e info_parecer() no Python | Total é tamanho da lista; aprovados/reprovados por prefixo do parecer; restante contado como pendente |
| AulasPraticas | Email principal — Para | emails.xlsx → Email por Polo; depois Master → EMAIL GESTOR PRISMA / EMAIL DIRETOR DE UNIDADE, se houver endereço com @ | A Master prevalece quando encontra email; sem ele, mantém o de emails.xlsx |
| AulasPraticas | Nome do gerente operacional | Master / BASE_DE_UNIDADES → GERENTE OPERACIONAL, por NOME UNIDADE SISTEMA | Usado para localizar a cópia oculta; não muda o agrupamento por polo |
| AulasPraticas | Email do GO — BCC/CCO | Master / CONTATOS_PARCEIROS: B=Nome, C=Cargo, E=E-mail; complemento EMAILS_GERENTES_EXTRA | Restringe contatos a cargo contendo operacional; tenta nome normalizado exato/depois prefixo; complemento manual para ausentes |
| AulasPraticas | Canal e status de elegibilidade | Master / BASE_DE_UNIDADES → CANAL e STATUS DA UNIDADE/POLO | --marcados usa PARCEIRO e status contendo OPERACAO/CAPTACAO; primeira linha por chave prevalece |
| AulasPraticas | Marcação manual Enviar | emails.xlsx → Enviar, associada por Polo | Lida inicialmente, mas substituída pela elegibilidade quando a consulta da Master é aplicada |
| AulasPraticas | Cópia visível — CC | Constante EMAIL_AUDITORES | Fixa para todos os envios; não vem da Master |
| AulasPraticas | Remetente e nome de exibição | Constantes EMAIL_REMETENTE e NOME_REMETENTE | Código contém remetente placeholder; configurar conta/permissão antes de envio |
| AulasPraticas | Assunto, título e subtítulo | TITULO e SUBTITULO; assunto construído como [RGC] + TITULO + nome do polo | Fixos/derivados no código |
| AulasPraticas | Área, subárea e textos institucionais | AREA_MACRO, SUB_AREA e textos literais de gerar_html() | Fixos; não vêm das exportações |
| AulasPraticas | Prazos e links | Datas 31/05/2026 e 26/06/2026 e links Prisma/Smartsheet escritos em gerar_html() | Fixos no template atual, não lidos de planilha |
| AulasPraticas | Configuração de transporte SMTP | SERVIDOR_SMTP, PORTA_SMTP, EMAIL_REMETENTE e SENHA | Somente --smtp; senha hoje é placeholder. Não é dado de negócio nem deve ser gravada no vault |
| AulasPraticas | Modo de operação e filtro | Argumentos --polo, --marcados, --mostrar, --rascunho, --enviar e --smtp | Controle da execução, não campo de planilha; SMTP com mostrar/rascunho entra no caminho de envio |
| Ambas | Cores, fontes, larguras e formatação atuais | HTML/CSS embutidos em MontarHTML do VBA e gerar_html do Python | Estilo legado atual. Nova regra aprovada: espelhar arte do LIRA; tokens detalhados ainda a recuperar |

## Campos disponíveis, mas não aproveitados pelo gerador atual

- **Mari:** ID B participa da atualização, mas B e auditor G não entram diretamente no email. Não há CC configurado nesse disparador. Uma aba de auditorias já preenchida pode gerar a prévia sem atualizar a base.
- **Labs:** semestre, IDs auxiliares, Canal, Cape, Local, Tipo auditoria, Auditor, Agendada, Data agendada, Realizada, Data realização e Finalizada existem em labs.xlsx, mas o Python vigente só usa Polo, Laboratório e Parecer Auditoria.
- **Sequências:** Comprovação (%), Dentro do prazo (%), Validadas e Validação (%) não são consumidas pelo gerador atual.
- **aprovacao.xlsx:** não é lido pelo Python da raiz; `% Aprovação` é usado apenas pelo script antigo em `scripts/disparar_emails.py`.
- **Nome do gestor/carteira e checklist:** não são um conjunto de campos de consolidação implementado nas duas saídas atuais. Não confundir o GO de Mari com o gestor de polo/diretor nem a base de contatos com resultados de checklist.

## Evidências e ressalvas

- Mari: `Modulo1` linhas 27–47 (constantes), 136–205 (colunas/agrupamento), 364–583 (HTML), 609–755 (WhatsApp); Módulo2 embutido 125–178 (CI/U/contato). Os exports de Módulo2 diferem: CH, tentativa de GN e Apelidos/TBD. A tabela acima não atribui essas melhorias ao XLSM.
- Coluna B de Mari: fórmulas armazenadas observadas em B10:B80; procuram nome na base e têm exceção literal para um polo. Os números de códigos não são automaticamente equivalentes entre sistemas.
- Python: 59–95 (configuração), 102–179 (chaves/sequências/labs), 182–323 (emails/Master), 330–602 (HTML e cálculos), 609–699 (transporte), 706–787 (modos).
- Base_polos e Contatos de Mari já estão armazenados no XLSM; possuem consultas Power Query de origens SharePoint diferentes, não atualizadas nesta análise. O Python lê os arquivos locais, não consulta o Power BI ao vivo.
- A regra futura de arte do CCAA deve espelhar LIRA, mas os tokens concretos não foram recuperados nas buscas desta etapa. Nenhuma identidade alternativa foi inventada ou aplicada.
- Não houve mudança nos geradores, execução de macros ou emissão de emails.
