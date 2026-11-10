# CCAA — somente campos faltantes, divergentes ou omitidos

## Versão e critério

Análise da última versão remota confirmada: **`05883137d26dd678299a4d942dbc3f0bf46bcd11`**.

O pull no diretório principal foi bloqueado por alterações locais em `testes/preview_server.py`. Elas foram preservadas, sem stash/reset. A revisão foi feita em checkout isolado dessa revisão, com `git pull --ff-only origin main` concluído e árvore limpa. **O diretório principal não foi mesclado/atualizado para essa revisão.** Este relatório foi salvo no diretório principal apenas como documentação.

O `sample.html` **já participava do catálogo anterior**, sob o nome SITUACAO. A conferência agora abrangeu as demais amostras, incluindo as duas versões Mari; ela encontrou omissões e contagens que precisam de correção.

Esta tabela contém **31 itens filtrados**: faltas de fonte operacional, divergências entre fonte/amostra/renderer e omissões/agrupamentos incorretos no catálogo anterior. Itens sem diferença foram excluídos. Uma diferença não significa automaticamente erro: pode ser outro snapshot, modelo demonstrativo ou métrica distinta.

- **Sim:** existe fonte local, regra de cálculo ou conteúdo fixo para a finalidade indicada, mas a descrição pode apontar cobertura, composição ou ciclo incompatíveis.
- **Não:** falta fonte operacional correspondente ou preparação para a finalidade indicada. Exemplos fixos não suprem dados por polo. Itens opcionais e condicionais estão identificados; não são todos bloqueios das páginas atuais.
- **Quantidade:** fluxos distintos em que o campo/conceito participa do modelo considerado, não quantidade de aparições ou registros. Uma divergência pode afetar apenas um dos fluxos listados.
- Nome de campo é um rótulo conceitual, não proposta de criar coluna ou função. MAIL inclui corpo padrão e regras/índice de prévia, pois o catálogo anterior também contava seleção/agrupamento; seus metadados não são confundidos com conteúdo do email.

## Fluxos na versão remota

| Sigla | Pasta em `fluxos/` |
|---|---|
| AGENDA | `AGENDA_SEMANAL_AUDITORIAS` |
| ACADEMICA | `AGENDA_REGULARIZACAO_AUDITORIA_ACADEMICA` |
| FAST_TRACK | `AGENDA_FAST_TRACK_INFRA_2026` |
| MAIL | `MAIL` |
| CONSOLIDADO | `AGENDA_AUDITORIA_E_SITUACAO_REGULARIZACAO_DOS_POLOS` |

## Tabela simplificada — somente exceções

