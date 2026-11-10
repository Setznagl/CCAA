# CCAA — campos compartilhados entre os fluxos

## Como ler

**Contagem:** quantidade de fluxos distintos em que o dado participa do modelo de prévia, diretamente no conteúdo ou na seleção/agrupamento. Cada fluxo conta uma vez, mesmo com várias tabelas ou ocorrências. Os nomes abaixo são rótulos conceituais para comparação, não novos nomes obrigatórios de colunas.

**Temos para consulta?** **Sim** = existe fonte local preenchida, cálculo possível a partir dos dados disponíveis ou conteúdo fixo consultável no modelo. Isso não garante atualização, cobertura de todos os polos ou equivalência ao ciclo 26.2. **Não** = falta fonte operacional preenchida para variar o dado por polo; valores isolados/fictícios do sample não contam como essa fonte. As limitações aparecem na última coluna.

**Escopo: cinco fluxos**, incluindo o genérico MAIL e o sample consolidado:

- **AGENDA**: `AGENDA_SEMANAL_AUDITORIAS` (Mari).
- **ACADEMICA**: `REGULARIZACAO_AUDITORIA_ACADEMICA` (Aulas práticas).
- **FAST_TRACK**: `FAST_TRACK_INFRA_2026` (HTML estático).
- **MAIL**: `MAIL` (modelo genérico padrão; não integrado à bancada).
- **SITUACAO**: `SITUACAO_REGULARIZACAO_DOS_POLOS` (sample; gerador dinâmico ainda não implementado).

SITUACAO conta pela estrutura exigida no sample, **não** por leitura automática já implementada. FAST_TRACK conta apenas pelo conteúdo fixo do corpo; suas bases futuras não entram. MAIL pode aceitar colunas arbitrárias: aqui vale o modelo padrão, não todo campo hipoteticamente configurável. Campos presentes somente nas bases, sem efeito na prévia considerada, não aumentam a contagem. Configurações de envio/SMTP não entram.

