# Disparador — Auditoria de Laboratórios (agenda semanal para os GOs)

Planilha com macro que envia, pelo Outlook, a **agenda da semana de auditorias de
laboratório** para cada GO (gerente operacional). Um GO com vários polos recebe
**um e-mail só**, com todos os polos dele. Remetente: `auditoria.academica@kroton.com.br`.

Depois do disparo, abre um painel (`previews\_WHATSAPP.html`) com um botão por GO
que abre o WhatsApp Web com a mensagem de aviso já digitada. O telefone vem da aba
**Contatos**. O WhatsApp não envia sozinho: é preciso clicar em enviar em cada conversa.

## Arquivos

| Arquivo | O que é |
|---|---|
| `Disparador_auditoria_automatizado_FINAL(1).xlsm` | **a planilha que se usa** |
| `Modulo1_import.bas`, `Modulo2_import.bas` | cópia do código das macros (Modulo1 = disparo e prévia; Modulo2 = preenche gerente e contatos a partir da Base_polos) |
| `Modulo1_NOVO.bas`, `Modulo2_NOVO.bas` | versão alternativa dos mesmos módulos |
| `preview_modelo.html`, `preview_layout_novo.html` | modelos do layout do e-mail |
| `previews\` | prévias geradas (uma por GO) |
| `prints\` | imagens de exemplo do aviso por WhatsApp |

## Como usar

1. Abra a `.xlsm` e habilite as macros. Se o Windows bloquear, clique com o botão direito
   no arquivo → Propriedades → marque **Desbloquear**.
2. Preencha a aba **Aba de auditorias** a partir da linha 10:
   A=Polo, B=ID, C=Grupo Econômico, D=Data, E=Gerente, F=E-mail, H=Cópia oculta.
3. Use o botão de **Prévia** para gerar os e-mails em `previews\` sem enviar nada e confira.
4. Depois use o botão de disparo.
