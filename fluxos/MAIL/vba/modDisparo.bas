Attribute VB_Name = "modDisparo"
Option Explicit

' Esqueleto de disparo. O texto do e-mail é um RASCUNHO do Outlook (o
' "modelo"): a pessoa escreve lá, como qualquer e-mail, com {campos} onde quer
' os dados da planilha e {tabela} onde quer a tabela de polos. Para cada
' destinatário o modelo é copiado, os campos são trocados e a cópia é enviada.
' Mesmo motor do Farol das Ondas (Outlook, "Enviar como", pausa anti-spam).
'
' Ordem de uso: Criar/escolher modelo -> Prévia -> Rascunhos (opcional) -> Enviar.
' Linha com Status "Enviado ..." é pulada: dá para parar (Esc) e retomar.
'
' 27/10/2026: o texto já foi escrito numa aba MENSAGEM da planilha e saiu de
' lá. Para quem nunca viu a planilha ficava confuso; escrever e-mail no
' Outlook todo mundo sabe, e imagem, assinatura e anexo vêm de graça.

' Colunas com papel fixo. Qualquer outra coluna da DESTINATARIOS é "livre":
' vira {campo} no texto e coluna da tabela do e-mail.
Private Const FIXAS As String = "|STATUS|ENVIAR?|POLO|NOME|PARA|CC|CCO|ASSUNTO|ANEXO|"

Private Const ROXO As String = "#5B2A86"
Private Const ROXO_CLARO As String = "#F1EBF8"
Private Const COR_TABELA As String = "#6A2C91"
Private Const ROSA As String = "#D6246E"
Private Const VERMELHO As String = "#C62828"
Private Const CINZA As String = "#444444"
Private Const BORDA As String = "#E3E3E3"

Private Const CFG_ID_MODELO As String = "ID do modelo (não mexer)"
Private Const CFG_MODELO As String = "Modelo escolhido"

Private mValores As Object
Private mOutlook As Object
Private mModelo As Object
Private mModeloHtml As String

' -- Modelo --------------------------------------------------------------

' Cria no Outlook um rascunho com o visual do comunicado do Farol, já com os
' {campos}, e deixa ele escolhido como modelo.
Public Sub CriarModelo()
    Dim m As Object
    On Error GoTo Falha
    Set m = AppOutlook().CreateItem(0)
    m.Subject = "[RGC] Pendências dos polos — {nome}"
    m.HTMLBody = ModeloFarolHtml()
    m.Save
    GuardarModelo m
    MsgBox "O modelo vai abrir no Outlook, como um rascunho." & vbLf & vbLf & _
           "Mude o que quiser: textos, cores, partes inteiras. Só mantenha entre chaves o que deve ser trocado para cada pessoa:" & vbLf & _
           "    {nome}   {polo}   {qtd_polos}   {tabela}" & vbLf & _
           "e as colunas que você criar na DESTINATARIOS, ex.: {Prazo}." & vbLf & vbLf & _
           "Quando terminar, feche o e-mail e clique em Sim para salvar.", vbInformation, "Modelo do e-mail"
    m.Display
    Exit Sub
Falha:
    MsgBox "Não consegui criar o modelo no Outlook: " & Err.Description & vbLf & _
           "O Outlook clássico está aberto?", vbExclamation
End Sub

' Usa como modelo o e-mail aberto (ou selecionado) no Outlook.
Public Sub UsarModeloSelecionado()
    Dim ol As Object, it As Object
    Set ol = AppOutlook()
    On Error Resume Next
    Set it = ol.ActiveInspector.CurrentItem
    If it Is Nothing Then Set it = ol.ActiveExplorer.Selection(1)
    On Error GoTo 0
    If it Is Nothing Then
        MsgBox "Abra ou selecione no Outlook o e-mail que vai servir de modelo e clique de novo.", vbExclamation
        Exit Sub
    End If
    If it.Class <> 43 Then
        MsgBox "O item selecionado no Outlook não é um e-mail.", vbExclamation
        Exit Sub
    End If
    If it.Sent Then
        MsgBox "Esse e-mail já foi enviado ou recebido. O modelo precisa ser um RASCUNHO:" & vbLf & _
               "crie um e-mail novo (ou encaminhe esse), feche salvando, selecione o rascunho e clique de novo.", vbExclamation
        Exit Sub
    End If
    it.Save
    GuardarModelo it
    MsgBox "Modelo escolhido: " & it.Subject, vbInformation
End Sub

Private Sub GuardarModelo(ByVal m As Object)
    SetCfg CFG_ID_MODELO, m.EntryID
    SetCfg CFG_MODELO, m.Subject
End Sub