| Nome do campo/dado | Temos para consulta? | Qtd. de fluxos em que se repete | Descrição de como afeta o preview |
|---|---|---:|---|
| `nome_polo` | Sim | 4 | **AGENDA, ACADEMICA, MAIL, SITUACAO:** Identifica o polo nas tabelas; em ACADEMICA também identifica a prévia individual. |
| `ID_polo / chave_polo` | Sim | 3 | **AGENDA, ACADEMICA, SITUACAO:** Relaciona cadastros e resultados para não misturar polos. Em AGENDA é auxiliar da preparação; o código entre parênteses não é sempre o ID COLABORAR. |
| `nome_gestor` | Sim | 2 | **MAIL, SITUACAO:** Personaliza identificação e saudação; em MAIL corresponde ao campo genérico {nome} do modelo padrão. |
| `nome_gerente_operacional` | Sim | 1 | **AGENDA:** Personaliza o cabeçalho e a saudação de Mari. Não é o mesmo papel que nome_gestor. |
| `email_destinatario` | Sim | 2 | **AGENDA, MAIL:** Define agrupamento/elegibilidade dos registros na geração original. Não precisa aparecer no corpo; em MAIL aparece também no índice de prévias. |
| `qtd_polos` | Sim | 3 | **AGENDA, MAIL, SITUACAO:** Preenche o resumo da carteira/grupo. AGENDA conta linhas; MAIL conta nomes de polos distintos; SITUACAO depende do recorte da carteira. Há dados para calcular, mas o recorte da carteira ainda precisa ser confirmado para SITUACAO. |
| `grupo_economico` | Sim | 1 | **AGENDA:** Preenche a coluna Grupo Econômico. O dado atualmente salvo pode ser quantidade de unidades; não é garantia do nome do grupo. |
| `data_auditoria` | Sim | 2 | **AGENDA, SITUACAO:** Mostra a data da auditoria e permite indicar ausência de agendamento. |
| `data_referencia` | Sim | 1 | **AGENDA:** Controla destaque de data passada e dia da semana, sem mudar as datas salvas das auditorias. |
| `periodo_auditorias` | Sim | 1 | **AGENDA:** Resume a menor e a maior data do grupo no cabeçalho. |
| `proxima_auditoria` | Sim | 1 | **AGENDA:** Preenche o texto de próxima auditoria; a lógica original usa a menor data, inclusive passada. |
| `nome_laboratorio / ambiente` | Sim | 2 | **ACADEMICA, SITUACAO:** Identifica o ambiente nas linhas de auditoria; em SITUACAO também compõe a agenda. |
| `parecer_laboratorio` | Sim | 2 | **ACADEMICA, SITUACAO:** Exibe aprovação, reprovação ou pendência e determina destaques e mensagens. |
| `qtd_laboratorios_por_status` | Sim | 2 | **ACADEMICA, SITUACAO:** Gera resumos numéricos e alertas de laboratórios; os critérios específicos não são necessariamente iguais entre os dois modelos. |
| `tipo_auditoria` | Sim | 1 | **SITUACAO:** Preenche a coluna Tipo de auditoria na agenda consolidada. |
| `nome_auditor` | Sim | 1 | **SITUACAO:** Identifica o responsável no checklist e na agenda. O campo existente na entrada de Mari não aparece no corpo atual. Disponível na agenda/labs; o vínculo completo do auditor de checklist por polo ainda precisa de fonte. |
| `status_agendamento / realizacao` | Sim | 1 | **SITUACAO:** Define A marcar e os avisos de pendência ou não comparecimento; regras de composição ainda precisam ser confirmadas. |
| `qtd_reprovados_sem_retorno` | Sim | 1 | **SITUACAO:** Preenche o aviso específico de reprovados sem retorno; não equivale à contagem de todos os pareceres Reprovado. |
| `numero_sequencia` | Sim | 1 | **ACADEMICA:** Identifica as linhas de práticas por sequência e participa dos totais. O sample SITUACAO não mostra essa divisão. |
| `aulas_previstas` | Sim | 2 | **ACADEMICA, SITUACAO:** Preenche a quantidade esperada de aulas por sequência/polo e os totais. |
| `aulas_comprovadas` | Sim | 2 | **ACADEMICA, SITUACAO:** Preenche a quantidade comprovada e é usada no cálculo do percentual. |
| `aulas_pendentes` | Sim | 2 | **ACADEMICA, SITUACAO:** Mostra o que falta comprovar e alimenta os alertas de pendência. |
| `percentual_comprovacao` | Sim | 2 | **ACADEMICA, SITUACAO:** Mostra comprovadas em relação às previstas e altera a sinalização visual. |
| `ciclo_referencia` | Sim | 1 | **SITUACAO:** Identifica o ciclo do comunicado no título e no cabeçalho; exige bases compatíveis para uma prévia dinâmica fiel. Consultável nas exportações/modelo, mas as bases 261 não correspondem automaticamente ao sample 26.2. |
| `nota_checklist` | Não | 1 | **SITUACAO:** Preenche a nota CL 2026; a fonte preenchida correspondente ainda falta. Não há base preenchida da nota; valor isolado no sample não permite consultar outros polos. |
| `status_checklist` | Não | 1 | **SITUACAO:** Exibe Concluído/Não realizado e diferencia visualmente os polos; a fonte correspondente ainda falta. As colunas candidatas de preenchimento/validação estão vazias; só há exemplos no sample. |
| `data_envio_checklist` | Não | 1 | **SITUACAO:** Preenche a observação Enviado em; não deve ser confundida automaticamente com data de visita ou data de checklist. Não foi localizada fonte operacional equivalente à observação Enviado em do sample. |
| `prazo_checklist` | Não | 1 | **SITUACAO:** Preenche o prazo por polo quando a avaliação está pendente; falta confirmar a fonte/regra. O sample tem prazo de exemplo, mas falta a fonte/regra por polo para consulta dinâmica. |
| `pendencia_descricao` | Não | 1 | **MAIL:** Preenche {Pendência} e a coluna de pendências no modelo genérico padrão. O MAIL fornece textos fictícios de exemplo; falta uma lista operacional preenchida de pendências. |
| `prazo_regularizacao` | Sim | 4 | **ACADEMICA, FAST_TRACK, MAIL, SITUACAO:** Exibe datas-limite nos textos/tabelas. Pode ser fixo ou variável; no FAST_TRACK o 31/08 é histórico e não um campo editável. Consultável como texto/configuração dos modelos; datas históricas não comprovam prazo vigente. |
| `nota_minima_MEC` | Sim | 1 | **FAST_TRACK:** Mostra o requisito fixo 3,0 no comunicado; não representa nota obtida por um polo. |
| `nome_contato / tema_atendimento` | Sim | 1 | **SITUACAO:** Compõe a lista de responsáveis por checklist e acompanhamento no fechamento. Nomes estão nos cadastros; tema e composição por carteira precisam de confirmação. |
| `email_contato / telefone_contato` | Sim | 1 | **SITUACAO:** Mostra os meios de atendimento no rodapé; precisa respeitar os responsáveis da carteira. |
| `links_referencia / atendimento` | Sim | 5 | **AGENDA, ACADEMICA, FAST_TRACK, MAIL, SITUACAO:** Preenche os acessos a agenda, relatórios, book e atendimento; os destinos variam entre os modelos. |
| `textos_institucionais / titulo / assinatura` | Sim | 5 | **AGENDA, ACADEMICA, FAST_TRACK, MAIL, SITUACAO:** Define conteúdo fixo, orientações e fechamento. Em MAIL o rascunho escolhido pode substituir o modelo padrão. |
| `estilo_email` | Sim | 5 | **AGENDA, ACADEMICA, FAST_TRACK, MAIL, SITUACAO:** Define fontes, cores, hierarquia, tabelas e espaçamentos do HTML; não é dado lido das planilhas. |

## Ressalvas

- `nome_gestor` e `nome_gerente_operacional` são papéis diferentes; não foram somados como um único campo.
- `ID_polo / chave_polo` agrupa a finalidade de relacionamento, não afirma equivalência entre identificadores de sistemas.
- Contagem de presença não comprova disponibilidade ou atualização do dado: o checklist e a compatibilidade de ciclo do consolidado seguem pendentes.
- Para a bancada atual ACADEMICA, destinatários/Master não são lidos: por isso email, canal, status cadastral e marcação de envio não foram contados como entradas dessa prévia.
- Fontes: renderizadores em `testes/preview_mari.py` e `testes/preview_aulas.py`; fonte original em `fluxos/REGULARIZACAO_AUDITORIA_ACADEMICA/disparar_emails.py`; modelo `fluxos/FAST_TRACK_INFRA_2026/modelo_email.html`; modelo padrão/funções de prévia em `fluxos/MAIL/vba/modDisparo.bas`; `fluxos/SITUACAO_REGULARIZACAO_DOS_POLOS/sample.html`; proveniência detalhada em `docs/CCAA-sample-dados-disponiveis-e-lacunas.md`.
