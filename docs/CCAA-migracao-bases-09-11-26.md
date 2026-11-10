# CCAA — Migração concluída para as bases de 09/11/2026

Integração local concluída em 10/11/2026, sem commit/push ou envio de email. As três prévias operacionais usam somente `databases/09-11-26`; Fast Track continua estático.

## Entrega

- Quatro módulos `preview_<NOME_EXATO_DO_FLUXO>.py` em `testes/`, com imports, controles e documentação correspondentes. Um único `preview_server.py` atende as quatro rotas existentes.
- Agenda Semanal: todas as linhas/datas de laboratório disponíveis para seleção; grupo econômico, GO/email e lacunas em inputs manuais, com confirmação antes de gerar. Sem seleção semanal automática nem email de gestor de polo usado como email de GO.
- Regularização Acadêmica: renderer próprio sem dependência de disparadores; práticas agregadas e laboratórios revisáveis. Prazos começam vazios, com confirmação explícita quando não aplicáveis; datas históricas não são defaults vigentes.
- Consolidado: carteira por gestor principal, recortada pelos polos presentes em timeline/apps/acompanhamento; checklist, prazos e lacunas continuam manuais. Vereditos não substituem Checklist CL2026. Ausência não vira zero/Não realizado.
- `databases/09-11-26/emails.xlsx`: 587 polos, emails distintos dos gestores principais concatenados com `;`, coluna Enviar inteiramente vazia. Arquivo derivado e ignorado no Git, sem alimentar o corpo HTML.
- Dados manuais enviados por POST, não na URL ou localStorage. Edições invalidam prévia/download, inclusive respostas obsoletas; snapshots opacos e downloads conferidos byte a byte.

## Limpeza e preservação

Foram removidos **15 arquivos operacionais obsoletos** das pastas de Agenda Semanal e Regularização Acadêmica: XLSM/XLSB/XLSX, módulos BAS e disparadores antigos. As pastas conservam READMEs com as instruções vigentes.

Antes da exclusão, cada arquivo foi copiado e conferido por SHA-256. Backup durável fora do repositório:

`/opt/data/ccaa-archive/2026-11-10T040345.113336Z-source-migration/manifest.json`

O manifesto registra os 15 caminhos, tamanhos e hashes; após a limpeza, todas as cópias foram reconferidas e todos os caminhos operacionais antigos estavam ausentes. `rev/` e `references/` permanecem preservados, sem participação no runtime.

As cinco bases novas foram conferidas contra os bytes versionados, sem alteração. Os 13 arquivos versionados de MAIL e Fast Track também permanecem iguais ao HEAD, incluindo suas bases reservadas, PDF e HTML estático. MAIL é independente e não foi migrado nem executado.

## Verificação final do responsável, após a limpeza

| Verificação | Resultado |
|---|---|
| Python | 50 testes aprovados, nenhum erro/pulado |
| JavaScript | 32 testes aprovados, nenhuma falha/pulado |
| Navegador — integração das quatro páginas | Aprovada em Chromium desktop/móvel |
| Navegador — consolidado aprofundado | Aprovado; origem 262 preservada mesmo com título 26.1 |
| Geração/snapshot/download | Bytes idênticos |
| Requisições externas / erros JavaScript | Nenhum nos dois E2E |
| Inicialização HTTP | Uma URL anunciada; porta ocupada não abre alternativa |
| `git diff --check` | Limpo |
| Servidores temporários | Encerrados; nenhum listener em 8876/8877 ao final da verificação |

Evidências locais, ignoradas no Git: `testes/evidence/browser-all.json`, `browser-consolidado.json` e capturas dos quatro fluxos. Os HTMLs/campos de QA podem conter overrides manuais de teste, não aprovação operacional dos dados.

## Contagens das fontes, sem rodapés ou separadores

| Fonte | Polos | Linhas operacionais |
|---|---:|---:|
| apps-prazo | 586 | 586 |
| acompanhamento | 461 | 461 |
| contatos | 2.336 | 37.073 |
| timeline | 460 | 1.762 |
| vereditos | 89 | 738 |

As contagens anteriores com um polo adicional incluíam o rodapé da exportação. Os relatórios de cobertura foram corrigidos.

## Limites

Não houve publicação, macros, COM, SMTP/Outlook, refresh SharePoint ou envio. A aparência foi verificada no navegador, não em clientes de email. Emails com tabelas de largura fixa exigem rolagem interna no celular. Há avisos cosméticos do openpyxl sobre ausência de estilo padrão nas fontes; não foram escondidos nem alteradas as planilhas para removê-los. Checklist e demais dados sem fonte continuam exigindo preenchimento/revisão humana.
