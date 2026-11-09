Attribute VB_Name = "Módulo2"


Option Explicit

Sub AtualizarTodosDados()

    Dim wsAuditorias As Worksheet
    Dim wsBase As Worksheet
    Dim wsContatos As Worksheet
    
    Dim ultimaAuditoria As Long
    Dim ultimaBase As Long
    Dim ultimaContato As Long
    
    Dim i As Long
    Dim linhaBase As Long
    Dim colGN As Long
    Dim colGO As Long
    Dim gerenteBase As String

    Dim idAuditoria As String
    Dim idBase As String
    Dim valorE As String
    Dim valorContato As String
    
    Dim encontrouBase As Boolean
    Dim encontrouContato As Boolean
    
    Dim totalProcessados As Long
    Dim totalEncontrados As Long
    Dim totalNaoEncontrados As Long
    Dim totalContatos As Long
    Dim totalContatosNaoEncontrados As Long
    
    Dim calcAnterior As XlCalculation

    On Error GoTo TrataErro

    ' ==========================================================
    ' DEFINIR AS ABAS
    ' ==========================================================

    Set wsAuditorias = ThisWorkbook.Worksheets("Aba de auditorias")
    Set wsBase = ThisWorkbook.Worksheets("Base_polos")
    Set wsContatos = ThisWorkbook.Worksheets("Contatos")

    ' ==========================================================
    ' GUARDAR CONFIGURAÇÕES ATUAIS DO EXCEL
    ' ==========================================================

    calcAnterior = Application.Calculation

    Application.ScreenUpdating = False
    Application.EnableEvents = False
    Application.Calculation = xlCalculationManual

    ' ==========================================================
    ' DESCOBRIR ÚLTIMAS LINHAS
    ' ==========================================================

    ultimaAuditoria = wsAuditorias.Cells( _
        wsAuditorias.Rows.Count, "B").End(xlUp).Row

    ultimaBase = wsBase.Cells( _
        wsBase.Rows.Count, "D").End(xlUp).Row

    ultimaContato = wsContatos.Cells( _
        wsContatos.Rows.Count, "A").End(xlUp).Row

    ' ==========================================================
    ' COLUNAS DO GERENTE NA BASE_POLOS
    '
    ' Desde a recarterizacao de out/2026 a carteira vale pela
    ' coluna GERENTE DE NEGOCIOS (NOVO), que entrou no FIM da
    ' base. A GERENTE OPERACIONAL (U) fica de reserva para polo
    ' sem GN ("-"). Procuradas pelo cabecalho, nao pela letra:
    ' coluna nova no meio da base nao desloca nada.
    ' ==========================================================

    colGN = ColunaPorCabecalho(wsBase, "GERENTE DE NEGOCIOS (NOVO)")
    If colGN = 0 Then colGN = ColunaPorCabecalho(wsBase, "GERENTE DE NEGOCIOS")

    colGO = ColunaPorCabecalho(wsBase, "GERENTE OPERACIONAL")
    If colGO = 0 Then colGO = 21    ' U, onde sempre esteve

    ' ==========================================================
    ' ABA DE AUDITORIAS
    '
    ' IMPORTANTE:
    ' SOMENTE A PARTIR DA LINHA 10
    '
    ' LINHAS 1 A 9 NÃO SERÃO ALTERADAS.
    ' ==========================================================

    If ultimaAuditoria >= 10 Then

        For i = 10 To ultimaAuditoria

            ' ==================================================
            ' PEGAR E NORMALIZAR O ID
            ' ==================================================

            idAuditoria = NormalizarID( _
                wsAuditorias.Cells(i, "B").Value)

            ' ==================================================
            ' SÓ PROCESSA SE EXISTIR UM ID REAL
            ' ==================================================

            If Len(idAuditoria) > 0 Then

                totalProcessados = totalProcessados + 1

                encontrouBase = False
                encontrouContato = False

                ' ==================================================
                ' PROCURAR NA BASE_POLOS
                '
                ' IMPORTANTE:
                ' A BASE É PESQUISADA DESDE A LINHA 1.
                ' ==================================================

                If ultimaBase >= 1 Then

                    For linhaBase = 1 To ultimaBase

                        idBase = NormalizarID( _
                            wsBase.Cells(linhaBase, "D").Value)

                        If Len(idBase) > 0 Then

                            If idAuditoria = idBase Then

                                encontrouBase = True
                                totalEncontrados = totalEncontrados + 1

                                ' ======================================
                                ' C = Base_polos CH (GRUPO ECONOMICO)
                                '
                                ' Era CI, que e a QTDE de unidades
                                ' do grupo - saia 2, 3, 16 no e-mail.
                                ' ======================================

                                wsAuditorias.Cells(i, "C").Value = _
                                    wsBase.Cells(linhaBase, "CH").Value

                                
                                ' ======================================
                                ' E = GERENTE DE NEGOCIOS (NOVO)
                                '     ou, sem GN, GERENTE OPERACIONAL
                                ' ======================================

                                gerenteBase = ""

                                If colGN > 0 Then
                                    gerenteBase = Trim(CStr( _
                                        wsBase.Cells(linhaBase, colGN).Value))
                                End If

                                If gerenteBase = "" Or gerenteBase = "-" Then
                                    gerenteBase = Trim(CStr( _
                                        wsBase.Cells(linhaBase, colGO).Value))
                                End If

                                wsAuditorias.Cells(i, "E").Value = _
                                    gerenteBase

                                ' ======================================
                                ' BUSCAR CONTATO
                                '
                                ' Contatos:
                                ' Coluna A = Nome
                                ' Coluna D = E-mail
                                '
                                ' Se o nome nao bate, tenta a aba
                                ' Apelidos e o nome sem "TBD - ".
                                ' Ver EmailDoGerente.
                                ' ======================================

                                valorE = NormalizarNome( _
                                    wsAuditorias.Cells(i, "E").Value)

                                If Len(valorE) > 0 Then

                                    valorContato = EmailDoGerente( _
                                        valorE, wsContatos, ultimaContato)

                                    If Len(valorContato) > 0 Then

                                        ' ==========================
                                        ' F = E-mail do gerente
                                        ' ==========================

                                        wsAuditorias.Cells(i, "F").Value = _
                                            valorContato

                                        encontrouContato = True
                                        totalContatos = totalContatos + 1

                                    End If

                                    ' ======================================
                                    ' CONTATO NÃO ENCONTRADO
                                    ' ======================================

                                    If encontrouContato = False Then

                                        wsAuditorias.Cells(i, "F").Value = _
                                            "Contato não encontrado"

                                        totalContatosNaoEncontrados = _
                                            totalContatosNaoEncontrados + 1

                                    End If

                                Else

                                    wsAuditorias.Cells(i, "F").ClearContents

                                End If

                                ' ======================================
                                ' ID ENCONTRADO
                                ' ======================================

                                Exit For

                            End If

                        End If

                    Next linhaBase

                End If

                ' ==================================================
                ' ID NÃO ENCONTRADO NA BASE
                ' ==================================================

                If encontrouBase = False Then

                    totalNaoEncontrados = totalNaoEncontrados + 1

                    wsAuditorias.Cells(i, "C").Value = _
                        "ID não encontrado"

                    wsAuditorias.Cells(i, "D").ClearContents

                    wsAuditorias.Cells(i, "E").Value = _
                        "ID não encontrado"

                    wsAuditorias.Cells(i, "F").Value = _
                        "ID não encontrado"

                End If

            End If

        Next i

    End If

    ' ==========================================================
    ' RESTAURAR EXCEL
    ' ==========================================================

    Application.ScreenUpdating = True
    Application.EnableEvents = True
    Application.Calculation = calcAnterior

    ' ==========================================================
    ' MENSAGEM FINAL
    ' ==========================================================

    MsgBox _
        "Atualização concluída!" & vbCrLf & vbCrLf & _
        "Linhas processadas: " & totalProcessados & vbCrLf & _
        "IDs encontrados na Base_polos: " & totalEncontrados & vbCrLf & _
        "IDs não encontrados: " & totalNaoEncontrados & vbCrLf & vbCrLf & _
        "Contatos encontrados: " & totalContatos & vbCrLf & _
        "Contatos não encontrados: " & totalContatosNaoEncontrados, _
        vbInformation, _
        "Atualização concluída"

    Exit Sub

