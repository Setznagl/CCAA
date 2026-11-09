Attribute VB_Name = "Modulo1"
' ======================================================================
'  DISPARADOR - AUDITORIA DE LABORATORIOS  -  agenda semanal para os GOs
'
'  Substitui o Modulo1 antigo. A MECANICA E A MESMA:
'    - le a aba "Aba de auditorias" a partir da linha 10
'    - colunas  A=Polo  B=ID  C=Grupo Economico  D=Data  E=Gerente
'               F=E-mail  G=Auditor (nao usado)  H=Copia oculta
'    - agrupa por e-mail (um GO com varios polos recebe UM e-mail)
'    - envia pelo Outlook com SentOnBehalfOfName
'
'  O QUE MUDOU: o corpo do e-mail passou a usar o modelo institucional
'  (mesmo layout do Comunicado Consolidado), e ganhou um botao de PREVIA
'  que gera os e-mails em arquivo sem mandar nada.
'
'  11/09/2026 - AVISO POR WHATSAPP. Depois do disparo, abre um painel
'  (previews\_WHATSAPP.html) com um botao por GO que abre o WhatsApp Web
'  ja com a mensagem digitada, avisando que o e-mail foi enviado. O
'  telefone vem da aba Contatos (coluna C), buscado pelo e-mail do GO.
'  O WhatsApp nao permite envio automatico sem a API paga: ela clica em
'  enviar em cada conversa. Quem nao tem telefone aparece listado.
' ======================================================================

Option Explicit

' -- CONFIGURACAO ------------------------------------------------------
Private Const EMAIL_REMETENTE As String = "auditoria.academica@kroton.com.br"
Private Const ASSUNTO        As String = "[RGC] Auditoria de Laboratórios - Agenda da Semana"
Private Const AREA_MACRO     As String = "Regularização e Gestão de Contratos"
Private Const SUB_AREA       As String = "Auditoria de Laboratórios"
Private Const LINK_ATEND     As String = "https://app.smartsheet.com/b/form/019c71b513a67973be44a973a3ee479a"
Private Const ABA_DADOS      As String = "Aba de auditorias"
Private Const PRIMEIRA_LINHA As Long = 10

' -- WHATSAPP ----------------------------------------------------------
Private Const ABA_CONTATOS   As String = "Contatos"
Private Const CONT_COL_NOME  As Long = 1    ' A
Private Const CONT_COL_TEL   As Long = 3    ' C
Private Const CONT_COL_EMAIL As Long = 4    ' D
' web.whatsapp.com abre direto no navegador. Para deixar o Windows escolher
' entre o app e o navegador, troque por "https://wa.me/" (o "?text=" vira
' o primeiro parametro - a montagem em LinkWhats trata os dois).
Private Const WHATS_URL      As String = "https://web.whatsapp.com/send?phone="
Private Const WHATS_ARQUIVO  As String = "_WHATSAPP.html"
' Assinatura da mensagem. E ela quem manda pelo proprio WhatsApp.
Private Const WHATS_ASSINATURA As String = "Auditoria de Laboratórios" & vbLf & _
                                           "Regularização e Gestão de Contratos (RGC)"

' -- PALETA (a mesma do comunicado consolidado) ------------------------
Private Const ROXO       As String = "#5B2A86"
Private Const ROXO_CLARO As String = "#F1EBF8"
Private Const LABS_HDR   As String = "#5C3D9E"
Private Const VERMELHO   As String = "#C62828"
Private Const AMBAR      As String = "#B26A00"
Private Const CINZA_TXT  As String = "#444444"
Private Const BORDA      As String = "#E3E3E3"
Private Const LISTRA     As String = "#FAF8FD"   ' listra alternada da tabela


' ======================================================================
'  BOTAO 1 - PREVIA (nao envia nada; so gera os arquivos e abre o 1o)
' ======================================================================
Public Sub PREVIA_COMUNICADO()
    Disparar True
End Sub


' ======================================================================
'  BOTAO 2 - ENVIO REAL
' ======================================================================
Public Sub ENVIO_COMUNICADO()

    Dim resposta As VbMsgBoxResult

    resposta = MsgBox( _
        "Isto vai ENVIAR os e-mails de verdade para os gerentes." & vbCrLf & vbCrLf & _
        "Já conferiu a prévia?" & vbCrLf & vbCrLf & _
        "Clique em Sim para disparar.", _
        vbYesNo + vbExclamation, "Confirmar disparo")

    If resposta <> vbYes Then Exit Sub

    Disparar False

End Sub


