# CCAA — duas páginas de teste de HTML

Ambiente local de inspeção, sem integração com serviços de email e sem executar macros ou Outlook.

## Abrir as páginas

Na raiz do seu clone, após copiar a pasta `../fluxos` original conforme o README principal, execute:

```sh
.venv/bin/python testes/preview_server.py --port 8876
```

- Auditoria Mari: `http://127.0.0.1:8876/mari`
- Aulas práticas: `http://127.0.0.1:8876/aulas-praticas`

O servidor escuta apenas no loopback da máquina em que foi iniciado. Se Hermes e navegador estiverem em máquinas diferentes, use o acesso local/encaminhamento autorizado do seu ambiente; não publique esta porta, pois as bases contêm dados pessoais.

Selecione um gerente/grupo ou polo, clique em **Gerar HTML de teste**, confira a prévia e use **Baixar HTML gerado**. Trocar a seleção invalida o download anterior até gerar novamente.

O arquivo baixado contém somente o HTML do email. A página de controle não é incluída. A prévia conserva estilos inline e bloqueia scripts, formulários e carregamento de recursos externos. As tabelas de largura fixa do email podem exigir rolagem dentro da prévia no celular; o layout do email não é redesenhado pelo painel.

## Instalação em uma cópia nova

Verificado com Python 3.14 e as dependências fixadas em `testes/requirements.txt`:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r testes/requirements.txt
.venv/bin/python testes/preview_server.py
```

No Windows, use `.venv\\Scripts\\python.exe` no lugar de `.venv/bin/python`. O ambiente de teste de Mari não exige Excel: trata-se da reprodução isolada expressamente autorizada, não execução do VBA original.

## O que cada página valida

### Auditoria Mari

Lê somente os valores já armazenados de `rev/Disparo Auditoria Mari/Disparador_auditoria_automatizado_FINAL(1).xlsm`, aba `Aba de auditorias`, sem atualizar fórmulas, contatos ou consultas. A montagem HTML é uma reprodução isolada do Módulo1 atual. A data do controle afeta apenas avisos de data passada/próxima no email, não as datas das auditorias.

Para comparar com a prévia salva do grupo Adiel, use a data **11/09/2026**. A equivalência com o arquivo salvo é objeto dos testes de Mari; isso não certifica compilação ou execução das macros no Excel.

### Aulas práticas

Reutiliza diretamente, a partir do código recebido, `chave`, `ler_sequencias`, `adicionar_labs` e `gerar_html`, com suas constantes necessárias. Essas funções são selecionadas por AST, sem importar/executar o entrypoint do disparador e sem carregar funções de transporte.

Para inspecionar o corpo HTML, lê as quatro planilhas de sequência e `labs.xlsx`. Não lê `emails.xlsx` ou Master, não resolve destinatários e não aplica autorização/seleção de envio: esses dados não são usados pelo corpo HTML atual. A saída foi comparada à geração com os leitores completos para verificar que essa separação não altera o HTML.

## Limites deliberados

- Correções de lógica/checagens de negócio continuam adiadas em `docs/CCAA-pontos-de-atencao-adiados.md`.
- Não há envio, rascunhos Outlook, atualização SharePoint nem alteração das fontes recebidas.
- Usa as bases locais recebidas, que ficam fora do Git e precisam ser copiadas para `../fluxos`; upload/importação pela interface não faz parte desta etapa.
- Os dados são carregados na primeira utilização e mantidos em memória. Reinicie o servidor após mudar arquivos para uma nova rodada de teste.
- Os controles usam visual neutro temporário, autorizado pelo usuário. O HTML do email mantém seu estilo atual. A referência final LIRA permanece para a etapa visual posterior.
- Navegador não certifica renderização no Outlook/Gmail nem entrega de email.

## Testes

```sh
cd testes
../.venv/bin/python -m unittest discover -p 'test_*.py' -v
node --test test_app.mjs
```

Os testes Node não exigem pacotes adicionais e verificam também a troca de seleção/data durante uma geração pendente.

O teste de navegador `test_e2e.mjs` exige Playwright e Chromium disponíveis no ambiente de desenvolvimento; aceita `CCAA_PLAYWRIGHT_MODULE`, `AGENT_BROWSER_EXECUTABLE_PATH` e `CCAA_TEST_URL`. Evidências locais ficam em `testes/evidence/`.
