# Disparo — Auditoria de Aulas Práticas e Laboratórios (por polo)

Monta e envia **um e-mail por polo** com a situação da auditoria acadêmica
(Power BI "Auditoria Acadêmica EaD", canal PARCEIRO):

- aulas práticas **previstas / comprovadas / pendentes** em cada sequência (1 a 4);
- **% de aprovação dos laboratórios** do polo.

O gestor do polo recebe o e-mail, a auditoria acadêmica vai em cópia e o gerente
operacional vai em cópia oculta (os dois vêm da Base de Polos - Master).

## Arquivos de entrada (nesta pasta)

| Arquivo | O que é |
|---|---|
| `sequenciaa1.xlsx`, `sequenciaa2.xlsx`, `sequencia3.xlsx`, `sequencia4.xlsx` | exportações do Power BI, uma por sequência |
| `labs.xlsx` | uma linha por laboratório (Polo, Laboratório, Parecer Auditoria) |
| `emails.xlsx` | colunas Polo, Email, Enviar |
| `Base de Polos - Master (1).xlsb` | gestor e gerente operacional de cada polo |

## Como usar

```
pip install pandas openpyxl pyxlsb pywin32
python disparar_emails.py                               # só gera previews em ./previews/ (não envia)
python disparar_emails.py --mostrar --polo "CAMPO MOURAO"   # abre 1 e-mail no Outlook para conferir
python disparar_emails.py --enviar --marcados           # envia pelo Outlook para os polos elegíveis
```

Antes de enviar, troque `SEU.EMAIL@cogna.com.br` pelo seu e-mail no topo de
`disparar_emails.py`. Todas as opções estão descritas no começo do arquivo.

`scripts/disparar_emails.py` é a primeira versão (envio só por SMTP) e fica só de referência.