Private Function CarregarModelo() As Boolean
    Dim id As String
    id = Cfg(CFG_ID_MODELO)
    If Len(id) = 0 Then
        MsgBox "Ainda não há modelo de e-mail." & vbLf & _
               "Clique em 'Criar modelo', ou escolha um rascunho seu com 'Usar e-mail selecionado'.", vbExclamation
        Exit Function
    End If
    Set mModelo = Nothing
    On Error Resume Next
    Set mModelo = AppOutlook().Session.GetItemFromID(id)
    On Error GoTo 0
    If mModelo Is Nothing Then
        MsgBox "Não achei o rascunho do modelo no Outlook (foi apagado ou enviado?)." & vbLf & _
               "Crie ou escolha o modelo de novo.", vbExclamation
        Exit Function
    End If
    mModeloHtml = JuntarCamposQuebrados(mModelo.HTMLBody)
    CarregarModelo = True
End Function

' O editor do Outlook às vezes quebra um campo com formatação no meio:
' "{no</span><span>me}". Aqui o campo volta a ficar inteiro.
Private Function JuntarCamposQuebrados(ByVal html As String) As String
    Dim a As Long, b As Long, bruto As String, limpo As String
    a = InStr(InicioDoCorpo(html), html, "{")
    Do While a > 0
        b = InStr(a + 1, html, "}")
        If b = 0 Then Exit Do
        If b - a < 300 Then
            bruto = Mid$(html, a + 1, b - a - 1)
            If InStr(bruto, "<") > 0 Then
                limpo = SemTags(bruto)
                If NomeDeCampo(Decodificar(limpo)) Then
                    html = Left$(html, a) & limpo & Mid$(html, b)
                    b = a + Len(limpo) + 1
                End If
            End If
        End If
        a = InStr(a + 1, html, "{")
    Loop
    JuntarCamposQuebrados = html
End Function

Private Function SemTags(ByVal s As String) As String
    Dim a As Long, b As Long
    a = InStr(s, "<")
    Do While a > 0
        b = InStr(a, s, ">")
        If b = 0 Then Exit Do
        s = Left$(s, a - 1) & Mid$(s, b + 1)
        a = InStr(s, "<")
    Loop
    SemTags = Trim$(Replace(s, "&nbsp;", " "))
End Function

' O <head> do HTML do Outlook tem CSS cheio de chaves; os campos só são
' procurados do <body> em diante.
Private Function InicioDoCorpo(ByVal html As String) As Long
    InicioDoCorpo = InStr(1, html, "<body", vbTextCompare)
    If InicioDoCorpo = 0 Then InicioDoCorpo = 1
End Function

' -- Botões --------------------------------------------------------------

Public Sub Previa()
    Executar "previa"
End Sub

Public Sub Rascunhos()
    Executar "rascunho"
End Sub

Public Sub Enviar()
    Executar "enviar"
End Sub

Private Sub Executar(ByVal modo As String)
    Dim ws As Worksheet, cols As Object, rotulos As Object, grupos As Object, tabCols As Collection
    Dim chave As Variant, nOk As Long, nErro As Long

    Set ws = ThisWorkbook.Worksheets(ABA_DEST)
    Set rotulos = CreateObject("Scripting.Dictionary")
    Set cols = ColunasDest(ws, rotulos)
    If Not cols.Exists("PARA") Then
        MsgBox "A aba DESTINATARIOS precisa de uma coluna Para (na linha " & LINHA_CAB & ").", vbExclamation
        Exit Sub
    End If
    Set tabCols = ColunasTabela(cols)
    If tabCols Is Nothing Then Exit Sub
    If Not CarregarModelo() Then Exit Sub

    Application.StatusBar = "Montando os e-mails..."
    Set grupos = MontarGrupos(ws, cols)
    If grupos.Count = 0 Then
        Application.StatusBar = False
        MsgBox "Nenhuma linha para enviar (vazias, com Enviar? = N ou já enviadas).", vbInformation
        Exit Sub
    End If
    For Each chave In grupos.Keys
        Preparar grupos(chave), tabCols, rotulos
        If Len(grupos(chave)("erro")) > 0 Then nErro = nErro + 1 Else nOk = nOk + 1
    Next
    Application.StatusBar = False

    If modo = "previa" Then
        GravarPrevias grupos, ws, cols
    Else
        Despachar grupos, ws, cols, modo, nOk, nErro
    End If
End Sub

' -- Leitura da planilha -------------------------------------------------

