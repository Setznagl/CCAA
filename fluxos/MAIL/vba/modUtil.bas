Attribute VB_Name = "modUtil"
Option Explicit

' Funções de apoio usadas pelos outros módulos: nomes das abas, leitura da
' aba CONFIG, localização de colunas e limpeza de textos e e-mails.

Public Const ABA_CONFIG As String = "CONFIG"
Public Const ABA_DEST As String = "DESTINATARIOS"
Public Const ABA_LOG As String = "LOG"

' Na DESTINATARIOS as linhas 1 e 2 são dos botões; o cabeçalho é a 3ª.
Public Const LINHA_CAB As Long = 3

' Tira acento, põe em maiúscula e junta espaços repetidos. É assim que polo,
' cabeçalho, {campo} e rótulos da CONFIG são comparados.
Public Function Normalizar(ByVal s As String) As String
    Const COM_ACENTO As String = "ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑáàâãäéèêëíìîïóòôõöúùûüçñ"
    Const SEM_ACENTO As String = "AAAAAEEEEIIIIOOOOOUUUUCNaaaaaeeeeiiiiooooouuuucn"
    Dim i As Long, p As Long
    For i = 1 To Len(s)
        p = InStr(1, COM_ACENTO, Mid$(s, i, 1), vbBinaryCompare)
        If p > 0 Then Mid$(s, i, 1) = Mid$(SEM_ACENTO, p, 1)
    Next
    s = Replace(Replace(Replace(s, Chr(160), " "), vbCr, " "), vbLf, " ")
    s = UCase$(Trim$(s))
    Do While InStr(s, "  ") > 0
        s = Replace(s, "  ", " ")
    Loop
    Normalizar = s
End Function

Public Function Sim(ByVal s As String) As Boolean
    s = Normalizar(s)
    Sim = (s = "S" Or s = "SIM" Or s = "X")
End Function

Public Function Nao(ByVal s As String) As Boolean
    s = Normalizar(s)
    Nao = (s = "N" Or s = "NAO")
End Function

' Valor da célula como o usuário vê: data em dd/mm/aaaa, número como está
' formatado na planilha.
Public Function TextoCelula(ByVal cel As Range) As String
    Dim v As Variant
    v = cel.Value
    If IsError(v) Or IsEmpty(v) Then Exit Function
    Select Case VarType(v)
        Case vbDate
            If Int(v) = v Then
                TextoCelula = Format$(v, "dd/mm/yyyy")
            Else
                TextoCelula = Format$(v, "dd/mm/yyyy hh:nn")
            End If
        Case vbString
            TextoCelula = Trim$(v)
        Case Else
            TextoCelula = cel.Text
            ' coluna estreita mostra "####" no .Text
            If InStr(TextoCelula, "#") > 0 Or Len(TextoCelula) = 0 Then TextoCelula = CStr(v)
    End Select
End Function

' -- CONFIG: rótulo na coluna A, valor na B -----------------------------

Public Function Cfg(ByVal rotulo As String) As String
    Cfg = ValorPorRotulo(ABA_CONFIG, rotulo)
End Function

Private Function LinhaDoRotulo(ByVal ws As Worksheet, ByVal rotulo As String) As Long
    Dim r As Long, alvo As String
    alvo = Normalizar(rotulo)
    For r = 1 To ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
        If Normalizar(CStr(ws.Cells(r, 1).Value)) = alvo Then LinhaDoRotulo = r: Exit Function
    Next
End Function

Private Function ValorPorRotulo(ByVal aba As String, ByVal rotulo As String) As String
    Dim ws As Worksheet, r As Long
    Set ws = ThisWorkbook.Worksheets(aba)
    r = LinhaDoRotulo(ws, rotulo)
    If r > 0 Then ValorPorRotulo = TextoCelula(ws.Cells(r, 2))
End Function

Public Sub SetCfg(ByVal rotulo As String, ByVal valor As String)
    Dim ws As Worksheet, r As Long
    Set ws = ThisWorkbook.Worksheets(ABA_CONFIG)
    r = LinhaDoRotulo(ws, rotulo)
    If r > 0 Then ws.Cells(r, 2).Value = valor
End Sub

' -- DESTINATARIOS ------------------------------------------------------

' Cabeçalho normalizado -> número da coluna. As colunas são achadas pelo
' nome, então a ordem não importa e dá para acrescentar colunas livres.
Public Function ColunasDest(ByVal ws As Worksheet, Optional ByVal rotulos As Object = Nothing) As Object
    Dim d As Object, c As Long, ultCol As Long, k As String
    Set d = CreateObject("Scripting.Dictionary")
    ultCol = ws.Cells(LINHA_CAB, ws.Columns.Count).End(xlToLeft).Column
    For c = 1 To ultCol
        k = Normalizar(CStr(ws.Cells(LINHA_CAB, c).Value))
        If Len(k) > 0 And Not d.Exists(k) Then
            d.Add k, c
            If Not rotulos Is Nothing Then rotulos(k) = Trim$(CStr(ws.Cells(LINHA_CAB, c).Value))
        End If
    Next
    Set ColunasDest = d
