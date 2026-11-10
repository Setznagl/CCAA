# CCAA — Cobertura das bases `databases/09-11-26` para migração da fonte

Avaliação estática das cinco planilhas recebidas em 09/11/2026, comparadas ao inventário de campos das prévias (`fluxos/CCAA-inventario-consolidado-262-revisado.md`). Objetivo: determinar se a pasta pode se tornar a **única fonte** das informações usadas nas prévias que leem bases (Aulas práticas e o consolidado), ou se ainda serão necessárias bases suplementares. Leituras somente estáticas; nenhuma planilha foi alterada.

Semestre de referência: **262 (26.2)**. Timeline, acompanhamento, apps reexportado e vereditos declaram **262 explicitamente** em rodapé ou coluna própria; as fontes anteriores indicavam 261/26.1. Na integração de 10/11, as contagens abaixo foram reconferidas excluindo separadores e rodapés de exportação: estes não são polos. As cinco fontes permanecem idênticas aos bytes versionados em HEAD.

## Arquivos recebidos

| Arquivo | Conteúdo | Ciclo declarado | Polos |
|---|---|---|---|
| `auditoria-timeline-262.xlsx` | 1.762 linhas por laboratório: tipo, ambiente, auditor, datas agendada/realizada, status e parecer | **262** (rodapé + coluna) | 460 |
| `auditoria-polos-acompanhamento-262.xlsx` | Resumo por polo: labs aprovados/reprovados, Rep. Sem Retorno e percentuais | **262** (rodapé) | 461 |
| `auditoria-apps-prazo.xlsx` | Aulas práticas por polo: previstas, comprovadas, pendentes e percentuais; reexportação já substituída e publicada em `dc65246` | **262** (rodapé), sem os filtros de status anteriores | 586 |
| `auditoria-tabela-contatos.xlsx` | 37.073 contatos: nome, email, função/perfil e hierarquia | sem filtro semestral (não é dado de ciclo) | 2.336 |
| `auditoria-vereditos-262.xlsx` | 738 linhas de critérios/considerações de laboratório | **262** (coluna) | 89 |

**Evidência de que o dado é novo:** na base 261 antiga, Mauá VII (16219265) somava 3 reprovados e Mauá I (1121) aparecia sem reprovações; agora Mauá I tem **3 reprovados / 1 sem retorno** e Mauá VII **0/0**. Os valores de fato mudaram de ciclo.

## Cobertura por campo

| Campo/dado | Uso na prévia | Nova fonte | Status | Ressalva |
|---|---|---|---|---|
| `nome_polo` | Todas as tabelas | Todos os arquivos (`Polo`) | **Coberto (262)** | — |
| `ID_polo / chave_polo` | Junção entre bases | `tabela-contatos` e `timeline` trazem `ID polo` explícito | **Coberto (262)** | Chave numérica entre parênteses deixa de ser a única forma de junção; ID oficial disponível |
| Carteira por gestor (`nome_gestor`, `qtd_polos`, recorte) | Identificação e agrupamento do consolidado | `tabela-contatos` — linhas com Perfil **GESTOR PRINCIPAL** | **Coberto** | r2: 1.428 polos têm mais de um gestor principal; r3: GO com valores "TBD" |
| `email_destinatario` | Seleção/agrupamento (prévia não envia) | `tabela-contatos` — E-mail do GESTOR PRINCIPAL | **Coberto** | Nenhum gestor principal sem e-mail nas linhas verificadas |
| `gerente_operacional / comercial / diretor / regional` | Contexto hierárquico | `tabela-contatos` (colunas próprias) | **Coberto com ressalva** | r3 |
| Práticas `previstas / comprovadas / pendentes / %` | Bloco COMPROVAÇÃO DE AULAS PRÁTICAS | `apps-prazo` (reexportado em 10/11) | **Coberto (262)** | r1 resolvido: nova exportação sem filtro de status, 586 polos, 63.842 pendências; Mauá I 60/0/60, Mauá VII 96/0/96 e Santos 30/0/30 **iguais ao sample de referência** |
| Separação por sequência (1–4) | Texto de prazo do consolidado | `apps-prazo` consolidado em arquivo único | **Coberto** | Não há mais coluna de sequência; os totais já vêm agregados por polo. A menção "sequência 2" ao prazo permanece texto manual |
| Agenda de laboratórios (`tipo`, `ambiente`, `data`, `status`, `auditor`) | Bloco AGENDA DE AUDITORIAS | `timeline` (Agendada/Realizada/Finalizada + datas) | **Coberto (262)** | Datas 12/08/2026 a 15/12/2026 (ciclo corrente). r4: exportação filtrada para 6 auditores da acadêmica |
| Parecer de laboratório | Bloco RESULTADO — AUDITORIA DE LABORATÓRIOS | `timeline` (`Parecer Auditoria`) | **Coberto (262)** | 1.159 Reprovado / 540 Aprovado / 63 Pendente |
| `qtd_laboratorios_por_status` | Contagens e alertas do consolidado | `acompanhamento` e `timeline` | **Coberto (262)** | — |
| Indicador `Rep. Sem Retorno` | Alerta do consolidado | `acompanhamento` (coluna própria, 246 no total) | **Coberto (262)** | Continua distinto da contagem de Reprovados (628) — métricas separadas, como já registrado |
| Pendências e considerações do auditor | Enriquecimento futuro de pendências por laboratório | `vereditos` (`pendencia_macro`, `consideracoes_auditor`, `observacoes`, `critico`) | **Coberto com ressalva** | r5: 89 polos com detalhamento por critério/laboratório; a timeline tem 460 polos operacionais. Confirmado pelo usuário: **não** alimenta checklist |
| Checklist CL 2026 — `nota_checklist` | Bloco CHECKLIST DE INFRAESTRUTURA | **Não existe em nenhum arquivo** | **Base suplementar necessária** | Sem nota numérica (ex.: 69,94) em qualquer fonte. Origem outra, confirmada pelo usuário |
| Checklist CL 2026 — `status / prazo / data_envio / auditor do checklist` | Bloco CHECKLIST DE INFRAESTRUTURA | **Não existe em nenhum arquivo** | **Base suplementar necessária** | Concluído/Não realizado, "Enviado em", prazo por polo e auditor do checklist seguem sem fonte |
| `prazo_praticas / prazo_auditorias` (prazos gerais do ciclo) | Caixa PRAZOS GERAIS | — | **Manual (fixo)** | Nenhum arquivo traz prazo; permanece campo manual do formulário, sem reaproveitar 04/10 e 06/10 do exemplo |
| Links do relatório e atendimento | Rodapé de links | — | **Manual (fixo do modelo)** | Conteúdo institucional, não é dado por polo |
| Contatos internos do rodapé (nome/e-mail do time de auditoria) | Bloco Dúvidas | — | **Manual (fixo)** | `tabela-contatos` traz contatos **dos polos**, não do time interno Kroton |
| `telefone_contato` | Rodapé Dúvidas do consolidado | — | **Manual** | Contato interno fixo, não dado por polo; não exige base suplementar |
| Ciclo real das fontes (metadado) | Aviso de origem no HTML | Rodapés "Applied filters" + colunas `semestre_operacional` | **Coberto (262)** | Rodapés vieram em inglês ("Applied filters") — leitores precisam aceitar os dois idiomas |