| Nome do campo/dado | Temos para consulta? | Qtd. de fluxos em que aparece | Descrição de como afeta o preview / divergência |
|---|---|---:|---|
| `nota_checklist` | Não | 1 | **CONSOLIDADO — Faltante:** O sample exibe 69,94, mas NOTA FINAL do candidato Fast Track está vazia em todas as linhas. Valor isolado da amostra não permite consultar os demais polos. |
| `status_checklist` | Não | 1 | **CONSOLIDADO — Faltante:** Concluído/Não realizado no sample; PREENCHEU CL e VALIDADO estão vazios na fonte candidata. Não inferir status apenas por nota ausente. |
| `data_envio_checklist` | Não | 1 | **CONSOLIDADO — Faltante:** Não foi localizada fonte equivalente a Enviado em 21/09/2026 por polo. DATA CL no controle MEC não comprova data de envio. |
| `prazo_checklist / observacao_checklist` | Não | 1 | **CONSOLIDADO — Faltante:** Há prazo por polo e coluna de observação no sample, sem base operacional/regra correspondente para variar esses valores. Observação livre não estava discriminada no catálogo. |
| `ciclo_referencia` | Sim | 1 | **CONSOLIDADO — Divergente:** O sample está em 26.2; as quatro sequências e labs/aprovacao indicam 261. Os dados existem, mas não reproduzem aquele snapshot apenas mudando o título. |
| `qtd_polos / recorte_carteira` | Sim | 3 | **AGENDA, MAIL, CONSOLIDADO — Divergente:** O sample informa quatro polos; a Master possui 6 unidades PARCEIRO em OPERAÇÃO/CAPTAÇÃO para o mesmo gestor. Falta definir o recorte; presença de cadastro não confirma a carteira do comunicado. |
| `ID_polo / chave_polo` | Sim | 3 | **AGENDA, ACADEMICA, CONSOLIDADO — Divergente:** Código do nome e ID COLABORAR não são intercambiáveis: no exemplo de Mauá I, 1121 no nome corresponde a ID 15251646 na Master. Precisa do de-para e da regra de seleção do cadastro. |
| `aulas_previstas / aulas_pendentes / totais_carteira` | Sim | 2 | **ACADEMICA, CONSOLIDADO — Divergente:** Nos três polos da tabela de práticas, fontes somam 148 previstas contra 186 no sample. Mauá I é 48 versus 60; Mauá VII 72 versus 96; Santos III 28 versus 30. Falta snapshot/regra compatível, não coluna. |
| `nome_laboratorio / cobertura_ambientes` | Sim | 2 | **ACADEMICA, CONSOLIDADO — Divergente:** O sample agenda três ambientes em Mauá I, mas labs contém dois. O resultado exibe Multidisciplinar de Santos III, sem linha correspondente nessa fonte. Não confundir registro ausente com laboratório aprovado/sem pendência. |
| `data_auditoria` | Sim | 2 | **AGENDA, CONSOLIDADO — Divergente:** Mauá I aparece A marcar na agenda do sample, enquanto labs tem datas em maio de 2026. Datas existem, mas não são o mesmo retrato; confirmar fonte e ciclo. |
| `status_agendamento / realizacao` | Sim | 1 | **CONSOLIDADO — Divergente:** Agendada/Realizada/Finalizada existem separadamente. É necessário definir a regra para A marcar ou reprovado/não compareceu, em vez de tratar data passada como prova de ausência. |
| `tipo_auditoria` | Sim | 1 | **CONSOLIDADO — Divergente:** O sample usa Laboratório, enquanto Tipo auditoria da fonte usa Regular. São classificações diferentes; não preencher uma diretamente com a outra sem regra. |
| `nome_auditor / vinculo_polo_funcao` | Sim | 1 | **CONSOLIDADO — Divergente:** Há auditor no labs e consultores de infraestrutura/GO na Master, mas os responsáveis da agenda do sample diferem do snapshot. Atribuição de auditor de checklist e papel de atendimento precisa ser confirmada; não faltam todos os nomes. |
| `qtd_reprovados_sem_retorno` | Sim | 1 | **CONSOLIDADO — Divergente:** O campo Rep. Sem Retorno existe; os quatro polos do sample somam 2 na fonte contra cinco no aviso. Seis linhas Reprovado no HTML não significam erro nesse aviso: são métricas distintas; confirmar snapshot e critérios. |
| `orientacao_laboratorio / o_que_falta_para_aprovar` | Sim | 1 | **ACADEMICA — Omissão no catálogo:** Não estava discriminado. O renderer gera uma orientação genérica por parecer (regularizado, regularizar pendências, agendar ou aguardar). Não existe diagnóstico detalhado por item nessa regra; não prometer esse detalhe. |
| `pendencia_descricao` | Não | 1 | **MAIL — Faltante:** O modelo tem pendências de exemplo, não uma lista operacional pronta por polo. Observações de infraestrutura nas bases Fast Track não viram automaticamente a lista do MAIL. |
| `grupo_economico_nome / qtd_unidades_grupo` | Sim | 1 | **AGENDA — Divergência semântica:** O catálogo juntava nome e quantidade. preview_modelo exibe nomes; preview_layout_novo e os 48 registros salvos usam quantidade (CI), sob o título Grupo Econômico. O .bas novo busca o nome (CH), mas o VBA embutido/renderer continuam com o valor salvo. |
| `hora_auditoria` | Sim | 1 | **AGENDA — Omissão no catálogo / saída:** Há horário diferente de zero em 17 datas da agenda, 13 delas elegíveis. O catálogo não o separava e o renderer mostra somente o dia. Não é falta de fonte; meia-noite nos demais registros não comprova horário definido. |
| `papel_gerente_GO_ou_GN` | Sim | 1 | **AGENDA — Divergência de versão:** GO está disponível, mas o .bas novo prioriza gerente de negócios e a base Agenda não tem os cabeçalhos GN esperados. O VBA embutido usa GO e o cabeçalho segue dizendo GO. Nomes GN em planilhas Fast Track não comprovam a carteira da agenda. |
| `apelidos_contatos_gerente` | Não | 1 | **AGENDA — Faltante condicional:** O .bas novo prevê a aba Apelidos para correspondência alternativa de nomes; ela não existe no XLSM. Só é lacuna caso essa preparação alternativa seja adotada, não um requisito adicional do HTML atual. |
| `indice_linha / ordem_data` | Sim | 1 | **AGENDA — Omissão / divergência de saída:** A coluna # do layout novo é índice calculado, não número de sequência acadêmica. A mensagem promete ordem de data, mas o renderer preserva a ordem da planilha: há grupo que sai 11/09, 08/09, 11/09. |
| `preheader_agenda / proxima_auditoria` | Sim | 1 | **AGENDA — Divergência entre modelos:** O layout novo tem preheader com período e Próxima; o modelo antigo não mostra Próxima. O renderer calcula contagem + Próxima, sem o mesmo trecho de período. São diferenças de composição, não de disponibilidade de datas. |
| `dados_operacionais_da_amostra_agenda` | Não | 1 | **AGENDA — Faltante para reprodução exata:** Os cinco polos do preview_modelo não estão na agenda salva. No layout novo, as cinco linhas principais correspondem a um grupo, mas as duas linhas adicionais são demonstrativas; não somar sete auditorias nem assumir que exemplos são registros reais. |
| `links_referencia / atendimento` | Sim | 4 | **AGENDA, ACADEMICA, FAST_TRACK, CONSOLIDADO — Contagem anterior incorreta:** Correção: quatro fluxos, não cinco. O MAIL padrão não contém href/link; seu endereço de atendimento é texto. Rascunhos personalizados podem mudar isso, mas não foram presumidos. |
| `area_atendimento / email_atendimento` | Sim | 2 | **MAIL, CONSOLIDADO — Omissão / agrupamento incorreto:** O MAIL também tem área de dúvidas e email institucional fixo: presença em dois fluxos, não apenas no consolidado. Não estender essa contagem a nome de pessoa ou telefone, que o MAIL padrão não fornece. |
| `assunto_email_MAIL` | Sim | 1 | **MAIL — Omissão no catálogo — seleção/índice:** Assunto participa do agrupamento e aparece no índice da prévia. Há precedência coluna → CONFIG → rascunho. Não é o título visível do corpo; o modelo escolhido ainda precisa ser preparado. |
| `modelo_email_selecionado / ID_modelo` | Não | 1 | **MAIL — Faltante para executar a reprodução genérica:** A identificação do rascunho Outlook está vazia no XLSM recebido. O HTML de exemplo não prova que o modelo editável esteja selecionado. Isso não impede abrir o exemplo como estático. |
| `selecao_enviar / status_linha` | Sim | 1 | **MAIL — Omissão no catálogo — seleção:** As regras existem e afetam quem entra na prévia: vazio em Enviar? é incluído; N e Status Enviado são pulados. Estavam fora da tabela apesar do critério incluir seleção; vazio é um estado permitido, não ausência obrigatória de dado. |
| `CC / CCO_do_indice` | Não | 1 | **MAIL — Omissão no catálogo — metadados opcionais:** O índice da prévia mostra CC/CCO, mas os valores estão vazios na planilha/configuração recebida. São opcionais e não aparecem no corpo; não existe obrigação de preenchê-los para o modelo estático. |
| `qtd_linhas / qtd_emails / data_geracao / situacao_previa` | Sim | 1 | **MAIL — Omissão no catálogo — derivados do índice:** O índice calcula esses metadados. Linhas não equivale a polos distintos; data/hora de geração não é a data de referência de Mari; Situação pode conter erro de preparação. Não são novas colunas a fornecer no corpo. |
| `anexo_caminho` | Não | 1 | **MAIL — Omissão no catálogo — validação opcional:** Estrutura existe, mas não há anexos preenchidos. Se um caminho for informado e não existir, a prévia recebe erro. Não há coluna Anexos no índice nem anexo exigido pelo sample; não confundir com falta de conteúdo do corpo. |

