Attribute VB_Name = "modMaster"
Option Explicit

' Preenche Para / Nome / CC das linhas que têm Polo e estão sem Para, a partir
' da Base de Polos - Master. Tudo o que vier de lá fica pintado de AZUL, para
' ser conferido antes do envio: a Master já mandou comunicado para a pessoa
' errada (RICARDO -> sócios, RENATA -> NATALIA; ver o Farol das Ondas).
'
' Mesmas colunas e regras do Farol: o gestor é o da linha do polo
' (GESTOR DE POLO), o e-mail é o EMAIL GESTOR PRISMA, e consultor/GO saem da
' aba CONTATOS_PARCEIROS, procurados pelo nome.

Private Const AZUL As Long = 16247773     ' RGB(221, 235, 247)

Public Sub BuscarNaMaster()
    Dim ws As Worksheet, cols As Object, alvos As New Collection, r As Long, item As Variant
    Dim caminho As Variant, wb As Workbook, un As Worksheet, ct As Worksheet
    Dim cab As Variant, nCols As Long, nLin As Long
    Dim cPolo As Long, cGestor As Long, cEmail As Long, cCons As Long, cGo As Long
    Dim vPolo As Variant, vGestor As Variant, vEmail As Variant, vCons As Variant, vGo As Variant
    Dim polos As Object, emailsGestor As Object, agenda As Object, d As Object
    Dim i As Long, k As String, g As String, e As String, cc As String, novoCc As String
    Dim nOk As Long, nNao As Long, nConferir As Long, st As String
    Dim copiarCons As Boolean, copiarGo As Boolean

    Set ws = ThisWorkbook.Worksheets(ABA_DEST)
    Set cols = ColunasDest(ws)
    If Not (cols.Exists("POLO") And cols.Exists("PARA")) Then
        MsgBox "A aba DESTINATARIOS precisa das colunas Polo e Para.", vbExclamation
        Exit Sub
    End If
    For r = LINHA_CAB + 1 To UltimaLinha(ws)
        If Len(TextoCelula(ws.Cells(r, cols("POLO")))) > 0 And Len(TextoCelula(ws.Cells(r, cols("PARA")))) = 0 Then alvos.Add r
    Next
    If alvos.Count = 0 Then
        MsgBox "Nenhuma linha com Polo preenchido e Para vazio: nada a buscar.", vbInformation
        Exit Sub
    End If

    caminho = Cfg("Arquivo da Master")
    If Not ArquivoExiste(CStr(caminho)) Then
        caminho = Application.GetOpenFilename("Planilhas do Excel (*.xlsb;*.xlsx;*.xlsm),*.xlsb;*.xlsx;*.xlsm", , "Onde está a Base de Polos - Master?")
        If VarType(caminho) = vbBoolean Then Exit Sub
        SetCfg "Arquivo da Master", CStr(caminho)
    End If
    copiarCons = Sim(Cfg("Copiar consultor de infra (Master)"))
    copiarGo = Sim(Cfg("Copiar GO (Master)"))

    On Error GoTo Falha
    Application.ScreenUpdating = False
    Application.StatusBar = "Abrindo a Master (pode levar 1 minuto)..."
    Set wb = Workbooks.Open(CStr(caminho), UpdateLinks:=0, ReadOnly:=True)

    Set un = AcharAba(wb, "BASE_DE_UNIDADES|BASE DE UNIDADES")
    Set ct = AcharAba(wb, "CONTATOS_PARCEIROS|CONTATOS PARCEIROS")
    If un Is Nothing Then Err.Raise vbObjectError + 1, , "não achei a aba BASE_DE_UNIDADES na Master."

    nCols = un.Cells(1, un.Columns.Count).End(xlToLeft).Column
    cab = un.Range(un.Cells(1, 1), un.Cells(1, nCols)).Value
    cPolo = AcharColuna(cab, 1, "NOME UNIDADE SISTEMA|POLO|UNIDADE")
    cGestor = AcharColuna(cab, 1, "GESTOR DE POLO / DIRETOR UNIDADE|GESTOR DE POLO|DIRETOR DE UNIDADE|GESTOR")
    cEmail = AcharColuna(cab, 1, "EMAIL GESTOR PRISMA / EMAIL DIRETOR DE UNIDADE|EMAIL GESTOR PRISMA|E-MAIL GESTOR|EMAIL GESTOR")
    cCons = AcharColuna(cab, 1, "CONSULTOR DE INFRA|CONSULTOR INFRAESTRUTURA|CONSULTOR")
    cGo = AcharColuna(cab, 1, "GERENTE OPERACIONAL|GO")
    If cPolo = 0 Or cGestor = 0 Or cEmail = 0 Then Err.Raise vbObjectError + 2, , "não achei as colunas de polo, gestor e e-mail do gestor na BASE_DE_UNIDADES."

    Application.StatusBar = "Lendo a Master..."
    nLin = un.Cells(un.Rows.Count, cPolo).End(xlUp).Row
    vPolo = Coluna(un, cPolo, nLin)
    vGestor = Coluna(un, cGestor, nLin)
    vEmail = Coluna(un, cEmail, nLin)
    vCons = Coluna(un, cCons, nLin)
    vGo = Coluna(un, cGo, nLin)

    Set polos = CreateObject("Scripting.Dictionary")
    Set emailsGestor = CreateObject("Scripting.Dictionary")
    For i = 2 To nLin
        k = Normalizar(Celula(vPolo, i))
        If Len(k) > 0 And Not polos.Exists(k) Then polos.Add k, i
        g = Normalizar(Celula(vGestor, i))
        e = LimparEmails(Celula(vEmail, i))
        If Len(g) > 0 And Len(e) > 0 Then
            If Not emailsGestor.Exists(g) Then emailsGestor.Add g, CreateObject("Scripting.Dictionary")
            Set d = emailsGestor(g)
            d(e) = d(e) + 1
        End If
    Next

    Set agenda = CreateObject("Scripting.Dictionary")
    If Not ct Is Nothing Then CarregarAgenda ct, agenda

    wb.Close False
    Set wb = Nothing
    Application.ScreenUpdating = True

    For Each item In alvos
        r = item
        k = Normalizar(TextoCelula(ws.Cells(r, cols("POLO"))))
        If Not polos.Exists(k) Then
            st = "Master: polo não encontrado"
            nNao = nNao + 1
        Else
            i = polos(k)
            g = Celula(vGestor, i)
            e = EscolherEmail(LimparEmails(Celula(vEmail, i)), g, emailsGestor)
            If Len(e) > 0 Then Preencher ws.Cells(r, cols("PARA")), e
            If cols.Exists("NOME") Then
                If Len(TextoCelula(ws.Cells(r, cols("NOME")))) = 0 And Len(g) > 0 Then Preencher ws.Cells(r, cols("NOME")), g
            End If

            cc = ""
            If copiarCons Then cc = cc & ";" & BuscarContato(Celula(vCons, i), agenda, "INFRA")
            If copiarGo Then cc = cc & ";" & BuscarContato(Celula(vGo, i), agenda, "OPERACIONAL")
            If cols.Exists("CC") And Len(LimparEmails(cc)) > 0 Then
                novoCc = LimparEmails(TextoCelula(ws.Cells(r, cols("CC"))) & ";" & cc)
                If novoCc <> TextoCelula(ws.Cells(r, cols("CC"))) Then Preencher ws.Cells(r, cols("CC")), novoCc
            End If

            If Len(e) = 0 Then
                st = "Master: polo sem e-mail de gestor"
                nNao = nNao + 1
            ElseIf Not EmailCasaComNome(e, g) Then
                st = "Master: CONFIRA, o e-mail não parece ser de " & g
                nConferir = nConferir + 1
            Else
                st = "Master: ok"
                nOk = nOk + 1
            End If
        End If
        If cols.Exists("STATUS") Then ws.Cells(r, cols("STATUS")).Value = st
    Next

    Application.StatusBar = False
    MsgBox "Busca na Master concluída." & vbLf & vbLf & _
           nOk & " linha(s) preenchida(s)" & vbLf & _
           nConferir & " para conferir (e-mail não parece do gestor)" & vbLf & _
           nNao & " sem resultado (veja a coluna Status)" & vbLf & vbLf & _
           "O que veio da Master está pintado de azul. Confira antes de enviar.", vbInformation
    Exit Sub