End Function

Public Function UltimaLinha(ByVal ws As Worksheet) As Long
    Dim c As Long, r As Long, ultCol As Long
    ultCol = ws.Cells(LINHA_CAB, ws.Columns.Count).End(xlToLeft).Column
    UltimaLinha = LINHA_CAB
    For c = 1 To ultCol
        r = ws.Cells(ws.Rows.Count, c).End(xlUp).Row
        If r > UltimaLinha Then UltimaLinha = r
    Next
End Function

' -- Texto do e-mail ----------------------------------------------------

Public Function Esc(ByVal s As String) As String
    s = Replace(s, "&", "&amp;")
    s = Replace(s, "<", "&lt;")
    s = Replace(s, ">", "&gt;")
    s = Replace(s, """", "&quot;")
    Esc = Replace(s, "'", "&#39;")
End Function

' Troca {campo} pelo valor da linha. Campo vazio ou inexistente vai para
' 'faltando' e o e-mail é barrado: é a trava do "até DD/MM" do Farol, que
' passaria literal para todo mundo sem nada quebrar.
Public Function Campos(ByVal s As String, ByVal valores As Object, ByRef faltando As String, ByVal emHtml As Boolean) As String
    Dim a As Long, b As Long, nome As String, v As String
    a = InStr(s, "{")
    Do While a > 0
        b = InStr(a + 1, s, "}")
        If b = 0 Then Exit Do
        nome = Mid$(s, a + 1, b - a - 1)
        v = ""
        If valores.Exists(Normalizar(Decodificar(nome))) Then v = valores(Normalizar(Decodificar(nome)))
        If Not NomeDeCampo(Decodificar(nome)) Then
            ' chave que não é campo (CSS, texto qualquer entre chaves): segue
            a = InStr(a + 1, s, "{")
        ElseIf Len(v) = 0 Then
            If InStr(faltando, "{" & nome & "}") = 0 Then faltando = faltando & " {" & nome & "}"
            a = InStr(b + 1, s, "{")
        Else
            If emHtml Then v = Esc(v)
            s = Left$(s, a - 1) & v & Mid$(s, b + 1)
            a = InStr(a + Len(v), s, "{")
        End If
    Loop
    Campos = s
End Function

' Parece nome de campo? Curto e sem pontuação de código/HTML.
Public Function NomeDeCampo(ByVal s As String) As Boolean
    Dim i As Long
    If Len(s) = 0 Or Len(s) > 40 Then Exit Function
    For i = 1 To Len(s)
        If InStr(":;{}<>=""/", Mid$(s, i, 1)) > 0 Then Exit Function
    Next
    NomeDeCampo = True
End Function

' O Outlook pode gravar acento e espaço do nome do campo como entidade
' (&#234;, &nbsp;).
Public Function Decodificar(ByVal s As String) As String
    Dim a As Long, b As Long, n As String
    s = Replace(Replace(s, "&nbsp;", " "), "&amp;", "&")
    a = InStr(s, "&#")
    Do While a > 0
        b = InStr(a, s, ";")
        If b = 0 Then Exit Do
        n = Mid$(s, a + 2, b - a - 2)
        If IsNumeric(n) And Len(n) > 0 Then
            s = Left$(s, a - 1) & ChrW(CLng(n)) & Mid$(s, b + 1)
        End If
        a = InStr(a + 1, s, "&#")
    Loop
    Decodificar = s
End Function

' **texto** = negrito · !!texto!! = vermelho e negrito (como os prazos do Farol)
Public Function Marcas(ByVal s As String) As String
    s = Alternar(s, "**", "<b>", "</b>")
    Marcas = Alternar(s, "!!", "<b style='color:#C62828'>", "</b>")
End Function

Private Function Alternar(ByVal s As String, ByVal marca As String, ByVal abre As String, ByVal fecha As String) As String
    Dim partes() As String, i As Long, r As String
    If InStr(s, marca) = 0 Then Alternar = s: Exit Function
    partes = Split(s, marca)
    r = partes(0)
    For i = 1 To UBound(partes)
        If i Mod 2 = 1 Then r = r & abre Else r = r & fecha
        r = r & partes(i)
    Next
    If UBound(partes) Mod 2 = 1 Then r = r & fecha
    Alternar = r
End Function

' Quebra de linha vira <br/>; linha começando com "- " vira tópico.
Public Function Paragrafos(ByVal s As String) As String
    Dim l As Variant, r As String, t As String, i As Long, p As Long
    s = Replace(Replace(s, vbCrLf, vbLf), vbCr, vbLf)
    For Each l In Split(s, vbLf)
        t = Trim$(l)
        ' o "- " pode vir depois de uma tag de formatação (<span ...>)
        p = 1
        Do While Mid$(t, p, 1) = "<" And InStr(p, t, ">") > 0
            p = InStr(p, t, ">") + 1
        Loop
        If Mid$(t, p, 2) = "- " Then t = Left$(t, p - 1) & "&nbsp;&nbsp;&#9679;&nbsp; " & Mid$(t, p + 2)
        If i > 0 Then r = r & "<br/>"
        r = r & t
        i = i + 1
    Next
    Paragrafos = r
End Function

' Arquivo de prévia gravado só com ASCII: acento vira &#NNN; e o navegador
' mostra certo sem depender de codificação.
Public Function ParaAscii(ByVal s As String) As String
    Dim i As Long, c As Long, partes() As String
    ReDim partes(1 To Len(s) + 1)
    For i = 1 To Len(s)
        c = AscW(Mid$(s, i, 1))
        If c < 0 Then c = c + 65536
        If c > 127 Then partes(i) = "&#" & c & ";" Else partes(i) = Mid$(s, i, 1)
    Next
    ParaAscii = Join(partes, "")
End Function

' -- E-mails ------------------------------------------------------------

Public Function EmailValido(ByVal e As String) As Boolean
    Dim a As Long, p As Long
    e = Trim$(e)
    a = InStr(e, "@")
    p = InStrRev(e, ".")
    EmailValido = a > 1 And p > a + 1 And p < Len(e) And InStr(e, " ") = 0 And InStr(a + 1, e, "@") = 0
End Function

' Junta os endereços de 'lista' em 'destino' (sem repetir). Devolve o
' primeiro endereço inválido, ou "" se estiver tudo certo.
Public Function SomarEmails(ByVal destino As Object, ByVal lista As String) As String
    Dim p As Variant, t As String
    For Each p In Split(Replace(lista, ",", ";"), ";")
        t = Trim$(p)
        If Len(t) > 0 Then
            If Not EmailValido(t) Then SomarEmails = t: Exit Function
            If Not destino.Exists(LCase$(t)) Then destino.Add LCase$(t), t
        End If
    Next
End Function

Public Function Lista(ByVal d As Object) As String
    If d.Count > 0 Then Lista = Join(d.Items, "; ")
End Function

' Tira separador vazio ("; FULANO@...", ";;") sem remover endereço nenhum.
' Foi um "; " no começo que mandou o comunicado do RICARDO para os sócios.
Public Function LimparEmails(ByVal s As String) As String
    Dim p As Variant, t As String, vistos As Object
    Set vistos = CreateObject("Scripting.Dictionary")
    For Each p In Split(Replace(s, ",", ";"), ";")
        t = Trim$(p)
        If InStr(t, "@") > 0 And Not vistos.Exists(LCase$(t)) Then vistos.Add LCase$(t), t
    Next
    LimparEmails = Lista(vistos)
End Function

' O endereço tem algum pedaço (3+ letras) do nome antes do '@'? Serve para
' desempatar e avisar, nunca para descartar o único e-mail que existe.
Public Function EmailCasaComNome(ByVal email As String, ByVal nome As String) As Boolean
    Dim p As Variant, q As Variant, doNome As Collection
    Set doNome = Pedacos(Normalizar(nome))
    For Each p In Pedacos(Normalizar(Split(email & "@", "@")(0)))
        For Each q In doNome
            If p = q Then EmailCasaComNome = True: Exit Function
        Next
    Next
End Function

Private Function Pedacos(ByVal s As String) As Collection
    Dim c As New Collection, i As Long, ch As String, atual As String
    For i = 1 To Len(s) + 1
        ch = Mid$(s, i, 1)
        If ch Like "[A-Z0-9]" Then
            atual = atual & ch
        Else
            If Len(atual) >= 3 Then c.Add atual
            atual = ""
        End If
    Next
    Set Pedacos = c
End Function

' -- Diversos -----------------------------------------------------------

Public Function ArquivoExiste(ByVal caminho As String) As Boolean
    If Len(caminho) > 0 Then ArquivoExiste = CreateObject("Scripting.FileSystemObject").FileExists(caminho)
End Function

Public Function Duracao(ByVal seg As Double) As String
    If seg < 60 Then
        Duracao = CLng(seg) & "s"
    ElseIf seg < 3600 Then
        Duracao = (CLng(seg) \ 60) & "min"
    Else
        Duracao = (CLng(seg) \ 3600) & "h" & Format$((CLng(seg) Mod 3600) \ 60, "00")
    End If
End Function

Public Function NomeDeArquivo(ByVal s As String) As String
    Dim i As Long, ch As String, r As String
    For i = 1 To Len(s)
        ch = Mid$(s, i, 1)
        If ch Like "[A-Za-z0-9@._-]" Then r = r & ch Else r = r & "_"
    Next
    NomeDeArquivo = Left$(r, 60)
End Function