## Cobertura das amostras e evidências

Foram inventariados **35 arquivos nas cinco pastas**; isso não é certificação de execução dos aplicativos. Amostras de email examinadas:

| Fluxo | Amostra / fonte de conteúdo examinada |
|---|---|
| CONSOLIDADO | `sample.html` completo: checklist, agenda, aulas, pareceres, prazos e contatos; confrontado com Master, sequências, labs e aprovação. |
| AGENDA | `preview_modelo.html` **e** `preview_layout_novo.html`; XLSM salvo, VBA embutido/exportado e `testes/preview_mari.py`. |
| ACADEMICA | Não há HTML de prévia salvo nessa pasta remota. Foram examinados o renderer em `disparar_emails.py`, leitores e planilhas; a coluna O que falta para aprovar estava fora do catálogo detalhado. |
| MAIL | `EXEMPLO - prévia do e-mail.html`, modelo VBA, regras/índice de prévias, XLSM e fontes da Master. O sample é fictício e não coincide integralmente com a planilha salva. |
| FAST_TRACK | Duas páginas de `exemplo_email.pdf` e três bases candidatas; o corpo estático não ganhou novos campos variáveis faltantes. |

**Distinções que não devem virar falsos faltantes:**

- Na nova amostra Mari, as duas linhas demonstrativas de estados não integram as cinco auditorias principais.
- No consolidado, seis pareceres Reprovado e aviso de cinco sem retorno são métricas diferentes. A fonte disponível é de outro snapshot.
- Em FAST_TRACK, assunto com unidade e De/Data/Para/Cc são impressão Outlook, não campos do corpo estático. O prazo 31/08 e mínimo 3,0 são conteúdo fixo histórico já consultável; não exigem planilhas.
- O HTML local `FAST_TRACK_INFRA_2026/modelo_email.html` citado no catálogo anterior **não está nessa revisão remota**. A fonte remota é o PDF na pasta renomeada. Não se afirma ausência do arquivo local nem que as bases Fast Track já alimentem um renderer.
- Os três arquivos de `AGENDA_SEMANAL_AUDITORIAS/prints/` são material WhatsApp, apenas inventariado e excluído do escopo email conforme orientação anterior.
- Nome da pasta começar com AGENDA não transforma automaticamente todo campo de data/status em requisito do seu modelo.