Falha:
    Application.ScreenUpdating = True
    Application.StatusBar = False
    If Not wb Is Nothing Then wb.Close False
    MsgBox "Não consegui ler a Master: " & Err.Description, vbExclamation
End Sub

' O e-mail da linha do polo, se casar com o nome do gestor. Senão, entre os
' e-mails do mesmo gestor em outras linhas, o que casa com o nome e mais se
' repete. Sem nenhum, fica o da linha (e o Status pede para conferir).
Private Function EscolherEmail(ByVal e As String, ByVal gestor As String, ByVal emailsGestor As Object) As String
    Dim d As Object, k As Variant, melhor As String, n As Long
    EscolherEmail = e
    If Len(e) > 0 And EmailCasaComNome(e, gestor) Then Exit Function
    If Not emailsGestor.Exists(Normalizar(gestor)) Then Exit Function
    Set d = emailsGestor(Normalizar(gestor))
    For Each k In d.Keys
        If EmailCasaComNome(CStr(k), gestor) And d(k) > n Then melhor = k: n = d(k)
    Next
    If Len(melhor) > 0 Then EscolherEmail = melhor
End Function

' A BASE_DE_UNIDADES grava dois nomes numa célula: "ALEXANDRE - MARIA" fica
' o primeiro; "TBD - MARIA" fica o segundo (TBD é "a definir", não é gente).
Private Function LimparNomePessoa(ByVal s As String) As String
    Dim partes() As String
    s = Trim$(Replace(s, " – ", " - "))
    LimparNomePessoa = s
    If InStr(s, " - ") = 0 Then Exit Function
    partes = Split(s, " - ")
    Select Case Normalizar(partes(0))
        Case "TBD", "A DEFINIR", "N/A", "-"
            LimparNomePessoa = Trim$(partes(1))
        Case Else
            LimparNomePessoa = Trim$(partes(0))
    End Select