' ======================================================================
'  MOTOR - usado pelos dois botoes
' ======================================================================
Private Sub Disparar(ByVal modoPrevia As Boolean)

    Dim ws As Worksheet
    Dim olApp As Object, olMail As Object

    Dim dLinhas As Object, dBCC As Object, dGerente As Object
    Dim dQtd As Object, dMin As Object, dMax As Object
    Dim dTel As Object, dTelBruto As Object, dItens As Object
    Dim comTel As Long, semTel As Long

    Dim ultimaLinha As Long, i As Long
    Dim nomePolo As String, grupo As String, gerente As String
    Dim emailDestino As String, emailBCC As String
    Dim dataTxt As String, dataVal As Variant
    Dim chave As Variant, sCorpo As String
    Dim enviados As Long, validos As Long, ignorados As Long
    Dim pastaPrevia As String, arq As String, primeiroArq As String
    Dim fnum As Integer
    Dim logDescartes As String

    On Error GoTo TrataErro

    Set ws = ThisWorkbook.Worksheets(ABA_DADOS)

    Set dLinhas = CreateObject("Scripting.Dictionary")
    Set dBCC = CreateObject("Scripting.Dictionary")
    Set dGerente = CreateObject("Scripting.Dictionary")
    Set dQtd = CreateObject("Scripting.Dictionary")
    Set dMin = CreateObject("Scripting.Dictionary")
    Set dMax = CreateObject("Scripting.Dictionary")
    Set dItens = CreateObject("Scripting.Dictionary")

    ' -- ultima linha preenchida --------------------------------------
    ultimaLinha = ws.Cells(ws.Rows.Count, "A").End(xlUp).Row
    If ws.Cells(ws.Rows.Count, "F").End(xlUp).Row > ultimaLinha Then
        ultimaLinha = ws.Cells(ws.Rows.Count, "F").End(xlUp).Row
    End If

    If ultimaLinha < PRIMEIRA_LINHA Then
        MsgBox "A aba """ & ABA_DADOS & """ não tem dados a partir da linha " & _
               PRIMEIRA_LINHA & ".", vbExclamation, "Nada a enviar"
        Exit Sub
    End If

    ' -- LEITURA E AGRUPAMENTO ----------------------------------------
    For i = PRIMEIRA_LINHA To ultimaLinha

        emailDestino = LimparEmail(CStr(ws.Cells(i, 6).Value))
        nomePolo = Trim(CStr(ws.Cells(i, 1).Value))

        ' Polo listado que NAO vai receber comunicado nenhum. O codigo antigo
        ' pulava em silencio: 12 dos 48 polos da rodada de 08/09 cairam aqui e
        ' ninguem soube. Agora fica registrado linha a linha.
        If nomePolo <> "" And Not EmailValido(emailDestino) Then
            ignorados = ignorados + 1
            logDescartes = logDescartes & "linha " & i & vbTab & nomePolo & vbTab & _
                           "gerente: " & Trim(CStr(ws.Cells(i, 5).Value)) & vbTab & _
                           "coluna F: " & Trim(CStr(ws.Cells(i, 6).Value)) & vbCrLf
        End If

        If EmailValido(emailDestino) And nomePolo <> "" Then

            validos = validos + 1

            grupo = Trim(CStr(ws.Cells(i, 3).Value))
            gerente = Trim(CStr(ws.Cells(i, 5).Value))
            emailBCC = LimparEmail(CStr(ws.Cells(i, 8).Value))

            dataVal = ws.Cells(i, 4).Value
            If IsDate(dataVal) Then
                dataTxt = Format(CDate(dataVal), "dd/mm/yyyy")
            Else
                dataTxt = Trim(CStr(dataVal))
                dataVal = Empty
            End If

            ' primeiro registro deste destinatario
            If Not dLinhas.Exists(emailDestino) Then
                dLinhas.Add emailDestino, ""
                dGerente.Add emailDestino, gerente
                dQtd.Add emailDestino, 0
                dMin.Add emailDestino, Empty
                dMax.Add emailDestino, Empty
                dItens.Add emailDestino, ""
            End If

            ' a mesma linha, em texto, para o WhatsApp
            dItens(emailDestino) = dItens(emailDestino) & ItemWhats(nomePolo, dataTxt, dataVal)

            dLinhas(emailDestino) = dLinhas(emailDestino) & _
                                    LinhaTabela(nomePolo, grupo, dataTxt, dataVal, _
                                                CLng(dQtd(emailDestino)) + 1)
            dQtd(emailDestino) = dQtd(emailDestino) + 1

            ' periodo coberto pelo e-mail
            If IsDate(dataVal) Then
                If Not IsDate(dMin(emailDestino)) Then
                    dMin(emailDestino) = CDate(dataVal)
                ElseIf CDate(dataVal) < CDate(dMin(emailDestino)) Then
                    dMin(emailDestino) = CDate(dataVal)
                End If
                If Not IsDate(dMax(emailDestino)) Then
                    dMax(emailDestino) = CDate(dataVal)
                ElseIf CDate(dataVal) > CDate(dMax(emailDestino)) Then
                    dMax(emailDestino) = CDate(dataVal)
                End If
            End If

            ' copia oculta, sem duplicar
            If EmailValido(emailBCC) Then
                If Not dBCC.Exists(emailDestino) Then
                    dBCC.Add emailDestino, emailBCC
                ElseIf InStr(1, dBCC(emailDestino), emailBCC, vbTextCompare) = 0 Then
                    dBCC(emailDestino) = dBCC(emailDestino) & ";" & emailBCC
                End If
            End If

        End If

    Next i

    If dLinhas.Count = 0 Then
        MsgBox "Nenhum destinatário válido foi encontrado." & vbCrLf & vbCrLf & _
               "Última linha lida: " & ultimaLinha & vbCrLf & _
               "Linhas com polo mas sem e-mail válido: " & ignorados & vbCrLf & vbCrLf & _
               "Confira a COLUNA F. Se estiver escrito ""Contato nao encontrado""," & vbCrLf & _
               "rode antes o botão de atualizar dados.", _
               vbExclamation, "Nenhum destinatário"
        Exit Sub
    End If

    ' -- MODO PREVIA: grava os HTML e abre o primeiro ------------------
    If modoPrevia Then

        pastaPrevia = ThisWorkbook.Path & "\previews"
        If Dir(pastaPrevia, vbDirectory) = "" Then MkDir pastaPrevia

        For Each chave In dLinhas.Keys

            sCorpo = MontarHTML(CStr(dGerente(chave)), CStr(dLinhas(chave)), _
                                CLng(dQtd(chave)), dMin(chave), dMax(chave))

            arq = pastaPrevia & "\" & NomeArquivo(CStr(chave)) & ".html"
            If primeiroArq = "" Then primeiroArq = arq

            fnum = FreeFile
            Open arq For Output As #fnum
            Print #fnum, "<!-- Para: " & chave & _
                         "  |  Cco: " & IIf(dBCC.Exists(chave), dBCC(chave), "(nenhum)") & _
                         "  |  Assunto: " & ASSUNTO & " -->"
            ' O Print grava em ANSI (cp1252). O e-mail vai como UTF-8 e o Outlook
            ' resolve, mas o ARQUIVO de previa precisa declarar o que ele realmente e,
            ' senao os acentos aparecem quebrados no navegador.
            Print #fnum, Replace(sCorpo, "charset=""UTF-8""", "charset=""windows-1252""")
            Close #fnum

            enviados = enviados + 1
        Next chave

        ' Relatorio dos polos que ficariam de fora.
        If ignorados > 0 Then
            fnum = FreeFile
            Open pastaPrevia & "\_POLOS_SEM_EMAIL.txt" For Output As #fnum
            Print #fnum, "Polos listados que NÃO receberiam comunicado (" & ignorados & "):"
            Print #fnum, ""
            Print #fnum, logDescartes
            Print #fnum, "Como resolver: o nome na coluna E precisa existir IGUAL na aba"
            Print #fnum, "Contatos (coluna A). Ex.: a base traz 'ANDRE DUARTE' e a Contatos"
            Print #fnum, "tem 'ANDRE MARTINS DUARTE' - nomes diferentes, nao casa."
            Close #fnum
        End If

        ' Painel do WhatsApp em modo previa: mostra quem tem e quem nao tem
        ' telefone, mas com os botoes travados - o e-mail ainda nao foi.
        BuscarTelefones dLinhas, dGerente, dTel, dTelBruto, comTel, semTel
        GerarPainelWhats pastaPrevia, True, dLinhas, dGerente, dQtd, dMin, dItens, dTel, dTelBruto

        MsgBox "Prévia gerada - NADA foi enviado." & vbCrLf & vbCrLf & _
               "E-mails montados: " & enviados & vbCrLf & _
               "Linhas de polo usadas: " & validos & vbCrLf & _
               "POLOS QUE FICARIAM DE FORA: " & ignorados & _
               IIf(ignorados > 0, " (ver _POLOS_SEM_EMAIL.txt)", "") & vbCrLf & vbCrLf & _
               "WhatsApp - GOs com telefone: " & comTel & vbCrLf & _
               "WhatsApp - GOs SEM telefone na Contatos: " & semTel & _
               IIf(semTel > 0, " (ver " & WHATS_ARQUIVO & ")", "") & vbCrLf & vbCrLf & _
               "Arquivos em:" & vbCrLf & pastaPrevia, _
               vbInformation, "Prévia concluída"

        If primeiroArq <> "" Then ThisWorkbook.FollowHyperlink primeiroArq

        Exit Sub

    End If

    ' -- ENVIO REAL ---------------------------------------------------
    Set olApp = CreateObject("Outlook.Application")

    For Each chave In dLinhas.Keys

        sCorpo = MontarHTML(CStr(dGerente(chave)), CStr(dLinhas(chave)), _
                            CLng(dQtd(chave)), dMin(chave), dMax(chave))

        Set olMail = olApp.CreateItem(0)
        With olMail
            .SentOnBehalfOfName = EMAIL_REMETENTE
            .To = chave
            If dBCC.Exists(chave) Then
                If Trim(dBCC(chave)) <> "" Then .BCC = dBCC(chave)
            End If
            .Subject = ASSUNTO
            .HTMLBody = sCorpo
            .Send
        End With
        Set olMail = Nothing

        enviados = enviados + 1
    Next chave

    ' -- AVISO POR WHATSAPP -------------------------------------------
    ' E-mails ja foram. Agora o painel com um botao por GO. Qualquer erro
    ' daqui em diante NAO pode passar a impressao de que o disparo falhou,
    ' por isso o tratamento e separado.
    On Error GoTo TrataErroWhats

    pastaPrevia = ThisWorkbook.Path & "\previews"
    If Dir(pastaPrevia, vbDirectory) = "" Then MkDir pastaPrevia

    BuscarTelefones dLinhas, dGerente, dTel, dTelBruto, comTel, semTel
    GerarPainelWhats pastaPrevia, False, dLinhas, dGerente, dQtd, dMin, dItens, dTel, dTelBruto

    MsgBox "Disparo concluído!" & vbCrLf & vbCrLf & _
           "Remetente: " & EMAIL_REMETENTE & vbCrLf & _
           "E-mails enviados: " & enviados & vbCrLf & _
           "Linhas de polo incluidas: " & validos & vbCrLf & _
           "Linhas descartadas (sem e-mail válido): " & ignorados & vbCrLf & vbCrLf & _
           "AVISO POR WHATSAPP" & vbCrLf & _
           "GOs com telefone: " & comTel & vbCrLf & _
           "GOs SEM telefone na Contatos: " & semTel & vbCrLf & vbCrLf & _
           "Ao clicar em OK abre o painel com um botão por GO." & vbCrLf & _
           "Cada botão abre o WhatsApp Web com a mensagem pronta - " & vbCrLf & _
           "é só conferir e clicar em enviar.", _
           vbInformation, "Envio concluído"

    ThisWorkbook.FollowHyperlink pastaPrevia & "\" & WHATS_ARQUIVO

    Exit Sub

