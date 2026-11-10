# CCAA

Projeto do agrupador Cogna Automations. Páginas locais para gerar, inspecionar e baixar HTML, sem envio de email.

## Preparar seu clone

```sh
git clone git@github.com:Setznagl/CCAA.git
cd CCAA
```

Os fluxos estão organizados em `fluxos/`:

| Pasta | Página de teste | Entrada atual |
|---|---|---|
| `AGENDA_SEMANAL_AUDITORIAS` | Agenda Semanal de Auditorias | Valores salvos no XLSM; seleção de gerente/grupo e data de referência |
| `AGENDA_REGULARIZACAO_AUDITORIA_ACADEMICA` | Agenda de Regularização da Auditoria Acadêmica | Planilhas de sequência e laboratórios; seleção de polo |
| `AGENDA_FAST_TRACK_INFRA_2026` | Agenda Fast Track Infra 2026 | HTML fixo baseado em `exemplo_email.pdf`; **sem preenchimento e sem leitura de planilhas** |
| `AGENDA_AUDITORIA_E_SITUACAO_REGULARIZACAO_DOS_POLOS` | Agenda de Auditoria e Situação de Regularização dos Polos | Carteira por gestor e bases locais; formulário para completar/revisar os dados antes de gerar |

A pasta `MAIL` é um disparador genérico independente e não participa destas páginas. Não execute macros ou os disparadores originais para usar a bancada.

Os leitores aceitam também os nomes anteriores das pastas acadêmica e consolidada, preservados em clones com alterações locais. A compatibilidade não faz pull nem move as bases.

## Linux/macOS

Verificado com Python 3.14:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r testes/requirements.txt
.venv/bin/python testes/preview_server.py
```

## Windows — PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r testes/requirements.txt
.\.venv\Scripts\python.exe testes/preview_server.py
```

- Agenda Semanal de Auditorias: `http://127.0.0.1:8876/mari`
- Agenda de Regularização da Auditoria Acadêmica: `http://127.0.0.1:8876/aulas-praticas`
- Agenda Fast Track Infra 2026: `http://127.0.0.1:8876/fast-track-infra-2026`
- Agenda de Auditoria e Situação de Regularização dos Polos: `http://127.0.0.1:8876/auditoria-situacao-polos`

Clique em **Gerar HTML de teste**, confira a prévia e baixe o arquivo. No Fast Track não é necessário selecionar ou preencher nada. O prazo **31/08** é conteúdo histórico do exemplo recebido, não um prazo atualizado.

No consolidado, selecione um gestor para carregar a carteira e os dados disponíveis; confira os polos, complete checklist, prazos e contatos e revise as tabelas antes de gerar. A opção de preenchimento manual permite começar sem uma carteira carregada. As exportações atuais de práticas/laboratórios/aprovação indicam **261 (26.1)**; **262 e 26.2 são sinônimos**, mas mudar o ciclo do título não atualiza as fontes. O aviso de origem acompanha o HTML gerado. Dados manuais não são gravados nas planilhas; salve o HTML que deseja conservar.

O serviço escuta somente em loopback; não publique a porta com bases pessoais. As evidências geradas e o ambiente virtual não são versionados.

Detalhes e testes: [testes/README.md](testes/README.md). Os testes de comparação Mari exigem também a prévia original em `fluxos/AGENDA_SEMANAL_AUDITORIAS/previews/`, que não veio no último push de reorganização; sua ausência não impede a geração pela página.

## Escopo preservado

- Correções de lógica e checagens de negócio adiadas: [tabela](docs/CCAA-pontos-de-atencao-adiados.md).
- Controles neutros temporários; emails conservam o estilo de suas referências. Padrão visual futuro deve seguir LIRA.
- Mari é reprodução isolada comparada à prévia salva, não execução VBA.
- Fast Track usa `fluxos/AGENDA_FAST_TRACK_INFRA_2026/modelo_email.html`; o PDF não precisa ser convertido durante a execução. Dados de remetente/destinatário da impressão Outlook não fazem parte do corpo HTML.
- Consolidado conserva a arte do sample e permite edição manual antes da prévia. Ausência de dado não é convertida automaticamente em zero ou Não realizado; campos sem preenchimento permanecem identificados.
- As bases Fast Track ficam reservadas para etapa futura, sem associação a destinatários agora.
- Sem integração SMTP/Outlook, atualização SharePoint ou envio.
