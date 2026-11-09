# Disparo de E-mails — esqueleto

Planilha com macro para quem quiser disparar um comunicado com o visual do
Farol das Ondas, escolhendo destinatários, cópias, assunto e texto. As
instruções para quem usa estão na aba **COMO USAR** da própria planilha.

| Arquivo | O que é |
|---|---|
| `Disparo de E-mails.xlsm` | a planilha que vai para o pessoal |
| `vba/*.bas` | o código das macros (fonte de verdade) |
| `montar_planilha.py` | monta o `.xlsm` a partir do `vba/` |
| `EXEMPLO - prévia do e-mail.html` | como o e-mail sai com o modelo padrão (dados fictícios); abra no navegador |

## De onde vem o texto do e-mail

De um **rascunho do Outlook** (o "modelo"). O botão *Criar modelo* gera um
no estilo do comunicado do Farol, e a pessoa edita no próprio Outlook. Para
cada destinatário o rascunho é copiado (vêm juntos imagens, assinatura e
anexos), os `{campos}` são trocados e o `{tabela}` vira a tabela de polos.

Até 27/10/2026 o texto era escrito numa aba MENSAGEM da planilha. Saiu
porque, para quem nunca tinha visto a planilha, ficava confuso.

## Para mudar o código

Edite o `.bas`, apague (ou renomeie) o `.xlsm` e rode `python montar_planilha.py`.
O script liga por instantes a opção "Confiar no acesso ao modelo de objeto do
VBA", importa os módulos e devolve a opção ao que era.

## O que veio do Farol

- Envio pelo Outlook com "Enviar como" via `PropertyAccessor`
  (`SentOnBehalfOfName` dá NDR), pausa anti-spam e espera de 8s quando o
  Outlook acabou de abrir.
- Prévia e Teste antes do envio real. Um `{campo}` vazio barra a linha,
  como a trava do "até DD/MM".
- Busca na Master: mesmas colunas, `limpar_emails`, `limpar_nome_pessoa` e a
  busca de consultor/GO por nome com cargo. O que vem da Master fica azul.

## Novo em relação ao Farol

- A coluna **Status** registra o que já saiu. Rodar de novo pula quem tem
  "Enviado…", então dá para parar com Esc e retomar.
- Aba **LOG** com cada envio.