' ==========================================================
' TRATAMENTO DE ERROS
' ==========================================================

TrataErro:

    Application.ScreenUpdating = True
    Application.EnableEvents = True
    Application.Calculation = calcAnterior

    MsgBox _
        "A macro encontrou um erro." & vbCrLf & vbCrLf & _
        "Número do erro: " & Err.Number & vbCrLf & _
        "Descrição: " & Err.Description, _
        vbCritical, _
        "Erro na atualização"

End Sub


' ==============================================================
' ACHAR O E-MAIL DO GERENTE
'
' A Base_polos e a Contatos nem sempre escrevem o nome igual
' (base: ANDRE DUARTE / Contatos: ANDRE MARTINS DUARTE).
' Tenta, nesta ordem:
'
' 1. o nome exato na Contatos
' 2. a aba Apelidos: e-mail direto (coluna C) ou o nome como
'    ele esta na Contatos (coluna B)
' 3. tudo de novo sem o prefixo "TBD - " (gerente provisorio)
'
' A Apelidos e preenchida a mao. Nao da para corrigir na
' propria Contatos: o Power Query apaga tudo a cada atualizacao.
'
' Devolve "" se nao achar.
' ==============================================================

Function EmailDoGerente(ByVal nome As String, _
                        wsContatos As Worksheet, _
                        ByVal ultimaContato As Long) As String

    Dim email As String
    Dim resto As String

    email = EmailPorNome(nome, wsContatos, ultimaContato)

    If Len(email) = 0 Then
        email = EmailPorApelido(nome, wsContatos, ultimaContato)
    End If

    If Len(email) = 0 And Left(nome, 4) = "TBD " Then

        resto = Trim(Mid(nome, 4))
        If Left(resto, 1) = "-" Then resto = Trim(Mid(resto, 2))

        If Len(resto) > 0 Then
            email = EmailDoGerente(resto, wsContatos, ultimaContato)
        End If

    End If

    EmailDoGerente = email

