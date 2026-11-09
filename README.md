# CCAA

Projeto do agrupador Cogna Automations. Etapa atual: duas páginas locais para gerar, inspecionar e baixar HTML dos fluxos Auditoria Mari e Aulas práticas, sem envio de email.

## Preparar seu clone

```sh
git clone git@github.com:Setznagl/CCAA.git
cd CCAA
```

As bases reais e os anexos recebidos **não são versionados**. Copie a pasta `rev` do pacote original para a raiz do clone, preservando os nomes:

```text
CCAA/
  rev/
    Disparo Auditoria Mari/
    DisparoAulasPraticas/
  testes/
  docs/
```

Mari usa o XLSM salvo; Aulas práticas usa o `disparar_emails.py` original, as quatro planilhas de sequência e `labs.xlsx`. Preserve também `Disparo Auditoria Mari/previews/` para os testes de comparação. Não execute macros ou o disparador original: o servidor de teste faz apenas leitura e geração isolada.

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

- Auditoria Mari: `http://127.0.0.1:8876/mari`
- Aulas práticas: `http://127.0.0.1:8876/aulas-praticas`

Selecione um registro, gere o HTML, confira a prévia e baixe o arquivo. O serviço escuta somente em loopback; não publique a porta com bases pessoais.

Detalhes e testes: [testes/README.md](testes/README.md). A suíte completa requer a cópia local de `rev/`; dados reais, evidências geradas e ambiente virtual ficam ignorados pelo Git.

## Escopo preservado

- Correções de lógica e checagens de negócio adiadas: [tabela](docs/CCAA-pontos-de-atencao-adiados.md).
- Controles neutros temporários; emails conservam o estilo original. Padrão visual futuro deve seguir LIRA.
- Mari é reprodução isolada comparada à prévia salva, não execução VBA.
- Sem integração SMTP/Outlook, atualização SharePoint ou envio.