TrataErroWhats:
    On Error Resume Next
    Close
    MsgBox "Os " & enviados & " e-mails FORAM ENVIADOS normalmente." & vbCrLf & vbCrLf & _
           "Só o painel do WhatsApp deu erro:" & vbCrLf & _
           "Número: " & Err.Number & vbCrLf & _
           "Descrição: " & Err.Description, _
           vbExclamation, "E-mails enviados; painel do WhatsApp falhou"
    Exit Sub

TrataErro:
    On Error Resume Next
    Close
    MsgBox "A macro encontrou um erro." & vbCrLf & vbCrLf & _
           "Número: " & Err.Number & vbCrLf & _
           "Descrição: " & Err.Description & vbCrLf & vbCrLf & _
           "E-mails já enviados antes do erro: " & enviados, _
           vbCritical, "Erro no disparo"

End Sub


' ======================================================================
'  UMA LINHA DA TABELA
'  Data no passado sai em vermelho: auditoria que ficou para tras.
' ======================================================================
Private Function LinhaTabela(ByVal polo As String, ByVal grupo As String, _
                             ByVal dataTxt As String, ByVal dataVal As Variant, _
                             ByVal indice As Long) As String

    Dim celData As String
    Dim estiloBase As String
    Dim fundo As String
    Dim faixa As String
    Dim diaSemana As String

    ' Listra alternada. E o unico jeito de a linha nao escorregar quando o GO
    ' tem muitos polos. O Outlook respeita background inline em <td>.
    If indice Mod 2 = 0 Then
        fundo = "background:" & LISTRA & ";"
    Else
        fundo = "background:#ffffff;"
    End If

    ' A faixa lateral repete o estado da data: roxa normal, ambar sem data,
    ' vermelha vencida. Da para varrer a coluna sem ler as datas.
    faixa = ROXO

    estiloBase = fundo & "padding:11px 14px;border-bottom:1px solid " & BORDA & ";font-size:13px;"

    If dataTxt = "" Then
        faixa = AMBAR
        celData = "<td style=""" & estiloBase & "text-align:center;font-weight:bold;color:" & _
                  AMBAR & """>A marcar</td>"
    ElseIf IsDate(dataVal) Then
        ' "dddd" usa o idioma do Windows: em pt-BR sai "terça-feira".
        diaSemana = LCase(Format(CDate(dataVal), "dddd"))
        If CDate(dataVal) < Date Then
            faixa = VERMELHO
            celData = "<td style=""" & estiloBase & "text-align:center"">" & _
                      "<span style=""font-weight:bold;color:" & VERMELHO & """>" & dataTxt & "</span><br/>" & _
                      "<span style=""font-size:10.5px;color:" & VERMELHO & """>data já passou</span></td>"
        Else
            celData = "<td style=""" & estiloBase & "text-align:center"">" & _
                      "<span style=""font-weight:bold;color:" & CINZA_TXT & """>" & dataTxt & "</span><br/>" & _
                      "<span style=""font-size:10.5px;color:#8a8a8a"">" & diaSemana & "</span></td>"
        End If
    Else
        celData = "<td style=""" & estiloBase & "text-align:center;color:" & CINZA_TXT & """>" & _
                  Esc(dataTxt) & "</td>"
    End If

    LinhaTabela = "<tr>" & _
        "<td style=""" & fundo & "padding:11px 0 11px 14px;border-bottom:1px solid " & BORDA & _
        ";border-left:3px solid " & faixa & ";font-size:12px;color:#a9a9a9"">" & CStr(indice) & "</td>" & _
        "<td style=""" & estiloBase & "font-weight:bold;color:" & ROXO & """>" & Esc(polo) & "</td>" & _
        "<td style=""" & estiloBase & "color:" & CINZA_TXT & """>" & Esc(NaoVazio(grupo)) & "</td>" & _
        celData & "</tr>"

End Function


' ======================================================================
'  O E-MAIL - modelo institucional
' ======================================================================
Private Function MontarHTML(ByVal gerente As String, ByVal linhas As String, _
                            ByVal qtd As Long, ByVal dtMin As Variant, _
                            ByVal dtMax As Variant) As String

    Dim s As String
    Dim nome As String
    Dim periodo As String
    Dim rotuloPolos As String
    Dim preheader As String

    nome = Trim(gerente)
    If nome = "" Then nome = "Gerente Operacional"

    ' periodo coberto pelas auditorias deste e-mail
    If IsDate(dtMin) And IsDate(dtMax) Then
        If CDate(dtMin) = CDate(dtMax) Then
            periodo = Format(CDate(dtMin), "dd/mm/yyyy")
        Else
            periodo = Format(CDate(dtMin), "dd/mm") & " a " & Format(CDate(dtMax), "dd/mm/yyyy")
        End If
    Else
        periodo = "A definir"
    End If

    If qtd = 1 Then
        rotuloPolos = "polo"
    Else
        rotuloPolos = "polos"
    End If

    ' Texto que aparece na LISTA da caixa de entrada, ao lado do assunto.
    If IsDate(dtMin) Then
        preheader = CStr(qtd) & " auditoria(s) de laboratório na sua carteira. " & _
                    "Próxima: " & LCase(Format(CDate(dtMin), "dddd")) & ", " & _
                    Format(CDate(dtMin), "dd/mm") & "."
    Else
        preheader = CStr(qtd) & " auditoria(s) de laboratório na sua carteira."
    End If

    s = "<html><head><meta charset=""UTF-8""></head>"
    s = s & "<body style=""margin:0;padding:0;background:#eef0f2;font-family:Arial,Helvetica,sans-serif"">"

    ' -- PREHEADER (invisivel dentro do e-mail) ------------------------
    s = s & "<div style=""display:none;font-size:1px;color:#eef0f2;line-height:1px;"
    s = s & "max-height:0;max-width:0;opacity:0;overflow:hidden"">" & Esc(preheader) & "</div>"

    s = s & "<table width=""100%"" cellpadding=""0"" cellspacing=""0"" style=""background:#eef0f2;padding:24px 0"">"
    s = s & "<tr><td align=""center"">"
    s = s & "<table width=""780"" cellpadding=""0"" cellspacing=""0"" style=""background:#ffffff;border-radius:6px"">"

    ' -- FAIXA SUPERIOR ------------------------------------------------
    s = s & "<tr><td style=""background:" & ROXO_CLARO & ";padding:18px 34px"">"
    s = s & "<table width=""100%""><tr><td>"
    s = s & "<span style=""font-size:15px;font-weight:bold;color:" & ROXO & """>-RGC &nbsp;&#9679;&#9679;</span><br/>"
    s = s & "<span style=""font-size:13px;font-weight:bold;color:" & ROXO & """>" & AREA_MACRO & "</span><br/>"
    s = s & "<span style=""font-size:12px;color:#6b6b6b"">" & SUB_AREA & "</span>"
    s = s & "</td><td style=""text-align:right;vertical-align:middle"">"
    s = s & "<span style=""font-size:11px;font-weight:bold;color:" & ROXO & ";letter-spacing:1px"">DOCUMENTO OFICIAL</span>"
    s = s & "</td></tr></table></td></tr>"

    ' -- TITULO --------------------------------------------------------
    s = s & "<tr><td style=""padding:22px 34px 0"">"
    s = s & "<span style=""font-size:11px;font-weight:bold;color:" & LABS_HDR & ";letter-spacing:1px"">AGENDA SEMANAL DE AUDITORIAS</span><br/>"
    s = s & "<span style=""font-size:21px;font-weight:bold;color:#222"">Auditoria de Laboratórios &mdash; Polos da sua carteira</span>"
    s = s & "</td></tr>"

    ' -- IDENTIFICACAO -------------------------------------------------
    ' Divisorias entre os tres cartoes: antes eles se fundiam num tapete
    ' roxo so. O numero de auditorias virou numeral grande.
    s = s & "<tr><td style=""padding:16px 34px 0"">"
    s = s & "<table width=""100%"" cellpadding=""0"" cellspacing=""0"" style=""background:" & ROXO_CLARO & ";border-radius:5px""><tr>"
    s = s & "<td width=""46%"" style=""padding:14px 20px;border-right:1px solid #ddd2ec"">"
    s = s & "<span style=""font-size:10px;font-weight:bold;color:" & ROXO & ";letter-spacing:0.5px"">GERENTE OPERACIONAL</span><br/>"
    s = s & "<span style=""font-size:15px;font-weight:bold;color:#222"">" & Esc(nome) & "</span></td>"
    s = s & "<td width=""32%"" style=""padding:14px 20px;border-right:1px solid #ddd2ec"">"
    s = s & "<span style=""font-size:10px;font-weight:bold;color:" & ROXO & ";letter-spacing:0.5px"">PERÍODO</span><br/>"
    s = s & "<span style=""font-size:15px;font-weight:bold;color:#222"">" & periodo & "</span></td>"
    s = s & "<td width=""22%"" style=""padding:14px 20px"">"
    s = s & "<span style=""font-size:10px;font-weight:bold;color:" & ROXO & ";letter-spacing:0.5px"">AUDITORIAS</span><br/>"
    s = s & "<span style=""font-size:24px;font-weight:bold;color:" & ROXO & ";line-height:1.1"">" & CStr(qtd) & "</span> "
    s = s & "<span style=""font-size:13px;color:#6b6b6b"">" & rotuloPolos & "</span></td>"
    s = s & "</tr></table></td></tr>"

    ' -- INTRO ---------------------------------------------------------
    s = s & "<tr><td style=""padding:18px 34px 0"">"
    s = s & "<span style=""font-size:13.5px;color:" & CINZA_TXT & ";line-height:1.65"">"
    s = s & "Olá, " & Esc(nome) & "! Segue a relação dos polos da sua carteira que serão auditados "
    s = s & "pela equipe de <b>Auditoria de Laboratórios</b>. Pedimos que reforce diretamente com "
    s = s & "os gestores a importância do recebimento e do apoio às equipes em campo."
    s = s & "</span></td></tr>"

    ' -- TABELA --------------------------------------------------------
    s = s & "<tr><td style=""padding:26px 34px 0"">"
    s = s & "<span style=""font-size:14px;font-weight:bold;color:" & LABS_HDR & ";letter-spacing:0.5px"">"
    s = s & "&#128197;&nbsp; AUDITORIAS PROGRAMADAS</span>"
    s = s & "<span style=""font-size:11.5px;color:#8a8a8a"">&nbsp; &middot; &nbsp;em ordem de data</span>"
    s = s & "</td></tr>"
    s = s & "<tr><td style=""padding:9px 34px 0"">"
    s = s & "<table width=""100%"" cellpadding=""0"" cellspacing=""0"" style=""border:1px solid " & BORDA & ";border-collapse:collapse"">"
    s = s & "<tr style=""background:" & LABS_HDR & """>"
    s = s & "<td width=""34"" style=""padding:9px 0 9px 14px""><span style=""color:#c9b8e6;font-size:11px;font-weight:bold"">#</span></td>"
    s = s & "<td style=""padding:9px 14px""><span style=""color:#fff;font-size:11px;font-weight:bold"">POLO</span></td>"
    s = s & "<td style=""padding:9px 14px""><span style=""color:#fff;font-size:11px;font-weight:bold"">GRUPO ECONÔMICO</span></td>"
    s = s & "<td width=""150"" style=""padding:9px 14px;text-align:center""><span style=""color:#fff;font-size:11px;font-weight:bold"">DATA DA AUDITORIA</span></td>"
    s = s & "</tr>"
    s = s & linhas
    s = s & "</table></td></tr>"

    ' -- ORIENTACOES ---------------------------------------------------
    ' Deixou de ser caixa VERMELHA: no modelo institucional o vermelho quer
    ' dizer prazo/urgencia, e isto aqui e uma lista de orientacoes. O
    ' vermelho ficou reservado para a data vencida, na tabela.
    s = s & "<tr><td style=""padding:26px 34px 0"">"
    s = s & "<table width=""100%"" cellpadding=""0"" cellspacing=""0"" style=""background:#F7F4FC;border:1px solid #e4dcf2;border-radius:5px""><tr>"
    s = s & "<td style=""padding:16px 20px"">"
    s = s & "<span style=""font-size:13px;font-weight:bold;color:" & ROXO & """>&#9989;&nbsp; REFORCE COM OS GESTORES DOS POLOS</span>"
    s = s & "<table cellpadding=""0"" cellspacing=""0"" style=""margin-top:10px"">"
    s = s & ItemOrientacao("Disponibilizar acesso facilitado às instalações no dia e horário agendados;")
    s = s & ItemOrientacao("Garantir a presença de um responsável pelo polo durante todo o período da auditoria;")
    s = s & ItemOrientacao("Manter a documentação de infraestrutura (laudos, ARTs, licenças) organizada e disponível;")
    s = s & ItemOrientacao("Assegurar que laboratórios, insumos e equipamentos estejam limpos e em condições de uso.")
    s = s & "</table>"
    s = s & "</td></tr></table></td></tr>"

    ' -- CANAL ---------------------------------------------------------
    ' Virou botao. Era um link de 12,5px no meio do texto, facil de perder.
    ' Botao feito com tabela, que e o que o Outlook renderiza.
    s = s & "<tr><td style=""padding:24px 34px 0"">"
    s = s & "<table cellpadding=""0"" cellspacing=""0""><tr>"
    s = s & "<td style=""background:" & LABS_HDR & ";border-radius:4px;padding:11px 22px"">"
    s = s & "<a href=""" & LINK_ATEND & """ style=""font-size:13px;font-weight:bold;color:#ffffff;text-decoration:none"">"
    s = s & "Abrir chamado com a equipe de auditoria</a></td>"
    s = s & "<td style=""padding-left:16px""><span style=""font-size:11.5px;color:#8a8a8a"">Reagendamentos e impedimentos por aqui</span></td>"
    s = s & "</tr></table></td></tr>"

    ' -- FECHAMENTO ----------------------------------------------------
    s = s & "<tr><td style=""padding:20px 34px 0"">"
    s = s & "<table width=""100%"" cellpadding=""0"" cellspacing=""0"" style=""background:#fafafa;border:1px solid #eee;border-radius:5px""><tr>"
    s = s & "<td style=""padding:16px 20px"">"
    s = s & "<span style=""font-size:13px;color:" & CINZA_TXT & ";line-height:1.65"">"
    s = s & "Qualquer reagendamento ou impedimento deve ser comunicado à nossa equipe com a maior "
    s = s & "antecedência possível, para não impactarmos o cronograma. Contamos com o seu apoio."
    s = s & "</span></td></tr></table></td></tr>"

    ' -- RODAPE --------------------------------------------------------
    s = s & "<tr><td style=""padding:22px 34px"">"
    s = s & "<table width=""100%"" style=""border-top:1px solid #eee""><tr>"
    s = s & "<td style=""padding-top:14px"">"
    s = s & "<span style=""font-size:12px;font-weight:bold;color:" & ROXO & """>" & AREA_MACRO & "<br/>" & SUB_AREA & "</span></td>"
    s = s & "<td style=""padding-top:14px;text-align:right;vertical-align:bottom"">"
    s = s & "<span style=""font-size:20px;color:#9b8fc4"">cogna</span>"
    s = s & "<span style=""font-size:20px;font-weight:bold;color:" & ROXO & """>educação</span></td>"
    s = s & "</tr></table>"
    s = s & "<span style=""font-size:9px;color:#bbb"">Público &middot; Comunicado interno &middot; Modelo institucional</span>"
    s = s & "</td></tr>"

    s = s & "</table></td></tr></table></body></html>"

    MontarHTML = s

End Function


' Um marcador da caixa de orientacoes. Virou tabela para que a linha longa
' quebre alinhada, em vez de voltar embaixo do bullet.
Private Function ItemOrientacao(ByVal texto As String) As String
    ItemOrientacao = "<tr>" & _
        "<td style=""padding:3px 8px 3px 0;vertical-align:top"">" & _
        "<span style=""color:" & LABS_HDR & ";font-size:13px"">&#9679;</span></td>" & _
        "<td style=""padding:3px 0;font-size:13px;color:" & CINZA_TXT & ";line-height:1.55"">" & _
        texto & "</td></tr>"
End Function

' ======================================================================
'  WHATSAPP
' ======================================================================

' Procura o telefone de cada destinatario na aba Contatos.
'
' A busca e pelo E-MAIL (coluna D), que e a chave do agrupamento: se o
' e-mail foi resolvido, o telefone da mesma linha e o certo. Se por algum
' motivo o e-mail nao esta na Contatos, tenta pelo NOME (coluna A), com a
' mesma normalizacao que o Modulo2 usa para casar os dois.
'
' dTel      -> chave = e-mail do GO, valor = so digitos com 55 na frente
' dTelBruto -> o que estava escrito na celula, para mostrar no painel
Private Sub BuscarTelefones(ByVal dLinhas As Object, ByVal dGerente As Object, _
                            ByRef dTel As Object, ByRef dTelBruto As Object, _
                            ByRef comTel As Long, ByRef semTel As Long)

    Dim wsC As Worksheet
    Dim porEmail As Object, porNome As Object
    Dim ultima As Long, i As Long
    Dim em As String, nm As String, tel As String
    Dim chave As Variant

    Set dTel = CreateObject("Scripting.Dictionary")
    Set dTelBruto = CreateObject("Scripting.Dictionary")
    Set porEmail = CreateObject("Scripting.Dictionary")
    Set porNome = CreateObject("Scripting.Dictionary")

    comTel = 0
    semTel = 0

    On Error Resume Next
    Set wsC = ThisWorkbook.Worksheets(ABA_CONTATOS)
    On Error GoTo 0

    If Not wsC Is Nothing Then
        ultima = wsC.Cells(wsC.Rows.Count, CONT_COL_NOME).End(xlUp).Row
        For i = 1 To ultima
            tel = Trim(Replace(CStr(wsC.Cells(i, CONT_COL_TEL).Value), Chr(160), " "))
            If tel <> "" Then
                em = LimparEmail(CStr(wsC.Cells(i, CONT_COL_EMAIL).Value))
                nm = NormalizarNome(wsC.Cells(i, CONT_COL_NOME).Value)
                ' primeira ocorrencia vale (a Contatos tem gerente repetido)
                If em <> "" Then If Not porEmail.Exists(em) Then porEmail.Add em, tel
                If nm <> "" Then If Not porNome.Exists(nm) Then porNome.Add nm, tel
            End If
        Next i
    End If

    For Each chave In dLinhas.Keys
        tel = ""
        If porEmail.Exists(chave) Then
            tel = porEmail(chave)
        Else
            nm = NormalizarNome(dGerente(chave))
            If porNome.Exists(nm) Then tel = porNome(nm)
        End If

        dTelBruto.Add chave, tel
        dTel.Add chave, TelefoneWhats(tel)

        If dTel(chave) <> "" Then
            comTel = comTel + 1
        Else
            semTel = semTel + 1
        End If
    Next chave

End Sub


' Reduz o telefone ao formato que o WhatsApp aceita: so digitos, com o
' codigo do pais e sem o "+". A Contatos tem de tudo: "(61) 99289-7603",
' "19981719355", "(31) 98313-1366 ", "(41)-99999-9999"...
' Devolve "" quando nao da para confiar no numero.
Private Function TelefoneWhats(ByVal t As String) As String

    Dim i As Long, d As String, c As String

    For i = 1 To Len(t)
        c = Mid(t, i, 1)
        If c >= "0" And c <= "9" Then d = d & c
    Next i

    ' "0" de operadora na frente do DDD: ninguem digita isso no WhatsApp.
    If Len(d) = 12 Or Len(d) = 11 Then
        If Left(d, 1) = "0" Then d = Mid(d, 2)
    End If

    Select Case Len(d)
        Case 10, 11                       ' DDD + numero (fixo ou celular)
            TelefoneWhats = "55" & d
        Case 12, 13                       ' ja veio com o 55
            If Left(d, 2) = "55" Then TelefoneWhats = d
        Case Else
            TelefoneWhats = ""
    End Select

End Function


' O texto que vai aparecer digitado na conversa: o mesmo conteudo do
' e-mail, em versao curta - a lista de polos com data e as orientacoes.
' *asteriscos* e o negrito do proprio WhatsApp.
Private Function MensagemWhats(ByVal gerente As String, ByVal qtd As Long, _
                               ByVal dtMin As Variant, ByVal itens As String) As String

    Dim primeiro As String, s As String

    primeiro = PrimeiroNome(gerente)

    s = "Prezado(a) " & primeiro & "," & vbLf & vbLf
    s = s & "Informamos que foi encaminhada ao seu e-mail a agenda de Auditoria de Laboratórios "
    If qtd = 1 Then
        s = s & "referente a 1 polo da sua carteira"
    Else
        s = s & "referente a " & CStr(qtd) & " polos da sua carteira"
    End If
    s = s & ". Segue o resumo:" & vbLf & vbLf
    s = s & "*AUDITORIAS PROGRAMADAS*" & vbLf
    s = s & itens & vbLf
    s = s & "Solicitamos que reforce com os gestores dos polos a importância do recebimento "
    s = s & "e do apoio às equipes em campo: acesso às instalações no dia e horário agendados, "
    s = s & "responsável presente durante a auditoria e documentação de infraestrutura "
    s = s & "(laudos, ARTs, licenças) disponível." & vbLf & vbLf
    s = s & "Eventuais impedimentos ou necessidades de reagendamento devem ser comunicados "
    s = s & "à nossa equipe com a maior antecedência possível." & vbLf & vbLf
    s = s & "Atenciosamente," & vbLf & WHATS_ASSINATURA

    MensagemWhats = s

End Function


' Uma linha da lista do WhatsApp. Mesmos tres estados da tabela do e-mail:
' data futura, "A marcar" e data que ja passou.
Private Function ItemWhats(ByVal polo As String, ByVal dataTxt As String, _
                           ByVal dataVal As Variant) As String
    Dim quando As String
    If dataTxt = "" Then
        quando = "A marcar"
    ElseIf IsDate(dataVal) Then
        quando = Format(CDate(dataVal), "dd/mm") & " (" & LCase(Format(CDate(dataVal), "dddd")) & ")"
        If CDate(dataVal) < Date Then quando = quando & " - data já passou"
    Else
        quando = dataTxt
    End If
    ItemWhats = "- " & polo & ": " & quando & vbLf
End Function


' Link que abre o WhatsApp Web ja com a conversa e o texto.
' EncodeURL grava em UTF-8, entao os acentos da mensagem chegam certos
' mesmo com o arquivo do painel gravado em ANSI.
Private Function LinkWhats(ByVal telDigitos As String, ByVal texto As String) As String
    Dim sep As String
    If InStr(1, WHATS_URL, "?") > 0 Then sep = "&" Else sep = "?"
    LinkWhats = WHATS_URL & telDigitos & sep & "text=" & _
                Application.WorksheetFunction.EncodeURL(texto)
End Function


Private Function PrimeiroNome(ByVal nome As String) As String
    nome = Trim(nome)
    ' "TBD - FULANO" e como a base marca gerente provisorio
    If UCase(Left(nome, 5)) = "TBD -" Then nome = Trim(Mid(nome, 6))
    If nome = "" Then
        PrimeiroNome = "Gerente"
    Else
        PrimeiroNome = StrConv(Split(nome, " ")(0), vbProperCase)
    End If
End Function


' O painel: uma linha por GO com botao "Abrir WhatsApp". Quem nao tem
' telefone vai para uma lista separada, para ela avisar por outro canal.
' Em modo previa os botoes ficam travados - o e-mail ainda nao foi.
Private Sub GerarPainelWhats(ByVal pasta As String, ByVal modoPrevia As Boolean, _
                             ByVal dLinhas As Object, ByVal dGerente As Object, _
                             ByVal dQtd As Object, ByVal dMin As Object, _
                             ByVal dItens As Object, _
                             ByVal dTel As Object, ByVal dTelBruto As Object)

    Dim fnum As Integer
    Dim chave As Variant
    Dim s As String, linhasCom As String, linhasSem As String
    Dim n As Long, nomeGO As String, polos As String

    For Each chave In dLinhas.Keys
        nomeGO = Trim(CStr(dGerente(chave)))
        If nomeGO = "" Then nomeGO = CStr(chave)
        polos = CStr(dQtd(chave)) & IIf(CLng(dQtd(chave)) = 1, " polo", " polos")

        If dTel(chave) <> "" Then
            n = n + 1
            linhasCom = linhasCom & "<tr>" & _
                "<td class=""n"">" & n & "</td>" & _
                "<td><b>" & Esc(nomeGO) & "</b><br><span class=""m"">" & Esc(CStr(chave)) & "</span></td>" & _
                "<td class=""tel"">" & Esc(CStr(dTelBruto(chave))) & "</td>" & _
                "<td>" & polos & "</td>" & _
                "<td class=""acao"">"
            If modoPrevia Then
                linhasCom = linhasCom & "<span class=""btn off"" title=""Na prévia o botão fica travado"">Abrir WhatsApp</span>"
            Else
                linhasCom = linhasCom & "<a class=""btn"" target=""_blank"" rel=""noopener"" href=""" & _
                    LinkWhats(CStr(dTel(chave)), MensagemWhats(nomeGO, CLng(dQtd(chave)), _
                                                              dMin(chave), CStr(dItens(chave)))) & _
                    """>Abrir WhatsApp</a>"
            End If
            linhasCom = linhasCom & "</td></tr>"
        Else
            linhasSem = linhasSem & "<tr>" & _
                "<td><b>" & Esc(nomeGO) & "</b><br><span class=""m"">" & Esc(CStr(chave)) & "</span></td>" & _
                "<td class=""tel"">" & IIf(Trim(CStr(dTelBruto(chave))) = "", "&mdash; vazio na Contatos", _
                                          Esc(CStr(dTelBruto(chave))) & " &nbsp;(número inválido)") & "</td>" & _
                "<td>" & polos & "</td></tr>"
        End If
    Next chave

    s = "<!DOCTYPE html><html lang=""pt-BR""><head><meta charset=""windows-1252"">"
    s = s & "<title>Aviso por WhatsApp - Auditoria de Laboratórios</title>"
    s = s & "<style>"
    s = s & "body{margin:0;padding:28px 16px;background:#eef0f2;font-family:Arial,Helvetica,sans-serif;color:" & CINZA_TXT & "}"
    s = s & ".box{max-width:860px;margin:0 auto;background:#fff;border-radius:6px;padding:26px 34px 30px}"
    s = s & "h1{font-size:20px;color:#222;margin:4px 0 4px}"
    s = s & ".sup{font-size:11px;font-weight:bold;letter-spacing:1px;color:" & LABS_HDR & "}"
    s = s & ".sub{font-size:13px;color:#6b6b6b;margin:0 0 18px}"
    s = s & ".aviso{background:#F7F4FC;border:1px solid #e4dcf2;border-radius:5px;padding:12px 16px;font-size:13px;line-height:1.55;margin-bottom:18px}"
    s = s & ".aviso.prev{background:#FFF6E5;border-color:#F0D9A8;color:" & AMBAR & "}"
    s = s & "h2{font-size:13px;color:" & LABS_HDR & ";letter-spacing:.5px;margin:22px 0 8px}"
    s = s & "table{width:100%;border-collapse:collapse;border:1px solid " & BORDA & ";font-size:13px}"
    s = s & "th{background:" & LABS_HDR & ";color:#fff;font-size:11px;text-align:left;padding:9px 12px}"
    s = s & "td{padding:10px 12px;border-bottom:1px solid " & BORDA & ";vertical-align:middle}"
    s = s & "tr:nth-child(even) td{background:" & LISTRA & "}"
    s = s & "td.n{color:#a9a9a9;font-size:12px;width:24px}"
    s = s & "td.tel{white-space:nowrap;font-family:Consolas,monospace;font-size:12.5px}"
    s = s & "td.acao{text-align:right;white-space:nowrap}"
    s = s & ".m{font-size:11.5px;color:#8a8a8a}"
    s = s & ".btn{display:inline-block;background:#25D366;color:#fff;font-weight:bold;font-size:12.5px;"
    s = s & "padding:8px 16px;border-radius:4px;text-decoration:none}"
    s = s & ".btn:hover{background:#1DA851}"
    s = s & ".btn.off{background:#cfcfcf;cursor:not-allowed}"
    s = s & "tr.feito td{background:#EDF9F0 !important}"
    s = s & "tr.feito .btn{background:#8fd9a8}"
    s = s & "tr.feito .btn:after{content:' \2713'}"
    s = s & ".sem th{background:" & AMBAR & "}"
    s = s & ".rod{margin-top:22px;font-size:11px;color:#bbb}"
    s = s & "</style></head><body><div class=""box"">"

    s = s & "<div class=""sup"">AUDITORIA DE LABORATÓRIOS &middot; " & Format(Now, "dd/mm/yyyy hh:nn") & "</div>"
    s = s & "<h1>Aviso por WhatsApp para os GOs</h1>"
    s = s & "<p class=""sub"">" & dLinhas.Count & " e-mail(s) " & IIf(modoPrevia, "montado(s) na prévia", "enviado(s)") & _
            " &nbsp;&middot;&nbsp; " & n & " com telefone &nbsp;&middot;&nbsp; " & (dLinhas.Count - n) & " sem telefone</p>"

    If modoPrevia Then
        s = s & "<div class=""aviso prev""><b>PRÉVIA - o e-mail ainda NÃO foi enviado.</b> Este painel serve só para " & _
                "conferir quem tem telefone. Depois do envio real ele abre de novo, com os botões liberados.</div>"
    Else
        s = s & "<div class=""aviso"">Cada botão abre o <b>WhatsApp Web</b> na conversa do gerente, já com a mensagem " & _
                "digitada. <b>Confira e clique em enviar</b> lá dentro - o WhatsApp não manda sozinho. " & _
                "A linha fica verde quando o botão já foi clicado.</div>"
    End If

    s = s & "<h2>&#128241;&nbsp; GOS COM TELEFONE</h2>"
    If n > 0 Then
        s = s & "<table><tr><th>#</th><th>Gerente</th><th>Telefone</th><th>Polos</th><th></th></tr>" & linhasCom & "</table>"
    Else
        s = s & "<p class=""m"">Nenhum dos destinatários tem telefone na aba Contatos.</p>"
    End If

    If linhasSem <> "" Then
        s = s & "<h2 style=""color:" & AMBAR & """>&#9888;&nbsp; SEM TELEFONE NA ABA CONTATOS &mdash; avisar por outro canal</h2>"
        s = s & "<table class=""sem""><tr><th>Gerente</th><th>Telefone</th><th>Polos</th></tr>" & linhasSem & "</table>"
        s = s & "<p class=""m"">Para resolver: preencher a coluna C (Telefone) da aba Contatos na linha do gerente, com DDD.</p>"
    End If

    s = s & "<div class=""rod"">" & AREA_MACRO & " &middot; " & SUB_AREA & " &middot; gerado pelo disparador</div>"
    s = s & "</div>"
    ' marca a linha como feita quando o botao e clicado
    s = s & "<script>document.querySelectorAll('a.btn').forEach(function(a){"
    s = s & "a.addEventListener('click',function(){a.closest('tr').classList.add('feito');});});</script>"
    s = s & "</body></html>"

    fnum = FreeFile
    Open pasta & "\" & WHATS_ARQUIVO For Output As #fnum
    Print #fnum, s
    Close #fnum

