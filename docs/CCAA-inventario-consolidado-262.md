# CCAA — Inventário consolidado de dados

Situação de consulta e atualização das informações utilizadas nas prévias de email. Semestre de referência solicitado: 262 (26.2).

AGENDA: agenda semanal de auditorias; ACADEMICA: regularização da auditoria acadêmica; FAST_TRACK: infraestrutura 2026; MAIL: disparador genérico; CONSOLIDADO: agenda e situação de regularização dos polos.

| Nome do campo/dado | Temos para consulta? | Atualizado para o semestre atual 262? | Qtd. de fluxos em que se repete | Descrição de como afeta o preview |
|---|---|---|---:|---|
| `nome_polo` | Sim | Não confirmado | 4 | AGENDA, ACADEMICA, MAIL, CONSOLIDADO — Identifica os polos nas tabelas e na prévia individual. O cadastro disponível não confirma atualização da carteira para 262. |
| `ID_polo / chave_polo` | Sim | Não confirmado | 3 | AGENDA, ACADEMICA, CONSOLIDADO — Relaciona cadastros e resultados. Código no nome e ID COLABORAR podem diferir; é necessário validar o de-para e o cadastro selecionado. |
| `nome_gestor` | Sim | Não confirmado | 2 | MAIL, CONSOLIDADO — Personaliza a identificação e a saudação. Não equivale ao gerente operacional; o recorte da carteira requer confirmação. |
| `nome_gerente_operacional` | Sim | Não confirmado | 1 | AGENDA — Preenche identificação e saudação da agenda. A versão alternativa prioriza gerente de negócios, mas o arquivo salvo e o título usam GO. |
| `nome_gerente_negocios_agenda` | Não | Não | 1 | AGENDA — A preparação alternativa prevê GN, mas os cabeçalhos correspondentes não existem na base da agenda. Dados Fast Track não comprovam essa carteira; não é requisito do HTML atual. |
| `email_destinatario` | Sim | Não confirmado | 2 | AGENDA, MAIL — Participa do agrupamento e da seleção; no MAIL também aparece no índice. O cadastro necessita validação, sem envio para gerar o corpo HTML. |
| `qtd_polos / recorte_carteira` | Sim | Não confirmado | 3 | AGENDA, MAIL, CONSOLIDADO — Compõe o resumo da carteira. A agenda conta linhas e o MAIL, polos distintos; o consolidado mostra quatro polos, contra seis elegíveis na Master consultada. |
| `grupo_economico_nome` | Sim | Não confirmado | 1 | AGENDA — Deveria exibir o nome do grupo. A fonte possui esse nome, mas os valores salvos e o gerador ainda utilizam quantidade sob o título Grupo Econômico. |
| `qtd_unidades_grupo` | Sim | Não confirmado | 1 | AGENDA — É a quantidade de unidades, não o nome do grupo. Os 48 valores salvos examinados correspondem à coluna de quantidade; os conceitos precisam permanecer separados. |
| `data_auditoria` | Sim | Não confirmado | 2 | AGENDA, CONSOLIDADO — Mostra a data e os avisos da agenda. Há diferenças entre o exemplo e as datas de maio de 2026 na fonte; a correspondência com 262 não foi comprovada. |
| `hora_auditoria` | Sim | Não confirmado | 1 | AGENDA — Há horário não zero em 17 datas, 13 elegíveis, mas a prévia mostra apenas o dia. Meia-noite nos demais registros não comprova horário operacional definido. |
| `data_referencia` | Sim | Não se aplica | 1 | AGENDA — Controla os avisos de data passada e dia da semana sem alterar as datas das auditorias. É parâmetro do teste, não dado de um semestre. |
| `periodo_auditorias` | Sim | Não confirmado | 1 | AGENDA — Resume a menor e a maior data do grupo; sua atualização depende das datas e do recorte da carteira utilizados. |
| `proxima_auditoria / preheader_agenda` | Sim | Não confirmado | 1 | AGENDA — Compõe o texto inicial da agenda. As versões diferem no uso do período; a lógica atual chama de próxima a menor data, mesmo passada. |
| `indice_linha / ordem_apresentacao` | Sim | Não se aplica | 1 | AGENDA — Numera as linhas; não é a sequência acadêmica. A mensagem promete ordem cronológica, mas o gerador preserva a ordem da planilha. |
| `nome_laboratorio / ambiente` | Sim | Não | 2 | ACADEMICA, CONSOLIDADO — Identifica ambientes e resultados. A base está em 261 e não cobre todas as linhas do exemplo 262: há diferenças de quantidade e ambientes ausentes. |
| `parecer_laboratorio` | Sim | Não | 2 | ACADEMICA, CONSOLIDADO — Exibe aprovação, reprovação ou pendência e define os destaques. Os pareceres disponíveis são do conjunto identificado como 261. |
| `qtd_laboratorios_por_status` | Sim | Não | 2 | ACADEMICA, CONSOLIDADO — Gera contagens e alertas. O cálculo depende dos registros, do filtro e do ciclo; os critérios entre os modelos não são automaticamente iguais. |
| `tipo_auditoria` | Sim | Não | 1 | CONSOLIDADO — Preenche o tipo na agenda consolidada. O exemplo usa Laboratório, enquanto a fonte 261 usa Regular; é preciso definir a equivalência, não copiar diretamente. |
| `nome_auditor / vinculo_polo_funcao` | Sim | Não confirmado | 1 | CONSOLIDADO — Identifica responsáveis no checklist e na agenda. Existem nomes nas fontes, mas os vínculos e papéis não comprovam os responsáveis do exemplo 262. |
| `status_agendamento / realizacao` | Sim | Não | 1 | CONSOLIDADO — Determina A marcar e outros avisos. Agendada, Realizada e Finalizada são estados distintos da fonte 261; data passada não prova não comparecimento. |
| `qtd_reprovados_sem_retorno` | Sim | Não | 1 | CONSOLIDADO — Preenche o aviso específico. Os polos examinados somam dois na fonte 261, contra cinco no exemplo; não equivale a contar todos os pareceres Reprovado. |
| `orientacao_laboratorio` | Sim | Não se aplica | 1 | ACADEMICA — É uma regra textual por parecer: regularizado, regularizar, agendar ou aguardar. Não fornece diagnóstico detalhado por item; a saída depende do parecer utilizado. |
| `numero_sequencia` | Sim | Não | 1 | ACADEMICA — Identifica as sequências das práticas. As quatro exportações disponíveis estão marcadas como 261; não há comprovação equivalente para 262. |
| `aulas_previstas` | Sim | Não | 2 | ACADEMICA, CONSOLIDADO — Mostra a quantidade esperada. Os valores 261 divergem do exemplo 262: em Mauá I, 48 previstas na soma das fontes contra 60 no exemplo. |
| `aulas_comprovadas` | Sim | Não | 2 | ACADEMICA, CONSOLIDADO — Mostra o que foi comprovado e participa do percentual. Os valores consultados pertencem às exportações 261, não a uma atualização comprovada para 262. |
| `aulas_pendentes` | Sim | Não | 2 | ACADEMICA, CONSOLIDADO — Mostra o que falta comprovar. A fonte 261 não reproduz os valores do exemplo; pendência importada não deve ser substituída silenciosamente por outro cálculo. |
| `percentual_comprovacao` | Sim | Não | 2 | ACADEMICA, CONSOLIDADO — Relaciona comprovadas e previstas e altera a sinalização visual. Embora calculável, o resultado continua dependente das bases 261. |
| `totais_praticas` | Sim | Não | 2 | ACADEMICA, CONSOLIDADO — Resume práticas por polo ou carteira. Nos três polos do exemplo, as fontes somam 148 previstas contra 186; confirmar ciclo, cobertura e sequências incluídas. |
| `ciclo_referencia` | Sim | Não | 1 | CONSOLIDADO — Identifica o ciclo do comunicado. O exemplo informa 26.2/262, mas práticas e laboratórios disponíveis indicam 261; mudar o rótulo não atualiza os dados. |
| `nota_checklist` | Não | Não | 1 | CONSOLIDADO — Preenche a nota CL 2026. A coluna candidata está vazia; a nota 69,94 isolada no exemplo não constitui base consultável para os demais polos. |
| `status_checklist` | Não | Não | 1 | CONSOLIDADO — Exibe Concluído ou Não realizado. As colunas candidatas de preenchimento e validação estão vazias; não inferir o status apenas por nota ausente. |
| `data_envio_checklist` | Não | Não | 1 | CONSOLIDADO — Preenche a observação Enviado em. Não foi localizada fonte operacional equivalente; DATA CL não comprova data de envio. |
| `prazo_checklist` | Não | Não | 1 | CONSOLIDADO — Mostra o prazo por polo quando houver pendência. Falta fonte ou regra operacional para variar o prazo do exemplo entre os polos. |
| `observacao_checklist` | Não | Não | 1 | CONSOLIDADO — Complementa o prazo ou a situação na coluna de observação. Falta fonte operacional para esse conteúdo por polo, além dos textos isolados do exemplo. |
| `pendencia_descricao` | Não | Não | 1 | MAIL — Preenche a pendência por polo. O MAIL tem textos fictícios de exemplo, não uma lista operacional; observações Fast Track não substituem automaticamente essa lista. |
| `prazo_regularizacao` | Sim | Não confirmado | 4 | ACADEMICA, FAST_TRACK, MAIL, CONSOLIDADO — Exibe datas-limite. Os modelos têm prazos fixos, históricos ou fictícios; o prazo Fast Track de 31/08 não comprova uma configuração vigente para 262. |
| `nota_minima_MEC` | Sim | Não se aplica | 1 | FAST_TRACK — Exibe o parâmetro fixo 3,0 do exemplo, não a nota obtida por um polo. O valor não foi revalidado como orientação normativa nesta consolidação. |
| `nome_contato / telefone_contato` | Sim | Não confirmado | 1 | CONSOLIDADO — Compõe o atendimento por pessoa. Os cadastros existem, mas os responsáveis e meios de contato da carteira 262 precisam de confirmação. |
| `area_atendimento / email_atendimento` | Sim | Não confirmado | 2 | MAIL, CONSOLIDADO — Compõe o suporte: no MAIL há área e email institucional fixos; no consolidado há funções e responsáveis. MAIL não fornece nome de pessoa ou telefone nesse trecho. |
| `links_referencia / atendimento` | Sim | Não confirmado | 4 | AGENDA, ACADEMICA, FAST_TRACK, CONSOLIDADO — Dá acesso a agenda, relatórios, book e atendimento. São quatro fluxos: o MAIL padrão tem endereço em texto, sem hyperlink. Destinos e conteúdo 262 não foram revalidados. |
| `textos_institucionais / titulo / assinatura` | Sim | Não se aplica | 5 | AGENDA, ACADEMICA, FAST_TRACK, MAIL, CONSOLIDADO — Define orientações, títulos e fechamento. São conteúdo do modelo; o MAIL pode usar rascunho personalizado. Referências temporais devem seguir os campos específicos. |
| `estilo_email` | Sim | Não se aplica | 5 | AGENDA, ACADEMICA, FAST_TRACK, MAIL, CONSOLIDADO — Define fontes, cores, hierarquia e tabelas; não é uma atualização semestral de dados. A referência visual futura permanece LIRA. |
| `apelidos_contatos_gerente` | Não | Não se aplica | 1 | AGENDA — A preparação alternativa prevê uma aba Apelidos, ausente no arquivo. É uma dependência condicional de correspondência de nomes, não exigência do corpo atual. |
| `assunto_email_MAIL` | Sim | Não confirmado | 1 | MAIL — Participa do agrupamento e do índice. A precedência é coluna, configuração e rascunho; não equivale ao título do corpo e não há preparação 262 comprovada. |
| `modelo_email_selecionado / ID_modelo` | Não | Não confirmado | 1 | MAIL — Identifica o rascunho editável do Outlook; está vazio na planilha recebida. Impede comprovar essa reprodução genérica, mas não impede abrir o HTML estático. |
| `selecao_enviar / status_linha` | Sim | Não confirmado | 1 | MAIL — Controla quais linhas entram na prévia. Vazio em Enviar? é incluído; N e Status Enviado são pulados. A regra existe, mas não comprova seleção operacional 262. |
| `CC / CCO_do_indice` | Não | Não confirmado | 1 | MAIL — São cópias opcionais mostradas no índice, não no corpo. Os valores estão vazios na configuração recebida; não são obrigatórios para o modelo estático. |
| `qtd_linhas / qtd_emails / data_geracao / situacao_previa` | Sim | Não se aplica | 1 | MAIL — São metadados calculados do índice. Linhas não equivale a polos distintos; data de geração não é data de referência da agenda; Situação pode indicar erro de preparação. |
| `anexo_caminho` | Não | Não confirmado | 1 | MAIL — É opcional e está vazio na planilha recebida. Caminho informado que não existir causa erro de preparação; o exemplo não exige anexo nem o exibe no corpo. |

