# CCAA — Comparativo: Agenda Semanal de Auditorias × bases novas

Comparação do leitor atual `testes/preview_mari.py:12–34` com os cabeçalhos das cinco planilhas em `databases/09-11-26`. O problema não é o semestre 262/26.2: os conjuntos de dados têm granularidade e papéis de contato diferentes. Esta avaliação não autoriza excluir a fonte de Mari nem decide mantê-la permanentemente.

## Campo a campo

| Informação | Fonte consumida hoje | Bases novas | Diferença / complemento necessário |
|---|---|---|---|
| Polo | `Disparador_auditoria_automatizado_FINAL(1).xlsm` → `Aba de auditorias`, coluna A, desde a linha 10 | `Polo` em timeline e contatos; `ID polo` explícito em ambos | Disponível. A migração exige conferir a identidade e evitar duplicar um polo pelas várias linhas de laboratório. |
| Grupo econômico mostrado no email | Mesma aba, coluna C | Nenhum dos cinco cabeçalhos possui campo equivalente | Precisa de complemento manual ou outra fonte. Não substituir nome de grupo por quantidade de unidades. |
| Data da auditoria | Mesma aba, coluna D | `Data agendada` e `Data realização` na timeline, por laboratório | Existem datas, mas não uma data única por polo. É necessário definir o recorte e como mostrar múltiplas auditorias. O leitor atual apenas reproduz as linhas salvas: **não filtra automaticamente a semana corrente**. |
| Nome do gerente operacional | Mesma aba, coluna E | `Gerente Operacional` nos contatos | Há nomes e placeholders `TBD`. Um placeholder não deve ser confirmado como gerente válido. |
| Destinatário que determina o agrupamento | Mesma aba, coluna F; o leitor agrupa por email | `E-mail` refere-se à pessoa da coluna `Nome`, com `Perfil` próprio | Email de `GESTOR PRINCIPAL` **não equivale** ao email do gerente operacional. A conferência dos contatos não encontrou igualdade exata entre os nomes de GO e os nomes de contatos com email. Não há uma coluna própria de email de GO. |
| Horário | Pode existir no valor de data salvo | Datas de agendamento/realização | O renderer atual imprime apenas dia/mês/ano; não exibe horário. Existência de hora na fonte não muda isso automaticamente. |
| Quantidade e período exibidos | Calculados a partir das linhas lidas | Podem ser calculados após definir a seleção | Contagem de linhas de laboratório não equivale automaticamente à contagem de polos. |

## Por que a avaliação anterior parecia suficiente

O relatório de cobertura das novas bases avaliou principalmente a **Agenda de Regularização da Auditoria Acadêmica** e a **Agenda de Auditoria e Situação de Regularização dos Polos**. Esses fluxos usam práticas, laboratórios, carteira de gestores de polo e indicadores. A Agenda Semanal de Auditorias agrupa por outro contato e também exibe grupo econômico.

Portanto, disponibilidade para Aulas/consolidado não demonstrou equivalência integral para Mari. A versão anterior deste comparativo também chamou o email de gestor principal de equivalente ao destinatário de Mari e afirmou uma seleção semanal manual como fato; essas afirmações foram corrigidas. O código comprova leitura do estado salvo, não o processo humano que o produziu.

## O que permite migrar Mari sem manter a planilha antiga

- Preencher ou fornecer grupo econômico e os contatos de gerente que faltam.
- Definir a seleção das datas e dos polos a partir da timeline, sem assumir semana corrente ou descartar laboratórios arbitrariamente.
- Manter os suplementos revisáveis antes da geração, sem alterar as fontes originais.

**Situação:** migração de Mari e exclusão de sua fonte ainda dependem dessa escolha. Preservar o XLSM enquanto isso evita retirar uma página do ar; não é uma decisão de manter dados antigos como fonte definitiva.

## Demais fluxos

- **Aulas:** portar o renderer para código próprio, usando `auditoria-apps-prazo.xlsx` e `auditoria-timeline-262.xlsx`, sem dependência do disparador legado.
- **Consolidado:** migrar carteira, práticas, agenda, pareceres e indicador para as novas planilhas; Checklist CL 2026 e itens sem fonte continuam manuais. Vereditos não substituem checklist.
- **Fast Track:** permanece HTML estático; não usa planilhas e conserva o prazo histórico 31/08.

## Evidências da reconferência

- Leitor e renderer: `testes/preview_mari.py`, especialmente `load_mari`, `_row` e `render_mari`.
- Cabeçalhos das cinco planilhas conferidos estaticamente, sem macros, refresh ou envio.
- Contatos: 37.073 linhas operacionais; perfis presentes são de contatos de polo. Foram encontradas 29 designações distintas de GO e nenhuma correspondência exata dessas designações com `Nome` de contato com email. Isso **não prova** que um email de GO não possa existir em outra fonte ou sob outra grafia; apenas não permite deduzi-lo desta tabela.