End Sub


' ======================================================================
'  AUXILIARES
' ======================================================================

' Escapa caracteres que quebram o HTML (o "&" de "P&D", por exemplo).
Private Function Esc(ByVal t As String) As String
    t = Replace(t, "&", "&amp;")
    t = Replace(t, "<", "&lt;")
    t = Replace(t, ">", "&gt;")
    Esc = t
End Function

Private Function NaoVazio(ByVal t As String) As String
    If Trim(t) = "" Then
        NaoVazio = "-"
    Else
        NaoVazio = Trim(t)
    End If
End Function

' Nome de arquivo seguro para a previa.
Private Function NomeArquivo(ByVal t As String) As String
    Dim c As Variant
    For Each c In Array("\", "/", ":", "*", "?", """", "<", ">", "|", "@", ".")
        t = Replace(t, c, "_")
    Next c
    NomeArquivo = t
End Function

' Normaliza o endereco antes de virar chave de agrupamento.
'
' POR QUE ISTO EXISTE: na aba Contatos ha celulas de e-mail com ponto e virgula
' sobrando ("joao.boiani@cogna.com.br;") e com espaco no fim
' ("gislaine.simoes@cogna.com.br "). O codigo antigo agrupava pela string crua,
' entao o MESMO gerente virava DUAS chaves diferentes e recebia DOIS e-mails,
' cada um com parte dos polos. Alem disso o ";" no fim faz o Outlook interpretar
' um segundo destinatario vazio.
Private Function LimparEmail(ByVal t As String) As String

    t = Replace(t, Chr(160), " ")   ' espaco fixo, comum em texto colado
    t = Trim(LCase(t))

    ' tira ";" e "," sobrando nas pontas
    Do While Len(t) > 0
        If Right(t, 1) = ";" Or Right(t, 1) = "," Or Right(t, 1) = " " Then
            t = Trim(Left(t, Len(t) - 1))
        Else
            Exit Do
        End If
    Loop

    LimparEmail = t

End Function

Public Function EmailValido(ByVal endereco As String) As Boolean

    Dim posArroba As Long, posPonto As Long

    endereco = Trim(endereco)
    If endereco = "" Then Exit Function

    ' A macro de atualizacao escreve estes textos na coluna F quando falha.
    If InStr(1, endereco, "encontrado", vbTextCompare) > 0 Then Exit Function

    posArroba = InStr(1, endereco, "@")
    posPonto = InStrRev(endereco, ".")

    EmailValido = (posArroba > 1 And posPonto > posArroba + 1)

End Function
