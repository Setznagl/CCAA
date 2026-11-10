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

Lê timeline e contatos da pasta nova, não XLSM/Master. Mantém todas as linhas de laboratório e datas disponíveis para seleção explícita; não filtra automaticamente a semana corrente. O contador distingue polos únicos e linhas de laboratório.

Grupo econômico e email do GO começam vazios. GO ausente/TBD/ambíguo fica acessível na revisão manual, não desaparece. Complete os campos, selecione linhas/datas e confirme o período antes de gerar. Email de contato de polo não é reutilizado como email de GO. A data de referência afeta avisos de data passada, não substitui as datas das auditorias.

### Agenda de Regularização da Auditoria Acadêmica

Renderer próprio, sem AST/exec do disparador legado. Lê `auditoria-apps-prazo.xlsx` e `auditoria-timeline-262.xlsx`. As práticas são agregadas por polo; não há sequências inventadas. Laboratórios/pareceres e suplementos são revisados antes da geração; prazos sem fonte são informados manualmente, não herdados das datas históricas do modelo.

Ausência de linha na timeline não comprova ausência de auditoria. Contagens ausentes não viram zero. O corpo HTML não lê destinatários nem a planilha intermediária de emails.

### Agenda Fast Track Infra 2026

O módulo de mesmo nome lê os bytes de `fluxos/AGENDA_FAST_TRACK_INFRA_2026/modelo_email.html`. Não lê planilhas, não converte PDF em runtime e não possui campos. Preserva imagens incorporadas, texto e prazo **histórico 31/08** da referência; não inclui metadados Outlook/destinatários da impressão. O nome antigo da pasta continua aceito para o modelo estático.

### Agenda de Auditoria e Situação de Regularização dos Polos

- Carteira: tabela de contatos, Perfil GESTOR PRINCIPAL; somente polos presentes em timeline, apps ou acompanhamento. Mantém associações a todos os gestores, sem escolher o primeiro ou fundir pessoas distintas por um email compartilhado. Identidades potencialmente ambíguas são avisadas.
- Práticas: apps-prazo. Agenda/pareceres: timeline. Indicador Rep. Sem Retorno: acompanhamento, somente com cobertura completa e fonte única por polo.
- Checklist CL2026, prazos e contatos de apoio sem fonte permanecem manuais. Vereditos não são checklist. Carteira e linhas carregadas podem ser revisadas sem alterar as fontes.
- 262 e 26.2 são sinônimos. Ciclo ausente fica desconhecido; mudar o título não atualiza a origem. Rodapés EN/PT são metadados, não polos.
- Alterar a carteira limpa o indicador agregado para revisão. Totais de práticas são recalculados sem converter ausências em zero. Avisos de polos sem associação ficam na revisão manual, não em carteiras alheias.

Na carga do consolidado, `databases/09-11-26/emails.xlsx` é gerada com **Polo | Email | Enviar**: emails distintos de gestores principais concatenados com `;`, Enviar vazio. A escrita é atômica, protegida contra fórmulas e ignorada no Git. Uma falha de escrita vira aviso; o HTML continua usando as fontes originais. Mudança da assinatura das fontes provoca regeneração na próxima carga. O arquivo não é fonte de dados do corpo.

## Segurança e comportamento

Dados são carregados e mantidos em memória; reinicie o servidor após substituir bases. Campos manuais não são gravados em planilhas ou localStorage, nem enviados pela URL. A única escrita derivada é emails.xlsx. A geração revisada usa POST JSON limitado a 1 MiB e snapshots opacos; as últimas 16 prévias ficam em memória.

Qualquer edição/seleção invalida prévia e download, inclusive durante requisição. Respostas antigas não podem restaurar um resultado descartado. O HTML no iframe é isolado por sandbox/CSP; download e snapshot têm os mesmos bytes, sem painel de controle. Layouts de email fixos podem exigir rolagem dentro do iframe no celular; não equivalem a validação Outlook/Gmail.

Controles neutros temporários e arte dos emails preservada. A referência visual posterior é LIRA; envio e regras de negócio fora desta migração continuam sem integração.

## Testes

Da raiz:

```sh
.venv/bin/python -m unittest discover -s testes -p 'test_*.py' -v
node --test testes/test_app.mjs testes/test_*_app.mjs
```

Os testes unitários Node não precisam de pacotes adicionais. Testes de arte usam goldens sintéticos versionados, sem depender da prévia pessoal ausente de Mari. Fixtures não são fontes operacionais.

Os E2E exigem Playwright/Chromium e aceitam `CCAA_PLAYWRIGHT_MODULE`, `AGENT_BROWSER_EXECUTABLE_PATH` e `CCAA_TEST_URL`. Evidências ficam em `testes/evidence/`, ignoradas no Git. Use um servidor de teste apenas durante a execução e encerre-o ao terminar; não deixe outra instância ocupando uma segunda porta.