' Linhas com o mesmo Para (e o mesmo Assunto) viram UM e-mail, com uma linha
' por polo na tabela — como o Farol faz por gestor. Desligável na CONFIG.
Private Function MontarGrupos(ByVal ws As Worksheet, ByVal cols As Object) As Object
    Dim grupos As Object, g As Object, linha As Object, c As Variant, a As Variant
    Dim r As Long, chave As String, agrupar As Boolean, ruim As String

    Set grupos = CreateObject("Scripting.Dictionary")
    agrupar = Not Nao(Cfg("Agrupar linhas do mesmo destinatário"))

    For r = LINHA_CAB + 1 To UltimaLinha(ws)
        Set linha = CreateObject("Scripting.Dictionary")
        For Each c In cols.Keys
            linha(c) = TextoCelula(ws.Cells(r, cols(c)))
        Next
        If Incluir(linha) Then
            linha("_ROW") = r
            If agrupar And Len(LimparEmails(linha("PARA"))) > 0 Then
                chave = LCase$(LimparEmails(linha("PARA"))) & "|" & linha("ASSUNTO")
            Else
                chave = "L" & r
            End If

            If Not grupos.Exists(chave) Then
                Set g = CreateObject("Scripting.Dictionary")
                g("erro") = ""
                g("assunto") = linha("ASSUNTO")
                Set g("para") = CreateObject("Scripting.Dictionary")
                Set g("cc") = CreateObject("Scripting.Dictionary")
                Set g("cco") = CreateObject("Scripting.Dictionary")
                Set g("anexos") = CreateObject("Scripting.Dictionary")
                Set g("linhas") = New Collection
                ruim = SomarEmails(g("para"), linha("PARA"))
                If Len(ruim) > 0 Then Erro g, "e-mail inválido em Para: " & ruim
                ruim = SomarEmails(g("cc"), Cfg("CC em todos os e-mails"))
                If Len(ruim) > 0 Then Erro g, "e-mail inválido na CONFIG (CC): " & ruim
                ruim = SomarEmails(g("cco"), Cfg("CCO em todos os e-mails"))
                If Len(ruim) > 0 Then Erro g, "e-mail inválido na CONFIG (CCO): " & ruim
                If Len(Cfg("Anexo em todos os e-mails")) > 0 Then g("anexos")(Cfg("Anexo em todos os e-mails")) = True
                grupos.Add chave, g
            End If

            Set g = grupos(chave)
            g("linhas").Add linha
            ruim = SomarEmails(g("cc"), linha("CC"))
            If Len(ruim) > 0 Then Erro g, "e-mail inválido em CC: " & ruim
            ruim = SomarEmails(g("cco"), linha("CCO"))
            If Len(ruim) > 0 Then Erro g, "e-mail inválido em CCO: " & ruim
            For Each a In Split(linha("ANEXO"), ";")
                If Len(Trim$(a)) > 0 Then g("anexos")(Trim$(a)) = True
            Next
        End If
    Next
    Set MontarGrupos = grupos
End Function

Private Function Incluir(ByVal linha As Object) As Boolean
    Dim k As Variant, temAlgo As Boolean
    For Each k In linha.Keys
        If k <> "STATUS" And k <> "ENVIAR?" And Len(linha(k)) > 0 Then temAlgo = True: Exit For
    Next
    If Not temAlgo Then Exit Function
    If Nao(linha("ENVIAR?")) Then Exit Function
    If Left$(Normalizar(linha("STATUS")), 7) = "ENVIADO" Then Exit Function
    Incluir = True
End Function

Private Sub Erro(ByVal g As Object, ByVal texto As String)
    If Len(g("erro")) = 0 Then g("erro") = texto
End Sub