## Ressalvas de qualidade de dados

- **r1 — apps-prazo pré-filtrado (RESOLVIDO):** a primeira exportação vinha com `status_comprovacao is Comprovada`. A reexportação recebida em 10/11 declara apenas `semestre_operacional is 262` + `canal is PARCEIRO`: 586 polos sem duplicatas, 86.752 previstas / 22.910 comprovadas / 63.842 pendentes, 583 polos com pendência. Substituição publicada em `dc65246`. Os três polos do sample de referência batem valor a valor. Ausência de registro em uma fonte não certifica ausência de auditoria ou zero práticas; a prévia mantém essa distinção.
- **r2 — mais de um gestor principal:** o polo pode permanecer nas carteiras dos gestores associados. O usuário confirmou planilha intermediária por polo com todos os emails distintos de Perfil GESTOR PRINCIPAL concatenados com `;`, sem selecionar o primeiro. Recorte da carteira: polos presentes em timeline, apps ou acompanhamento. Nomes potencialmente ambíguos são sinalizados para revisão; email compartilhado não funde pessoas distintas.
- **r3 — hierarquia com placeholder:** `Gerente Operacional` contém valores "TBD - NOME" (ex.: "TBD - ADIEL MARTINS"). Não usar essa coluna para agrupar sem tratar os TBD.
- **r4 — timeline filtrada por auditores:** a exportação inclui 6 auditores da auditoria acadêmica (um com nome em branco no rodapé). Se o recorte for "toda a auditoria acadêmica", validar se não há outros auditores fora do filtro.
- **r5 — vereditos com cobertura parcial:** 89 polos operacionais e 738 linhas, excluído o rodapé da contagem de polos. É fonte futura de pendências/considerações onde existir; ausência não é "sem pendência" e não alimenta o checklist.
- **r6 — codificação:** valores de `Função` exibem mojibake ("LIDERANÃ‡A"). Não impede uso (Perfil é o campo-chave), mas normalizar acentuação se for exibir.

## Veredicto

**A pasta `databases/09-11-26` substitui as fontes atuais na quase totalidade** — Master (carteira/contatos), sequências (práticas), labs (agenda/pareceres) e aprovação (indicadores) deixam de ser necessárias após a migração. Faltam três pontos:

1. ~~Reexportação do `apps-prazo`~~ **concluída** em 10/11: práticas agora cobertas com pendências reais e valores conferidos contra o sample.
2. **Base suplementar para o bloco CHECKLIST DE INFRAESTRUTURA (CL 2026)** — nota numérica, status, prazo, data de envio e auditor do checklist não existem em nenhum dos cinco arquivos; o usuário confirmou que a origem é outra. Enquanto não chegar, o bloco permanece com preenchimento manual no formulário.
3. **Itens fixos/manuais:** prazos gerais do ciclo, links institucionais e contatos internos do rodapé, incluindo telefone manual quando necessário.

Nenhuma outra base suplementar foi identificada como necessária para os blocos de agenda, resultados de laboratório, práticas, carteira, contatos por polo e indicadores.