End Function


' ==============================================================
' E-MAIL PELO NOME EXATO NA CONTATOS
'
' Coluna A = Nome, coluna D = E-mail. Pesquisa desde a linha 1.
' ==============================================================

Function EmailPorNome(ByVal nome As String, _
                      wsContatos As Worksheet, _
                      ByVal ultimaContato As Long) As String

    Dim linhaContato As Long

    If Len(nome) = 0 Then Exit Function

    For linhaContato = 1 To ultimaContato

        If NormalizarNome(wsContatos.Cells(linhaContato, "A").Value) = nome Then

            EmailPorNome = Trim(CStr(wsContatos.Cells(linhaContato, "D").Value))
            Exit Function

        End If

    Next linhaContato

End Function


' ==============================================================
' E-MAIL PELA ABA APELIDOS
'
' Apelidos, a partir da linha 2:
' Coluna A = Nome como vem da base (coluna E da auditoria)
' Coluna B = Nome como esta na Contatos
' Coluna C = E-mail direto (vale mais que a coluna B)
' Coluna D = Telefone (usado pelo painel do WhatsApp, Modulo1)
'
' Se a aba nao existir, simplesmente nao acha nada.
' ==============================================================

Function EmailPorApelido(ByVal nome As String, _
                         wsContatos As Worksheet, _
                         ByVal ultimaContato As Long) As String

    Dim wsApelidos As Worksheet
    Dim ultimaApelido As Long
    Dim linha As Long

    On Error Resume Next
    Set wsApelidos = ThisWorkbook.Worksheets("Apelidos")
    On Error GoTo 0

    If wsApelidos Is Nothing Then Exit Function

    ultimaApelido = wsApelidos.Cells( _
        wsApelidos.Rows.Count, "A").End(xlUp).Row

    For linha = 2 To ultimaApelido

        If NormalizarNome(wsApelidos.Cells(linha, "A").Value) = nome Then

            EmailPorApelido = Trim(CStr(wsApelidos.Cells(linha, "C").Value))

            If Len(EmailPorApelido) = 0 Then
                EmailPorApelido = EmailPorNome( _
                    NormalizarNome(wsApelidos.Cells(linha, "B").Value), _
                    wsContatos, ultimaContato)
            End If

            Exit Function

        End If

    Next linha

End Function


' ==============================================================
' ACHAR UMA COLUNA PELO CABECALHO (linha 1)
'
' Devolve o numero da coluna, ou 0 se nao achar.
' ==============================================================

Function ColunaPorCabecalho(ws As Worksheet, ByVal titulo As String) As Long

    Dim achou As Range

    Set achou = ws.Rows(1).Find(What:=titulo, LookIn:=xlValues, _
                                LookAt:=xlWhole, MatchCase:=False)

    If Not achou Is Nothing Then ColunaPorCabecalho = achou.Column

End Function


' ==============================================================
' NORMALIZAR ID
' ==============================================================

Function NormalizarID(valor As Variant) As String

    Dim texto As String
    Dim numero As Double

    If IsError(valor) Then
        NormalizarID = ""
        Exit Function
    End If

    If IsEmpty(valor) Then
        NormalizarID = ""
        Exit Function
    End If

    texto = CStr(valor)

    texto = Replace(texto, Chr(160), "")
    texto = Replace(texto, vbTab, "")
    texto = Replace(texto, vbCr, "")
    texto = Replace(texto, vbLf, "")

    texto = Trim(texto)

    If Len(texto) = 0 Then
        NormalizarID = ""
        Exit Function
    End If

    If IsNumeric(texto) Then

        numero = CDbl(texto)

        NormalizarID = Format( _
            numero, _
            "0.############################")

    Else

        NormalizarID = UCase(texto)

    End If

End Function


' ==============================================================
' NORMALIZAR NOME
'
' Usado para comparar o nome do gerente.
'
' Ignora:
' - maiúsculas/minúsculas
' - espaços extras
' - espaços invisíveis
' - tabulações
' - quebras de linha
' ==============================================================

Function NormalizarNome(valor As Variant) As String

    Dim texto As String

    If IsError(valor) Then
        NormalizarNome = ""
        Exit Function
    End If

    If IsEmpty(valor) Then
        NormalizarNome = ""
        Exit Function
    End If

    texto = CStr(valor)

    texto = Replace(texto, Chr(160), " ")
    texto = Replace(texto, vbTab, " ")
    texto = Replace(texto, vbCr, " ")
    texto = Replace(texto, vbLf, " ")

    texto = Trim(texto)

    ' Remove espaços duplicados
    Do While InStr(texto, "  ") > 0
        texto = Replace(texto, "  ", " ")
    Loop

    NormalizarNome = UCase(texto)

End Function