### Referências por grupo de achados

- **Consolidado:** `sample.html:24–41,61–92,130`; `labs.xlsx/Export`; `aprovacao.xlsx/Export`; quatro planilhas de sequência/Export; Master/BASE_DE_UNIDADES. Exemplo de diferença de identificador: 1121 no nome de Mauá I corresponde ao ID COLABORAR 15251646 na Master.
- **Checklist:** `AGENDA_FAST_TRACK_INFRA_2026/AÇÕES_ENFERMAGEM_PRESENCIAL_2026_1.xlsx`, `Planilha1!F:H`, vazios inclusive sem `data_only`; controle MEC tem DATA CL, que não prova data de envio.
- **Agenda:** `preview_modelo.html:38–40`; `preview_layout_novo.html:13–15,73–159`; `Modulo2_NOVO.bas:81–85,140–178`; valores salvos de `Aba de auditorias!C:D`; `Base_polos!CH:CI`. Confronto dos 48 registros confirmou C igual a CI; exportado e embutido não são intercambiáveis.
- **Acadêmica:** `disparar_emails.py:341–350,369–401` para orientação por parecer; notas de filtro das quatro sequências e `semestre_operacional_x` de labs identificam 261.
- **MAIL:** `modDisparo.bas:222–269` (agrupamento/seleção), `330–343` (assunto/modelo/anexos), `405–451` (corpo padrão sem hyperlinks), `459–494` (índice). O suporte está em texto em `439–443`, sem pessoa/telefone.

## O que esta revisão não fez

Não alterou geradores, dados, macros, regras de negócio ou o catálogo anterior; não executou refresh, Outlook ou envio e não fez commit/push. Os achados de disponibilidade não certificam atualização da carteira nem renderização em clientes de email. A mesclagem do diretório principal continua pendente por conflito com as alterações locais.