End Function

' A BASE_DE_UNIDADES usa nome curto ("ANA CLARA") e a CONTATOS_PARCEIROS o
' completo ("ANA CLARA DE SOUZA"). Aceita o curto quando todos os pedaços
' aparecem no completo, só entre quem tem o cargo e só se der UM candidato.
Private Function BuscarContato(ByVal nome As String, ByVal agenda As Object, ByVal cargo As String) As String
    Dim chave As String, pedacos() As String, k As Variant, p As Variant
    Dim achado As String, n As Long, casa As Boolean
    chave = Normalizar(LimparNomePessoa(nome))
    If Len(chave) = 0 Then Exit Function
    If agenda.Exists(chave) Then BuscarContato = agenda(chave)(1): Exit Function
    pedacos = Split(chave, " ")
    If UBound(pedacos) < 1 Then Exit Function
    For Each k In agenda.Keys
        If InStr(agenda(k)(2), cargo) > 0 Then
            casa = True
            For Each p In pedacos
                If InStr(" " & k & " ", " " & p & " ") = 0 Then casa = False: Exit For
            Next
            If casa Then n = n + 1: achado = agenda(k)(1)
        End If
    Next
    If n = 1 Then BuscarContato = achado
End Function

' Na CONTATOS_PARCEIROS o cabeçalho não é a 1ª linha (estava na 5ª).
Private Sub CarregarAgenda(ByVal ct As Worksheet, ByVal agenda As Object)
    Dim dados As Variant, r As Long, linhaCab As Long, cNome As Long, cEmail As Long, cCargo As Long
    Dim nome As String
    With ct.UsedRange
        dados = ct.Range(ct.Cells(1, 1), ct.Cells(.Row + .Rows.Count - 1, .Column + .Columns.Count - 1)).Value
    End With
    For r = 1 To Application.Min(20, UBound(dados, 1))
        cNome = AcharColuna(dados, r, "NOME|NOME COMPLETO|COLABORADOR")
        cEmail = AcharColuna(dados, r, "E-MAIL|EMAIL|E-MAIL CORPORATIVO|EMAIL CORPORATIVO")
        If cNome > 0 And cEmail > 0 Then linhaCab = r: Exit For
    Next
    If linhaCab = 0 Then Exit Sub
    cCargo = AcharColuna(dados, linhaCab, "CARGO|FUNÇÃO|FUNCAO")
    For r = linhaCab + 1 To UBound(dados, 1)
        nome = Celula2(dados, r, cNome)
        If Len(Normalizar(nome)) > 0 And Not agenda.Exists(Normalizar(nome)) Then
            agenda.Add Normalizar(nome), Array(nome, Celula2(dados, r, cEmail), Normalizar(Celula2(dados, r, cCargo)))
        End If
    Next
End Sub

Private Function AcharAba(ByVal wb As Workbook, ByVal nomes As String) As Worksheet
    Dim ws As Worksheet, n As Variant
    For Each n In Split(nomes, "|")
        For Each ws In wb.Worksheets
            If Normalizar(ws.Name) = Normalizar(n) Then Set AcharAba = ws: Exit Function
        Next
    Next
End Function

' Primeiro apelido que bater, na ordem — o mais específico vem antes.
Private Function AcharColuna(ByRef dados As Variant, ByVal linha As Long, ByVal apelidos As String) As Long
    Dim a As Variant, c As Long
    For Each a In Split(apelidos, "|")
        For c = 1 To UBound(dados, 2)
            If Normalizar(Celula2(dados, linha, c)) = Normalizar(a) Then AcharColuna = c: Exit Function
        Next
    Next
End Function

Private Function Coluna(ByVal ws As Worksheet, ByVal c As Long, ByVal nLin As Long) As Variant
    If c > 0 Then Coluna = ws.Range(ws.Cells(1, c), ws.Cells(nLin, c)).Value
End Function

' ByRef de propósito: ByVal copiaria a coluna inteira (~4.800 linhas) a cada
' célula lida.
Private Function Celula(ByRef arr As Variant, ByVal i As Long) As String
    Celula = Celula2(arr, i, 1)
End Function

Private Function Celula2(ByRef arr As Variant, ByVal i As Long, ByVal c As Long) As String
    If IsEmpty(arr) Or c = 0 Then Exit Function
    If IsError(arr(i, c)) Then Exit Function
    Celula2 = Trim$(CStr(arr(i, c)))
End Function

Private Sub Preencher(ByVal cel As Range, ByVal valor As String)
    cel.Value = valor
    cel.Interior.Color = AZUL
End Sub
