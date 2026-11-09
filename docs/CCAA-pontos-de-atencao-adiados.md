# CCAA — pontos de atenção adiados

**Decisão vigente:** o usuário adiou as correções de lógica e checagens. A prioridade passa a ser duas páginas de teste, uma para cada frente, para gerar e inspecionar HTML sem integrar serviços de email. Esta tabela preserva os pontos discutidos, não autoriza sua implementação.

| Prioridade | Frente | Ponto de atenção / erro | Risco | Ajuste para depois |
|---|---|---|---|---|
| Crítica | AulasPraticas | --smtp combinado com --mostrar ou --rascunho entra no envio | Envio involuntário | Tornar modos exclusivos e impedir transporte em conferência |
| Alta | AulasPraticas | Chave reúne cadastros diferentes; primeira linha define elegibilidade | Exclusão de polo ativo | Definir identificação e resolver cadastros/ambiguidades |
| Alta | AulasPraticas | Duplicidade de chave/sequência sobrescreve valores | Perda ou troca de dados | Detectar duplicidades e definir separação/consolidação/rejeição |
| Alta | AulasPraticas | Master substitui marcação Enviar | Lote diferente da seleção manual | Separar elegibilidade de autorização de envio |
| Alta | AulasPraticas | Master substitui email de emails.xlsx | Destinatário diferente do esperado | Definir prioridade e conferir conflitos |
| Alta | Mari | ID não encontrado apaga a data D | Perda de dado operacional | Preservar data e registrar falha separadamente |
| Alta | Mari | Grupo econômico vem de CI, quantidade de unidades | Grupo exibido incorretamente | Usar GRUPO ECONOMICO, atualmente CH |
| Alta | Mari | Busca de contato exige igualdade do nome | Exclusão por grafia/nome abreviado/prefixo | Usar correspondências validadas e bloquear ambíguas |
| Alta | Mari | Validação de email insuficiente | Aceitar destino/lista malformada | Separar e validar endereços |
| Alta | Ambas | Sem controle persistente suficiente de retomada | Duplicidade após falha/reexecução | Registrar lote/destino/unidade/resultado e permitir retomada |
| Alta | Ambas | Ciclos/snapshots diferentes e prazos fixos no Python | Cobrança ou informação de período errado | Validar ciclo/snapshot e centralizar prazos |
| Média | AulasPraticas | Sem validação de coerência de previstas/comprovadas/pendentes | Email inconsistente com exportação ruim | Validar tipos, ausências e relação entre valores |
| Média | Mari | Agrupa apenas por email; nome da primeira linha e contagem de linhas | Misturar responsáveis ou duplicar contagem | Validar responsável e distinguir linhas/polos/auditorias |
| Média | Mari | Não ordena datas e pode chamar data passada de próxima | Agenda confusa | Ordenar e definir tratamento das datas |
| Média | Mari | Base_polos e Contatos usam origens SharePoint diferentes | Snapshots incompatíveis | Definir fontes oficiais e registrar atualização |
| Média | Ambas | Visual atual ainda não adequado à referência LIRA | Comunicação visual divergente | Recuperar e aplicar regras reais do LIRA depois da validação da geração |
| Limite da análise | Ambas | Diagnóstico estático, sem execução operacional | Confundir leitura com funcionamento certificado | Validar primeiro sem transporte de email |

Estado: correções adiadas por decisão do usuário; nenhuma foi aplicada nesta etapa. A proteção do novo ambiente de teste contra envios e acessos indevidos permanece obrigatória e não é uma alteração da lógica de negócio existente.