## Ressalvas

- Sim em consulta indica fonte local preenchida, cálculo possível ou conteúdo fixo disponível; não garante cobertura de todos os polos nem atualização para 262.
- Na coluna 262: Não indica fonte ausente ou identificada como 261; Não confirmado indica falta de evidência de atualização; Não se aplica identifica regra, formatação ou metadado sem ciclo próprio. Nenhum dado foi certificado como atualizado para 262 apenas porque o exemplo menciona 26.2.
- Campos calculados dependem de seus dados de origem. Uma regra sem ciclo próprio não torna atualizados seus resultados; não é possível corrigir o semestre apenas trocando o título.
- Gestor de polo, gerente operacional e gerente de negócios são papéis diferentes. Código no nome do polo e ID COLABORAR não são necessariamente o mesmo identificador; nome do grupo econômico não é quantidade de unidades.
- A carteira do consolidado e os filtros precisam de confirmação: o exemplo mostra quatro polos, enquanto a Master consultada tem seis elegíveis. Exemplos fixos ou fictícios não substituem uma base operacional.
- Os cinco polos do modelo antigo de agenda não constam da agenda salva. No layout novo, duas linhas adicionais são demonstrativas e não integram as cinco auditorias principais. A ordenação cronológica anunciada não é aplicada pelo gerador atual.
- Seis linhas Reprovado e cinco reprovados sem retorno não representam necessariamente erro: são métricas distintas. Agendada, Realizada e Finalizada também não devem ser tratadas como sinônimos.
- MAIL considera corpo padrão, seleção e índice; destinatários, cópias, assunto e anexos não são novos campos obrigatórios do corpo. Cópias e anexos são opcionais; a aba Apelidos só é pertinente à preparação alternativa.
- O consolidado foi contado pela estrutura da amostra, sem presumir gerador dinâmico implementado. Fast Track permanece estático, sem leitura de planilhas; De, Para, Cc e assunto na impressão Outlook não integram seu corpo.
- Links e contatos constam dos modelos ou cadastros, mas não foram revalidados. Prazos históricos, exemplos e o parâmetro fixo do modelo não comprovam vigência para uma nova rodada.
- Esta síntese consolida os dois documentos fornecidos, com as correções de contagem e disponibilidade. Não houve nova atualização das bases, execução de macros, envio de emails ou validação em clientes de email.