' Colunas da {tabela}: as da CONFIG, ou Polo + todas as colunas livres.
Private Function ColunasTabela(ByVal cols As Object) As Collection
    Dim c As New Collection, p As Variant, k As String, chave As Variant, faltam As String, lista As String
    lista = Cfg("Colunas da tabela")
    If Len(lista) > 0 Then
        For Each p In Split(Replace(lista, ",", ";"), ";")
            k = Normalizar(CStr(p))
            If Len(k) > 0 Then
                If cols.Exists(k) Then c.Add k Else faltam = faltam & " """ & Trim$(p) & """"
            End If
        Next
        If Len(faltam) > 0 Then
            MsgBox "CONFIG > Colunas da tabela cita coluna(s) que não existem na DESTINATARIOS:" & faltam, vbExclamation
            Exit Function
        End If
    Else
        If cols.Exists("POLO") Then c.Add "POLO"
        For Each chave In cols.Keys
            If InStr(FIXAS, "|" & chave & "|") = 0 Then c.Add chave
        Next
    End If
    Set ColunasTabela = c
End Function

' Valores para os {campos}: o primeiro não vazio entre as linhas do e-mail,
' mais {polo} (todos, separados por vírgula) e {qtd_polos}.
Private Function ValoresDoGrupo(ByVal g As Object) As Object
    Dim v As Object, polos As Object, linha As Variant, k As Variant, p As String
    Set v = CreateObject("Scripting.Dictionary")
    Set polos = CreateObject("Scripting.Dictionary")
    For Each linha In g("linhas")
        For Each k In linha.Keys
            If Len(v(k)) = 0 Then v(k) = linha(k)
        Next
        p = linha("POLO")
        If Len(p) > 0 And Not polos.Exists(Normalizar(p)) Then polos.Add Normalizar(p), p
    Next
    v("POLO") = Join(polos.Items, ", ")
    If polos.Count > 0 Then v("QTD_POLOS") = CStr(polos.Count) Else v("QTD_POLOS") = ""
    v("PARA") = Lista(g("para"))
    Set ValoresDoGrupo = v
End Function

Private Sub Preparar(ByVal g As Object, ByVal tabCols As Collection, ByVal rotulos As Object)
    Dim tpl As String, falta As String, a As Variant, k As Variant, ini As Long
    Set mValores = ValoresDoGrupo(g)

    If g("para").Count = 0 Then Erro g, "sem e-mail em Para"
    ' quem está no Para não precisa vir de novo em CC/CCO
    For Each k In g("para").Keys
        If g("cc").Exists(k) Then g("cc").Remove k
        If g("cco").Exists(k) Then g("cco").Remove k
    Next

    tpl = g("assunto")
    If Len(tpl) = 0 Then tpl = Cfg("Assunto padrão")
    If Len(tpl) = 0 Then tpl = mModelo.Subject
    If Len(tpl) = 0 Then Erro g, "sem assunto (coluna Assunto, Assunto padrão da CONFIG ou assunto do modelo)"
    g("assunto_final") = Campos(tpl, mValores, falta, False)

    ini = InicioDoCorpo(mModeloHtml)
    g("html") = Left$(mModeloHtml, ini - 1) & _
                Campos(TrocarTabela(Mid$(mModeloHtml, ini), TabelaHtml(g, tabCols, rotulos)), mValores, falta, True)
    If Len(falta) > 0 Then Erro g, "campo vazio ou inexistente:" & falta

    For Each a In g("anexos").Keys
        If Not ArquivoExiste(CStr(a)) Then Erro g, "anexo não encontrado: " & a
    Next
End Sub

' -- HTML ----------------------------------------------------------------

' Troca {tabela} pela tabela. Se o campo está sozinho num parágrafo, troca o
' parágrafo inteiro: tabela dentro de <p> o Outlook desmonta.
Private Function TrocarTabela(ByVal corpo As String, ByVal tabela As String) As String
    Dim p As Long, ini As Long, fim As Long
    p = InStr(1, corpo, "{tabela}", vbTextCompare)
    Do While p > 0
        ini = InStrRev(corpo, "<p", p, vbTextCompare)
        fim = InStr(p, corpo, "</p>", vbTextCompare)
        If ini > 0 And fim > 0 And InStr(ini + 2, Left$(corpo, p), "</p", vbTextCompare) = 0 _
           And Len(Trim$(SemTags(Mid$(corpo, ini, fim - ini)))) = 8 Then
            corpo = Left$(corpo, ini - 1) & tabela & Mid$(corpo, fim + 4)
            p = InStr(ini + Len(tabela), corpo, "{tabela}", vbTextCompare)
        Else
            corpo = Left$(corpo, p - 1) & tabela & Mid$(corpo, p + 8)
            p = InStr(p + Len(tabela), corpo, "{tabela}", vbTextCompare)
        End If
    Loop
    TrocarTabela = corpo
End Function

' Uma linha por linha da planilha, com o cabeçalho roxo do Farol.
Private Function TabelaHtml(ByVal g As Object, ByVal tabCols As Collection, ByVal rotulos As Object) As String
    Dim h As String, k As Variant, linha As Variant, v As String, peso As String
    If tabCols.Count = 0 Then Exit Function

    h = "<table width='100%' cellpadding='0' cellspacing='0' style='border:1px solid " & BORDA & ";border-collapse:collapse;font-family:Arial,Helvetica,sans-serif'>" & _
        "<tr style='background:" & COR_TABELA & "'>"
    For Each k In tabCols
        h = h & "<td style='background:" & COR_TABELA & ";padding:9px 14px'><span style='color:#fff;font-size:11px;font-weight:bold'>" & Esc(UCase$(rotulos(k))) & "</span></td>"
    Next
    h = h & "</tr>"

    For Each linha In g("linhas")
        h = h & "<tr>"
        peso = "bold"     ' 1ª coluna em negrito, como o polo no Farol
        For Each k In tabCols
            v = linha(k)
            If Len(v) = 0 Then v = "&mdash;" Else v = Paragrafos(Marcas(Esc(v)))
            h = h & "<td style='padding:10px 14px;border-bottom:1px solid " & BORDA & ";font-size:13px;font-weight:" & peso & ";color:" & CINZA & "'>" & v & "</td>"
            peso = "normal"
        Next
        h = h & "</tr>"
    Next
    TabelaHtml = h & "</table>"
End Function

Private Function Card(ByVal rotulo As String, ByVal valor As String) As String
    Card = "<td style='padding:14px 20px'><span style='font-size:10px;font-weight:bold;color:" & ROXO & ";letter-spacing:0.5px'>" & rotulo & "</span><br/>" & _
           "<span style='font-size:15px;font-weight:bold;color:#222'>" & valor & "</span></td>"
End Function

Private Function Bloco(ByVal conteudo As String, ByVal topo As Long) As String
    Bloco = "<tr><td style='padding:" & topo & "px 34px 0'>" & conteudo & "</td></tr>"
End Function

' Ponto de partida do "Criar modelo": o comunicado do Farol, com os textos de
' exemplo e os {campos}. Daqui em diante quem manda é o rascunho no Outlook.
Private Function ModeloFarolHtml() As String
    Dim h As String
    Const AREA As String = "Regula&ccedil;&atilde;o e Controle de Polos e Unidades"
    Const SUBAREA As String = "Alian&ccedil;a Jovens e Adultos"

    h = "<html><head><meta charset='UTF-8'></head>" & _
        "<body style='margin:0;padding:0;background:#eef0f2;font-family:Arial,Helvetica,sans-serif'>" & _
        "<table width='100%' cellpadding='0' cellspacing='0' style='background:#eef0f2;padding:24px 0'><tr><td align='center'>" & _
        "<table width='820' cellpadding='0' cellspacing='0' style='background:#fff;border-radius:6px'>"

    h = h & "<tr><td style='background:" & ROXO_CLARO & ";padding:18px 34px'><table width='100%'><tr><td>" & _
        "<span style='font-size:15px;font-weight:bold;color:" & ROXO & "'>-RGC &nbsp;&#9679;&#9679;</span><br/>" & _
        "<span style='font-size:13px;font-weight:bold;color:" & ROXO & "'>" & AREA & "</span><br/>" & _
        "<span style='font-size:12px;color:#6b6b6b'>" & SUBAREA & "</span></td>" & _
        "<td style='text-align:right;vertical-align:middle'><span style='font-size:11px;font-weight:bold;color:" & ROXO & ";letter-spacing:1px'>DOCUMENTO OFICIAL</span></td>" & _
        "</tr></table></td></tr>"

    h = h & Bloco("<span style='font-size:11px;font-weight:bold;color:" & ROSA & ";letter-spacing:1px'>COMUNICADO</span><br/>" & _
                  "<span style='font-size:21px;font-weight:bold;color:#222'>Pend&ecirc;ncias dos Polos</span>", 22)

    h = h & Bloco("<table width='100%' style='background:" & ROXO_CLARO & ";border-radius:5px'><tr>" & _
                  Card("GESTOR(A) DE POLOS", "{nome}") & Card("POLOS NESTE E-MAIL", "{qtd_polos}") & "</tr></table>", 16)

    h = h & Bloco("<span style='font-size:13.5px;color:" & CINZA & ";line-height:1.65'>Ol&aacute;, {nome}! Este comunicado re&uacute;ne as pend&ecirc;ncias " & _
                  "dos polos da sua carteira que precisam de aten&ccedil;&atilde;o. Confira abaixo cada uma delas e o prazo para regulariza&ccedil;&atilde;o.</span>", 16)

    h = h & Bloco("<span style='font-size:14px;font-weight:bold;color:" & COR_TABELA & ";letter-spacing:0.5px'>Situa&ccedil;&atilde;o por polo</span>", 24)
    h = h & "<tr><td style='padding:9px 34px 0'><p style='margin:0'>{tabela}</p></td></tr>"

    h = h & Bloco("<table width='100%' style='background:#FDECEC;border:1px solid #f5cfcf;border-radius:5px'><tr><td style='padding:16px 20px'>" & _
                  "<span style='font-size:13px;font-weight:bold;color:" & VERMELHO & "'>&#9200;&nbsp; PRAZO</span>" & _
                  "<p style='margin:10px 0 0;font-size:13px;color:" & CINZA & ";line-height:1.8'>&#9679;&nbsp; Regulariza&ccedil;&atilde;o das pend&ecirc;ncias listadas: " & _
                  "<b style='color:" & VERMELHO & "'>at&eacute; a data indicada na tabela</b></p></td></tr></table>", 26)

    h = h & Bloco("<table width='100%' style='background:#fafafa;border:1px solid #eee;border-radius:5px'><tr><td style='padding:16px 20px'>" & _
                  "<span style='font-size:13px;color:" & CINZA & ";line-height:1.65'>Contamos com o seu compromisso para resolvermos os pontos de cada polo " & _
                  "dentro do prazo. Qualquer dificuldade, nos avise o quanto antes para que possamos ajudar.</span>" & _
                  "<p style='font-size:12.5px;color:" & CINZA & ";line-height:1.6;margin:10px 0 0'>&#128222;&nbsp; <b>D&uacute;vidas:</b><br/>" & _
                  "&nbsp;&nbsp;&#9679;&nbsp; Regula&ccedil;&atilde;o e Controle &mdash; documentos.suporteecontrole@kroton.com.br</p></td></tr></table>", 18)

    h = h & "<tr><td style='padding:22px 34px'><table width='100%' style='border-top:1px solid #eee'><tr>" & _
        "<td style='padding-top:14px'><span style='font-size:12px;font-weight:bold;color:" & ROXO & "'>" & AREA & "<br/>" & SUBAREA & "</span></td>" & _
        "<td style='padding-top:14px;text-align:right;vertical-align:bottom'><span style='font-size:20px;color:#9b8fc4'>cogna</span> " & _
        "<span style='font-size:20px;font-weight:bold;color:" & ROXO & "'>educa&ccedil;&atilde;o</span></td></tr></table>" & _
        "<span style='font-size:9px;color:#bbb'>Comunicado interno</span></td></tr>"

    ModeloFarolHtml = h & "</table></td></tr></table></body></html>"
End Function

' -- Prévia --------------------------------------------------------------

' Um HTML por e-mail em ./previews, mais um 000_INDICE.html com a lista de
' quem recebe o quê. A pasta é limpa antes: no Farol, preview velho de quem
' saiu da lista ficava lá dentro misturado com os novos.
Private Sub GravarPrevias(ByVal grupos As Object, ByVal ws As Worksheet, ByVal cols As Object)
    Dim pasta As String, chave As Variant, g As Object, n As Long, arq As String, idx As String, situacao As String

    If Len(ThisWorkbook.Path) = 0 Then
        MsgBox "Salve a planilha primeiro: a prévia é gravada numa pasta ao lado dela.", vbExclamation
        Exit Sub
    End If
    pasta = ThisWorkbook.Path & "\previews"
    If Len(Dir(pasta, vbDirectory)) = 0 Then MkDir pasta
    On Error Resume Next
    Kill pasta & "\*.html"
    On Error GoTo 0

    idx = "<html><head><meta charset='UTF-8'></head><body style='font-family:Arial;font-size:13px;padding:20px'>" & _
          "<h2 style='color:" & ROXO & "'>Prévia do disparo &middot; " & grupos.Count & " e-mail(s) &middot; " & Format$(Now, "dd/mm/yyyy hh:nn") & "</h2>" & _
          "<p style='color:#777'>Modelo: " & Esc(mModelo.Subject) & ". Imagens coladas no modelo não aparecem aqui, só no e-mail.</p>" & _
          "<table cellpadding='6' style='border-collapse:collapse' border='1'><tr style='background:" & ROXO_CLARO & "'>" & _
          "<th>#</th><th>Para</th><th>CC</th><th>CCO</th><th>Assunto</th><th>Linhas</th><th>Situação</th></tr>"

    For Each chave In grupos.Keys
        Set g = grupos(chave)
        n = n + 1
        arq = Format$(n, "000") & "_" & NomeDeArquivo(IIf(Len(Lista(g("para"))) > 0, Lista(g("para")), "SEM_PARA")) & ".html"
        GravarTexto pasta & "\" & arq, g("html")
        If Len(g("erro")) > 0 Then
            situacao = "<b style='color:" & VERMELHO & "'>N&Atilde;O SAI: " & Esc(g("erro")) & "</b>"
            StatusGrupo ws, cols, g, "ERRO: " & g("erro")
        Else
            situacao = "<span style='color:#2E7D32'>ok</span>"
            StatusGrupo ws, cols, g, "Prévia ok " & Format$(Now, "dd/mm hh:nn")
        End If
        idx = idx & "<tr><td><a href='" & arq & "'>" & n & "</a></td><td>" & Esc(Lista(g("para"))) & "</td><td>" & Esc(Lista(g("cc"))) & "</td>" & _
              "<td>" & Esc(Lista(g("cco"))) & "</td><td>" & Esc(g("assunto_final")) & "</td><td>" & g("linhas").Count & "</td><td>" & situacao & "</td></tr>"
    Next
    GravarTexto pasta & "\000_INDICE.html", idx & "</table></body></html>"
    ThisWorkbook.FollowHyperlink pasta & "\000_INDICE.html"
End Sub

Private Sub GravarTexto(ByVal caminho As String, ByVal s As String)
    Dim f As Integer
    f = FreeFile
    Open caminho For Output As #f
    Print #f, ParaAscii(s);
    Close #f
End Sub

' -- Envio real / rascunhos ----------------------------------------------

Private Sub Despachar(ByVal grupos As Object, ByVal ws As Worksheet, ByVal cols As Object, ByVal modo As String, ByVal nOk As Long, ByVal nErro As Long)
    Dim intervalo As Long, aviso As String, chave As Variant, g As Object
    Dim feitos As Long, enviados As Long, falhas As Long, res As String, t0 As Date, resto As Double

    If nOk = 0 Then
        MsgBox "Todos os e-mails estão com erro. Rode a Prévia e veja a coluna Status.", vbExclamation
        Exit Sub
    End If
    intervalo = Val(Cfg("Intervalo entre envios (segundos)"))
    If intervalo < 0 Then intervalo = 0

    If modo = "enviar" Then
        aviso = "ENVIAR DE VERDADE " & nOk & " e-mail(s)?" & vbLf & vbLf & _
                "Tempo estimado: ~" & Duracao(nOk * (intervalo + 2)) & ". Não feche o Outlook durante o envio." & vbLf & _
                "Para parar no meio, aperte Esc: o que já saiu fica marcado como Enviado."
    Else
        aviso = "Criar " & nOk & " rascunho(s) no Outlook, com os destinatários reais?"
    End If
    If nErro > 0 Then aviso = aviso & vbLf & vbLf & nErro & " e-mail(s) com erro serão pulados (veja a coluna Status)."
    If MsgBox(aviso, vbYesNo + vbQuestion, "Disparo") <> vbYes Then Exit Sub

    Application.EnableCancelKey = xlErrorHandler
    On Error GoTo Interrompido
    t0 = Now

    For Each chave In grupos.Keys
        Set g = grupos(chave)
        If Len(g("erro")) > 0 Then
            StatusGrupo ws, cols, g, "ERRO: " & g("erro")
        Else
            feitos = feitos + 1
            Application.StatusBar = Progresso(feitos - 1, nOk, t0) & " · agora: " & Lista(g("para"))
            res = EnviarUm(Lista(g("para")), Lista(g("cc")), Lista(g("cco")), g("assunto_final"), g("html"), g("anexos"), modo)
            If Len(res) = 0 Then
                enviados = enviados + 1
                StatusGrupo ws, cols, g, IIf(modo = "enviar", "Enviado ", "Rascunho ") & Format$(Now, "dd/mm hh:nn")
            Else
                falhas = falhas + 1
                StatusGrupo ws, cols, g, "ERRO no envio: " & res
            End If
            Registrar modo, Lista(g("para")), Lista(g("cc")), Lista(g("cco")), g("assunto_final"), IIf(res = "", "ok", res)

            If modo = "enviar" And feitos < nOk Then
                resto = intervalo
                Do While resto > 0
                    Application.StatusBar = Progresso(feitos, nOk, t0) & " · próximo em " & resto & "s"
                    Application.Wait Now + TimeSerial(0, 0, 1)
                    DoEvents
                    resto = resto - 1
                Loop
            End If
        End If
    Next

Fim:
    On Error Resume Next
    ForcarEnvio
    Application.StatusBar = False
    Application.EnableCancelKey = xlInterrupt
    MsgBox IIf(modo = "enviar", "Enviados: ", "Rascunhos criados: ") & enviados & vbLf & _
           "Falhas: " & falhas & vbLf & "Pulados por erro: " & nErro & vbLf & vbLf & _
           "Tudo registrado na coluna Status e na aba LOG.", vbInformation
    Exit Sub

Interrompido:
    If Err.Number = 18 Then
        If MsgBox("Parar o disparo agora?" & vbLf & "(o que já saiu está marcado como Enviado)", vbYesNo + vbQuestion) = vbYes Then Resume Fim
        Resume
    End If
    MsgBox "Erro inesperado: " & Err.Description, vbExclamation
    Resume Fim
End Sub

Private Function Progresso(ByVal feitos As Long, ByVal total As Long, ByVal t0 As Date) As String
    Dim ritmo As Double, seg As Double
    Progresso = "Disparo " & feitos & "/" & total
    If feitos > 0 Then
        ritmo = (Now - t0) * 86400 / feitos
        seg = (total - feitos) * ritmo
        Progresso = Progresso & " · faltam ~" & Duracao(seg) & " (fim ~" & Format$(Now + seg / 86400, "hh:nn") & ")"
    End If
End Function

Private Sub StatusGrupo(ByVal ws As Worksheet, ByVal cols As Object, ByVal g As Object, ByVal texto As String)
    Dim linha As Variant, cel As Range
    If Not cols.Exists("STATUS") Then Exit Sub
    For Each linha In g("linhas")
        Set cel = ws.Cells(linha("_ROW"), cols("STATUS"))
        cel.Value = texto
        If Left$(texto, 4) = "ERRO" Then
            cel.Font.Color = RGB(198, 40, 40)
        ElseIf Left$(texto, 7) = "Enviado" Then
            cel.Font.Color = RGB(46, 125, 50)
        Else
            cel.Font.Color = RGB(68, 68, 68)
        End If
    Next
End Sub

Private Sub Registrar(ByVal modo As String, ByVal para As String, ByVal cc As String, ByVal cco As String, ByVal assunto As String, ByVal resultado As String)
    Dim ws As Worksheet, r As Long
    Set ws = ThisWorkbook.Worksheets(ABA_LOG)
    r = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row + 1
    ws.Cells(r, 1).Value = Now
    ws.Cells(r, 2).Value = modo
    ws.Cells(r, 3).Value = para
    ws.Cells(r, 4).Value = cc
    ws.Cells(r, 5).Value = cco
    ws.Cells(r, 6).Value = assunto
    ws.Cells(r, 7).Value = resultado
End Sub

' -- Outlook -------------------------------------------------------------

Private Function AppOutlook() As Object
    Dim vivo As String
    ' A conexão fica guardada entre uma execução e outra. Se o Outlook foi
    ' fechado/reaberto nesse meio tempo, ela morre e o envio falha com "A
    ' máquina do servidor remoto não existe ou não está disponível" (erro 462).
    If Not mOutlook Is Nothing Then
        On Error Resume Next
        vivo = mOutlook.Name
        If Err.Number <> 0 Then Set mOutlook = Nothing
        On Error GoTo 0
    End If
    If mOutlook Is Nothing Then
        On Error Resume Next
        Set mOutlook = GetObject(, "Outlook.Application")
        On Error GoTo 0
        If mOutlook Is Nothing Then
            Set mOutlook = CreateObject("Outlook.Application")
            mOutlook.GetNamespace("MAPI").Logon
            ' Recém-aberto, o Outlook recusa o 1º envio com "Falha na execução
            ' do servidor" (Farol, 06/10/2026). Dá tempo para ele subir.
            Application.StatusBar = "Abrindo o Outlook..."
            Application.Wait Now + TimeSerial(0, 0, 8)
            Application.StatusBar = False
        End If
    End If
    Set AppOutlook = mOutlook
End Function

' Copia o modelo (vem junto o que ele tiver: imagens, assinatura, anexos),
' troca o corpo e envia. Devolve "" se deu certo, ou a mensagem de erro.
' Tenta duas vezes.
Private Function EnviarUm(ByVal para As String, ByVal cc As String, ByVal cco As String, ByVal assunto As String, _
                          ByVal html As String, ByVal anexos As Object, ByVal modo As String) As String
    Dim tentativa As Long, m As Object, pa As Object, a As Variant, de As String, nomeDe As String

    For tentativa = 1 To 2
        On Error GoTo Falhou
        Set m = Nothing
        Set m = mModelo.Copy

        ' "Enviar como" uma caixa compartilhada, pelo PropertyAccessor.
        ' SentOnBehalfOfName NÃO funciona aqui: o servidor devolve NDR.
        de = Cfg("Enviar como (e-mail)")
        If Len(de) > 0 Then
            nomeDe = Cfg("Nome do remetente")
            If Len(nomeDe) = 0 Then nomeDe = de
            Set pa = m.PropertyAccessor
            pa.SetProperty "http://schemas.microsoft.com/mapi/proptag/0x0042001F", nomeDe
            pa.SetProperty "http://schemas.microsoft.com/mapi/proptag/0x0065001F", de
            pa.SetProperty "http://schemas.microsoft.com/mapi/proptag/0x0064001F", "SMTP"
            pa.SetProperty "http://schemas.microsoft.com/mapi/proptag/0x0C1A001F", nomeDe
            pa.SetProperty "http://schemas.microsoft.com/mapi/proptag/0x0C1F001F", de
            pa.SetProperty "http://schemas.microsoft.com/mapi/proptag/0x0C1E001F", "SMTP"
        End If

        m.To = para
        m.CC = cc
        m.BCC = cco
        m.Subject = assunto
        m.HTMLBody = html
        For Each a In anexos.Keys
            m.Attachments.Add CStr(a)
        Next
        If modo = "rascunho" Then
            m.Save
        Else
            m.Send
            ForcarEnvio
        End If
        EnviarUm = ""
        Exit Function
Falhou:
        EnviarUm = Err.Description
        Resume Seguir
Seguir:
        ' a cópia que falhou não fica largada nos Rascunhos
        On Error Resume Next
        If Not m Is Nothing Then m.Delete
        On Error GoTo 0
        If tentativa = 1 Then
            Application.Wait Now + TimeSerial(0, 0, 5)
            ' a 2ª tentativa reconecta do zero (e o modelo vem da conexão nova)
            Set mOutlook = Nothing
            On Error Resume Next
            Set mModelo = AppOutlook().Session.GetItemFromID(Cfg(CFG_ID_MODELO))
            On Error GoTo 0
        End If
    Next
End Function

' Empurra a fila do Outlook; sem isso o Outlook novo represa os e-mails.
Private Sub ForcarEnvio()
    Dim s As Object, i As Long
    On Error Resume Next
    Set s = AppOutlook().GetNamespace("MAPI").SyncObjects
    For i = 1 To s.Count
        s.Item(i).Start
    Next
End Sub
