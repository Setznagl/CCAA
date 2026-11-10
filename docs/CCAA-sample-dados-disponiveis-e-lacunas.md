# Situação de Regularização dos Polos — dados disponíveis e lacunas

## Escopo e resultado

Pull solicitado realizado com `git pull --ff-only origin main`, até `3ac0976`, preservando as alterações locais Fast Track. O novo arquivo é `fluxos/SITUACAO_REGULARIZACAO_DOS_POLOS/sample.html`; a pasta nova contém o exemplo, não uma base específica nem um gerador.

O sample é um email preenchido para um gestor e ciclo 26.2, com quatro blocos: checklist, agenda de laboratórios, comprovação de aulas práticas e resultados de laboratórios. Para exibi-lo como prévia estática não falta dado. Para gerar versões por gestor usando fontes locais, há insumos parciais, mas falta a base preenchida do checklist, compatibilidade de ciclo/snapshot e definição do recorte da carteira e dos indicadores. Esta etapa foi somente análise, sem criação de outra página ou mudança de regras.

## Matriz de disponibilidade

| Bloco / campos | Fonte existente | Situação / o que falta |
|---|---|---|
| Layout, textos institucionais, cabeçalho, rodapé, links | Próprio `sample.html` | Disponíveis para reprodução estática. É HTML preenchido, não um template parametrizado. |
| Gestor, polo e vínculo de carteira | `REGULARIZACAO_AUDITORIA_ACADEMICA/Base de Polos - Master (1).xlsb`, aba `BASE_DE_UNIDADES`, campos `GESTOR DE POLO / DIRETOR UNIDADE`, `NOME UNIDADE SISTEMA`, canal, status e IDs | Dados disponíveis. Confirmar regra de inclusão e ID de junção; o nome exibido pode conter código diferente do ID COLABORAR. Gestor de polo não é automaticamente o gerente operacional da agenda Mari. |
| Quantidade de polos na carteira | Derivada de carteira filtrada | Precisa de regra. O exemplo mostra quatro polos; a Master consultada contém seis unidades PARCEIRO em OPERAÇÃO/CAPTAÇÃO para o mesmo gestor. |
| Checklist: nota CL 2026, status, prazo/data de envio, auditor por polo | Há candidatos parciais nas planilhas Fast Track, mas não a tabela preenchida equivalente ao exemplo | Em `AÇÕES_ENFERMAGEM_PRESENCIAL_2026_1.xlsx`, aba `Planilha1`, as colunas `PREENCHEU CL`, `VALIDADO` e `NOTA FINAL` estão integralmente vazias, também na leitura sem `data_only`. `MEC_Contole_Adequacao_Polos.xlsx` tem `DATA CL`, mas não nota/status/prazo completos. Não sustenta a nota 69,94 e os demais registros do exemplo. |
| Agenda: polo, laboratório/ambiente, tipo, auditor, agendamento, data e realização | `REGULARIZACAO_AUDITORIA_ACADEMICA/labs.xlsx`, aba `Export`, campos `Polo`, `Laboratório`, `Local`, `Tipo auditoria`, `Auditor`, `Agendada`, `Data agendada`, `Realizada` e `Data realização` | Estrutura disponível. Os registros são do semestre 261 e divergem do exemplo 26.2. Confirmar filtro, significado do rótulo de tipo e regra dos avisos de pendência/não comparecimento. A agenda Mari é outra fonte de datas, mas não tem o mesmo detalhe por laboratório do sample. |
| Aulas: previstas, comprovadas, pendentes e percentual | Quatro planilhas `sequenciaa1.xlsx`, `sequenciaa2.xlsx`, `sequencia3.xlsx`, `sequencia4.xlsx`, aba `Export` | Campos disponíveis; percentual/totais são derivados. As exportações indicam semestre 261, não comprovam os valores do sample 26.2. Confirmar sequências incluídas, pois o exemplo não detalha o cálculo. |
| Resultado por laboratório: polo, laboratório e parecer | `labs.xlsx` → `Polo`, `Laboratório`, `Parecer Auditoria` | Estrutura disponível. Confirmar ciclo/snapshot e filtro de finalização/parecer para compor a seção. |
| Indicador “reprovados sem retorno” | `aprovacao.xlsx`, aba `Export`, campo `Rep. Sem Retorno`, além de outros agregados | O campo existe, mas os valores 261 não reproduzem o indicador do sample. Não confundir quantidade de pareceres Reprovado com quantidade sem retorno. |
| Contatos do rodapé | Contatos existentes na Master (`CONTATOS_PARCEIROS`) e no XLSM Mari (`Contatos`); textos também no sample | Cadastro disponível, mas precisa definir responsáveis por polo/tema e a regra de união sem repetição para cada gestor. Não publicar dados pessoais integrais em relatório. |
| Ciclo e prazos gerais | Escritos no sample: 26.2, 04/10, 06/10; checklist 09/10/2026 e envio 21/09/2026 | Podem ser mantidos como conteúdo histórico em prévia estática. Para geração de uma rodada diferente, confirmar os valores da configuração; não tratar como prazos atuais. |

Todos os caminhos da tabela estão sob `fluxos/`.

## Divergências verificadas no exemplo

- A Master possui seis unidades parceiras em operação/captação para o gestor do exemplo, enquanto o cabeçalho mostra quatro polos. Isso pede confirmação do recorte, não uma alteração automática para seis.
- As quatro sequências, somadas por código de polo, retornam para Mauá I (1121) 48 previstas/0 comprovadas/48 pendentes. O sample exibe 60/0/60. Para Mauá VII são 72/0/72 versus 96/0/96; Santos III 28/0/28 versus 30/0/30. São Paulo XIII tem 8/0/8 nas fontes e não aparece na tabela de práticas do sample. Não há reprodução fiel desses valores com o snapshot disponível sem outra fonte/regra.
- A agenda do sample exibe três laboratórios de Mauá I a marcar. A fonte `labs.xlsx` consultada tem duas linhas para esse polo, com datas de maio de 2026, outro auditor e parecer Reprovado. Confirma a diferença entre snapshots, não prova erro no sample.
- O sample tem seis linhas de parecer Reprovado e um indicador de cinco sem retorno; são métricas diferentes. `aprovacao.xlsx` oferece a segunda métrica, mas no snapshot 261.
- As planilhas Fast Track têm registros parciais de checklist/laboratórios e foco em enfermagem; para os polos do sample, os registros operacionais localizados se concentram em Mauá VII. Não substituem uma base completa CL 2026.

## Mínimo para previews dinâmicas completas

1. Exportação preenchida CL 2026 com polo/ID, nota, status, data de envio ou prazo/observação e auditor, cobrindo a carteira desejada.
2. Bases de aulas, agenda e resultados do mesmo ciclo/snapshot; ou autorização explícita para usar 261 com identificação correta, sem dizer que reproduz 26.2.
3. Regra de carteira e chave entre fontes: gestor, unidades/canais/status incluídos e tratamento de cadastros duplicados/IDs antigos.
4. Regras de composição: sequências de práticas incluídas, status de agenda, pareceres exibidos e definição de sem retorno; responsáveis e prazos da rodada.

Para prévia visual estática, o sample já contém todos os valores. Destinatários, autenticação e serviços de email não são necessários para gerar o corpo HTML.

## Limites da inspeção

Leitura local das planilhas e do HTML, sem refresh SharePoint, recálculo Excel, macros ou envio. Não foi criado um novo gerador nem alteradas fontes. As alterações Fast Track anteriores continuam locais, sem commit/push nesta análise.
