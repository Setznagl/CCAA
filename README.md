# CCAA

Projeto do agrupador Cogna Automations. Bancada local para gerar, inspecionar e baixar HTML, **sem envio de email pelo servidor**. Fast Track também exporta um lote revisado para execução separada no Windows/Outlook clássico.

**Instruções de uso do disparo em lote:** [guia para Outlook clássico](docs/CCAA-disparo-em-lote-outlook.md).

## Previews por fluxo

Os módulos ficam em `testes/` e usam o nome exato do fluxo:

| Fluxo | Módulo | Página |
|---|---|---|
| `AGENDA_SEMANAL_AUDITORIAS` | `preview_AGENDA_SEMANAL_AUDITORIAS.py` | `/mari` |
| `AGENDA_REGULARIZACAO_AUDITORIA_ACADEMICA` | `preview_AGENDA_REGULARIZACAO_AUDITORIA_ACADEMICA.py` | `/aulas-praticas` |
| `AGENDA_FAST_TRACK_INFRA_2026` | `preview_AGENDA_FAST_TRACK_INFRA_2026.py` | `/fast-track-infra-2026` |
| `AGENDA_AUDITORIA_E_SITUACAO_REGULARIZACAO_DOS_POLOS` | `preview_AGENDA_AUDITORIA_E_SITUACAO_REGULARIZACAO_DOS_POLOS.py` | `/auditoria-situacao-polos` |

**Um único servidor:** `preview_server.py`. Não inicie um servidor por template. As URLs antigas foram preservadas para não quebrar a navegação.

## Executar

```sh
git clone git@github.com:Setznagl/CCAA.git
cd CCAA
python3 -m venv .venv
.venv/bin/python -m pip install -r testes/requirements.txt
.venv/bin/python testes/preview_server.py
```

No Windows/PowerShell, use `py -m venv .venv` e `.\.venv\Scripts\python.exe` no lugar de `.venv/bin/python`.

Abra `http://127.0.0.1:8876/` e navegue pelo menu. O servidor anuncia um único endereço; se a porta estiver ocupada, encerra com orientação, sem procurar outra porta. `--port` permite escolher explicitamente uma porta diferente.

O serviço escuta somente em loopback. Não publique a porta com bases pessoais. Se o navegador estiver em outra máquina, use apenas encaminhamento autorizado.

## Hospedagem opcional (Traefik/HTTPS)

Padrão do LIRA adaptado ao servidor Python existente: `Dockerfile` (imagem `ccaa:local`, usuário não-root, healthcheck `/healthz`), `docker-compose.yml` (host networking, raiz somente-leitura, labels do Traefik com rate limit, credencial montada read-only) e `on.sh` (build → stop → init de credencial → up; nunca sobrescreve credencial existente).

```sh
cp .env.example .env   # ajuste TRAEFIK_HOST/CCAA_UID/CCAA_GID no servidor
./on.sh                # gera runtime/acesso.txt na 1ª execução (leia com sudo, não publique)
```

No modo hospedado (`CCAA_PUBLIC_URL` + `CCAA_AUTH_FILE`), todo conteúdo exige login HTTP Basic (scrypt) e Host/Origin exatos do domínio configurado; sem essas variáveis o servidor continua local em loopback, inalterado. A porta interna continua exposta na rede do host — o HTTPS e o rate limit são do Traefik, mantenha a porta bloqueada externamente.

## Fontes vigentes

As prévias com dados usam **somente `databases/09-11-26/`**:

- `auditoria-tabela-contatos.xlsx`: gestores de polo e hierarquia. Email de gestor principal não equivale ao de gerente operacional.
- `auditoria-apps-prazo.xlsx`: práticas agregadas por polo, sem inventar sequências.
- `auditoria-timeline-262.xlsx`: agenda e pareceres por laboratório.
- `auditoria-polos-acompanhamento-262.xlsx`: indicador Rep. Sem Retorno, distinto de todos os pareceres Reprovado.
- `auditoria-vereditos-262.xlsx`: preservada para uso futuro; não substitui Checklist CL2026.

262 e 26.2 são sinônimos. O semestre real vem das fontes, não do título digitado. Os leitores descartam separadores e rodapés de exportação como registros, preservando metadados de origem.

O consolidado gera `databases/09-11-26/emails.xlsx` intermediária: **Polo | Email | Enviar**. Concatena com `;` emails distintos de contatos com Perfil GESTOR PRINCIPAL, mantém Enviar vazio e recorta polos presentes em timeline, apps ou acompanhamento. O arquivo é ignorado no Git e **não é fonte do HTML nem autorização de envio**. Reinicie o servidor após substituir as bases; a carga refaz o derivado quando sua assinatura de origem mudar.

## Preencher antes de gerar

- **Agenda Semanal:** revise polos, laboratórios e datas; complete grupo econômico, email do GO e GO ausente/TBD/ambíguo. Confirme o período selecionado. Não há filtro automático de semana nem escolha arbitrária da primeira data.
- **Regularização Acadêmica:** revise práticas/laboratórios e informe os suplementos do formulário. As bases novas não fornecem os prazos gerais; os prazos históricos do modelo não devem ser reapresentados como vigentes.
- **Consolidado:** selecione gestor ou preenchimento manual, revise carteira, complete checklist, prazos e contatos. Um polo pode pertencer a mais de um gestor; não se escolhe silenciosamente o primeiro. Polos sem associação são sinalizados na revisão manual.
- **Fast Track:** corpo estático do **Comunicado CLFT_13.11.pdf**, prazo **20/11/2026**, sem campos nem leitura de planilhas na prévia e com arte institucional preservada. **DIsparo em lote** abre a união dos polos com datas de checklist vazias nas duas bases de acompanhamento, contatos gerenciais revisáveis e assunto automático com nome do polo, para baixar ZIP compatível com a ponte Outlook existente. A alternativa manual anterior permanece disponível. Detalhes e limites em `testes/README.md`.

Alterar dados invalida a prévia/download anterior. Suplementos são enviados por POST, não pela URL, e não são persistidos nas planilhas ou no navegador. Salve o HTML desejado antes de sair.

## Segurança e limites

- O servidor não executa macros, Outlook, SMTP, rascunhos ou atualização SharePoint. O pacote Fast Track usa uma ponte local separada para Outlook clássico, com rascunhos por padrão e envio confirmado pelo operador. `fluxos/MAIL/` permanece independente e intacto.
- Prévia isolada por sandbox/CSP; sem scripts, formulários ou recursos externos no email. O download contém os mesmos bytes do HTML gerado, sem o painel.
- Ausência não vira zero, Não realizado ou ausência de auditoria. Lacunas continuam explícitas para revisão.
- Controles neutros temporários; arte dos emails preservada. A referência visual futura continua sendo LIRA.
- Bases de Fast Track reservadas para outra etapa. `references/` e `rev/` são preservação local, não fontes operacionais.
- Navegador não certifica renderização Outlook/Gmail ou entrega de email.

Detalhes e testes: [testes/README.md](testes/README.md). Cobertura e comparação de fontes: [docs/](docs/).
