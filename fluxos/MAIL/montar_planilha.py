# -*- coding: utf-8 -*-
"""
Monta 'Disparo de E-mails.xlsm' — o esqueleto de disparo — a partir dos
módulos VBA em ./vba.

    python montar_planilha.py              → cria a planilha do zero
    python montar_planilha.py --atualizar  → só troca as macros da planilha
                                             existente (mantém dados e CONFIG)

O código de verdade está em ./vba/*.bas; este script só cria as abas, os
exemplos e os botões, e importa os módulos. Para mudar o comportamento, edite
o .bas e rode de novo (ele recusa sobrescrever uma planilha que já existe,
para não apagar a lista de alguém — apague ou renomeie antes).

Importar módulo por automação exige a opção "Confiar no acesso ao modelo de
objeto do projeto do VBA". O script liga essa opção só enquanto roda e devolve
ao que era.
"""

import os
import sys
import tempfile
import winreg

import win32com.client as win32

PASTA = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(PASTA, "Disparo de E-mails.xlsm")
MODULOS = ["modUtil.bas", "modMaster.bas", "modDisparo.bas"]
CHAVE_VBOM = r"Software\Microsoft\Office\16.0\Excel\Security"

ROXO, ROXO_CLARO, VERMELHO, CINZA = (0x5B, 0x2A, 0x86), (0xF1, 0xEB, 0xF8), (0xC6, 0x28, 0x28), (0x44, 0x44, 0x44)


def cor(rgb):
    """Excel guarda a cor como BGR."""
    r, g, b = rgb
    return r + g * 256 + b * 65536


# ── conteúdo das abas ────────────────────────────────────────────────────

CONFIG = [
    ("Modelo escolhido", "", "Assunto do rascunho do Outlook que é o modelo. Preenchido pelos botões de modelo."),
    ("ID do modelo (não mexer)", "", "Identificação do rascunho no Outlook. Preenchida pelos botões."),
    ("Enviar como (e-mail)", "",
     "Caixa compartilhada que aparece no 'De:'. Precisa ter permissão de Enviar como. Vazio = sai da sua conta."),
    ("Nome do remetente", "", "Nome exibido no 'De:' quando 'Enviar como' está preenchido."),
    ("Assunto padrão", "",
     "Usado quando a coluna Assunto da linha está vazia. Vazio = assunto do modelo. Aceita {campos}."),
    ("CC em todos os e-mails", "", "Endereços separados por ';'. Somados ao CC de cada linha."),
    ("CCO em todos os e-mails", "", "Cópia oculta em todos. Separados por ';'."),
    ("Anexo em todos os e-mails", "", "Caminho completo de um arquivo. Vazio = sem anexo."),
    ("Intervalo entre envios (segundos)", 8, "Pausa anti-spam do firewall. Entre 5 e 15."),
    ("Agrupar linhas do mesmo destinatário", "S",
     "S = linhas com o mesmo Para e Assunto viram UM e-mail, com uma linha por polo na tabela. N = um e-mail por linha."),
    ("Colunas da tabela", "",
     "Quais colunas da DESTINATARIOS entram na tabela, separadas por ';'. Vazio = Polo + todas as colunas livres."),
    ("Arquivo da Master", "", "Caminho da Base de Polos - Master. Se vazio, o botão pergunta e guarda aqui."),
    ("Copiar consultor de infra (Master)", "N", "S = a busca na Master põe o consultor de infra do polo em CC."),
    ("Copiar GO (Master)", "N", "S = a busca na Master põe o gerente operacional do polo em CC."),
]

DEST_CAB = ["Status", "Enviar?", "Polo", "Nome", "Para", "CC", "CCO", "Assunto", "Anexo", "Pendência", "Prazo"]
DEST_EXEMPLOS = [
    ["", "S", "CONCORDIA/SC - I(3100)U", "Maria Exemplo", "maria.exemplo@exemplo.com", "", "", "", "",
     "Envio do checklist de infraestrutura", "até 30/11"],
    ["", "S", "JOACABA/SC - I(1234)U", "Maria Exemplo", "maria.exemplo@exemplo.com", "", "", "", "",
     "Agendar auditoria de laboratório", "até 15/11"],
    ["", "S", "IPORA/GO - I(4059)U", "João Exemplo", "joao.exemplo@exemplo.com", "", "", "", "",
     "Comprovar aulas práticas", "até 01/11"],
]

COMO_USAR = [
    ("DISPARO DE E-MAILS — esqueleto", "titulo"),
    ("", ""),
    ("1. O E-MAIL: clique em 'Criar modelo'. Abre no Outlook um rascunho no estilo do comunicado.", ""),
    ("   Mude o que quiser (textos, cores, partes inteiras), feche e salve. Ele é o modelo de todos os e-mails.", ""),
    ("   Entre chaves, o que muda para cada pessoa: {nome}, {polo}, {qtd_polos}, {tabela} (a tabela de polos)", ""),
    ("   e qualquer coluna da DESTINATARIOS, ex.: {Prazo}. Digite o campo de uma vez, sem formatar só metade.", ""),
    ("   Já tem um rascunho seu? Selecione ele no Outlook e clique em 'Usar e-mail selecionado'.", ""),
    ("2. Na aba DESTINATARIOS, uma linha por polo (ou por pessoa).", ""),
    ("   Para, CC e CCO aceitam vários endereços separados por ';'.", ""),
    ("   Enviar? = N pula a linha. Linha com Status 'Enviado...' também é pulada.", ""),
    ("   Colunas novas (ex.: Pendência, Prazo) viram campos no e-mail e colunas na {tabela}.", ""),
    ("3. Sem o e-mail do gestor? Preencha só o Polo e clique em 'Buscar na Master'.", ""),
    ("   O que vier da Master fica em AZUL. Confira: a Master tem cadastros errados.", ""),
    ("4. Se quiser, ajuste a aba CONFIG (cópias em todos, remetente, intervalo).", ""),
    ("5. Prévia: gera os e-mails na pasta 'previews' e abre o índice. Nada é enviado.", ""),
    ("   Se faltar um {campo}, ou um e-mail estiver inválido, a linha NÃO sai e o Status diz por quê.", ""),
    ("6. Rascunhos (opcional): cria tudo como rascunho no Outlook, com os destinatários reais, sem enviar.", ""),
    ("   Apague os rascunhos antes do passo 7, senão quem você mandar à mão recebe duas vezes.", ""),
    ("7. Enviar: disparo real pelo seu Outlook clássico (deixe ele aberto). Esc para parar no meio.", ""),
    ("", ""),
    ("Tudo o que sai fica registrado na aba LOG.", ""),
    ("Se a planilha abrir com as macros bloqueadas: feche, clique com o botão direito no arquivo >", ""),
    ("Propriedades > marque 'Desbloquear' > OK, e abra de novo.", ""),
]

BOTOES = [("Criar modelo", "CriarModelo", (0xD6, 0x24, 0x6E)),
          ("Usar e-mail selecionado", "UsarModeloSelecionado", (0xD6, 0x24, 0x6E)),
          ("Buscar na Master", "BuscarNaMaster", ROXO),
          ("Prévia", "Previa", ROXO),
          ("Rascunhos", "Rascunhos", ROXO),
          ("ENVIAR", "Enviar", VERMELHO)]


def valor_seguro(v):
    """Texto começando com '-', '=' ou '+' seria lido como fórmula."""
    if isinstance(v, str) and v[:1] in "-=+":
        return "'" + v
    return v


def cabecalho(rng):
    rng.Font.Bold = True
    rng.Font.Color = cor((255, 255, 255))
    rng.Interior.Color = cor(ROXO)


def aba_rotulo_valor(ws, titulos, linhas, larg_b):
    for c, t in enumerate(titulos, 1):
        ws.Cells(1, c).Value = t
    cabecalho(ws.Range("A1:C1"))
    for r, (rot, val, ajuda) in enumerate(linhas, 2):
        ws.Cells(r, 1).Value = rot
        ws.Cells(r, 2).Value = valor_seguro(val)
        ws.Cells(r, 3).Value = ajuda
    ws.Columns(1).ColumnWidth = 36
    ws.Columns(2).ColumnWidth = larg_b
    ws.Columns(3).ColumnWidth = 70
    ws.Range(f"A2:A{len(linhas) + 1}").Font.Bold = True
    ws.Range(f"B2:C{len(linhas) + 1}").WrapText = True
    ws.Range(f"C2:C{len(linhas) + 1}").Font.Color = cor((120, 120, 120))
    ws.Range(f"A1:C{len(linhas) + 1}").VerticalAlignment = -4160  # topo


def montar(excel):
    wb = excel.Workbooks.Add()
    while wb.Worksheets.Count < 4:
        wb.Worksheets.Add(After=wb.Worksheets(wb.Worksheets.Count))
    nomes = ["COMO USAR", "DESTINATARIOS", "CONFIG", "LOG"]
    for i, n in enumerate(nomes, 1):
        wb.Worksheets(i).Name = n

    escrever_como_usar(wb.Worksheets("COMO USAR"))

    # DESTINATARIOS — linhas 1-2 para os botões, cabeçalho na 3
    ws = wb.Worksheets("DESTINATARIOS")
    ws.Rows(1).RowHeight = 34
    ws.Cells(2, 1).Value = ("Uma linha por polo/pessoa · as colunas depois de 'Anexo' são livres: "
                            "renomeie, apague ou crie quantas quiser · apague os exemplos antes de usar")
    ws.Cells(2, 1).Font.Italic = True
    ws.Cells(2, 1).Font.Color = cor((120, 120, 120))
    for c, t in enumerate(DEST_CAB, 1):
        ws.Cells(3, c).Value = t
    cabecalho(ws.Range(ws.Cells(3, 1), ws.Cells(3, len(DEST_CAB))))
    for r, linha in enumerate(DEST_EXEMPLOS, 4):
        for c, v in enumerate(linha, 1):
            ws.Cells(r, c).Value = valor_seguro(v)
    larguras = [28, 9, 28, 22, 32, 28, 24, 30, 24, 34, 14]
    for c, w in enumerate(larguras, 1):
        ws.Columns(c).ColumnWidth = w
    ws.Range("B4:B5000").Validation.Add(3, 1, 1, "S,N")
    ws.Activate()
    excel.ActiveWindow.SplitRow = 3
    excel.ActiveWindow.SplitColumn = 0
    excel.ActiveWindow.FreezePanes = True

    criar_botoes(ws)

    aba_rotulo_valor(wb.Worksheets("CONFIG"), ["Configuração", "Valor", "Para que serve"], CONFIG, 45)

    ws = wb.Worksheets("LOG")
    for c, t in enumerate(["Data/hora", "Modo", "Para", "CC", "CCO", "Assunto", "Resultado"], 1):
        ws.Cells(1, c).Value = t
    cabecalho(ws.Range("A1:G1"))
    ws.Columns(1).NumberFormat = "dd/mm/yyyy hh:mm"
    for c, w in enumerate([17, 10, 32, 32, 25, 50, 30], 1):
        ws.Columns(c).ColumnWidth = w

    importar_modulos(wb)
    wb.Worksheets("DESTINATARIOS").Activate()
    wb.SaveAs(SAIDA, FileFormat=52)  # .xlsm
    wb.Close(False)


def importar_modulos(wb):
    """Troca os módulos do .xlsm pelos de ./vba. O editor do VBA lê em ANSI
    (cp1252) e com CRLF."""
    comps = wb.VBProject.VBComponents
    with tempfile.TemporaryDirectory() as tmp:
        for nome in MODULOS:
            modulo = os.path.splitext(nome)[0]
            for i in range(comps.Count, 0, -1):
                if comps.Item(i).Name == modulo:
                    comps.Remove(comps.Item(i))
            with open(os.path.join(PASTA, "vba", nome), encoding="utf-8") as f:
                codigo = f.read()
            destino = os.path.join(tmp, nome)
            with open(destino, "w", encoding="cp1252", newline="\r\n") as f:
                f.write(codigo)
            comps.Import(destino)


def escrever_como_usar(ws):
    ws.Columns(1).ClearContents()
    ws.Columns(1).Font.Size = 11
    ws.Columns(1).Font.Bold = False
    for r, (txt, estilo) in enumerate(COMO_USAR, 1):
        ws.Cells(r, 1).Value = valor_seguro(txt)
        if estilo == "titulo":
            ws.Cells(r, 1).Font.Size = 16
            ws.Cells(r, 1).Font.Bold = True
            ws.Cells(r, 1).Font.Color = cor(ROXO)
    ws.Columns(1).ColumnWidth = 110


def botao(ws, rotulo, macro, rgb, esq, topo, largura):
    shp = ws.Shapes.AddShape(5, esq, topo, largura, 26)  # retângulo arredondado
    shp.Fill.ForeColor.RGB = cor(rgb)
    shp.Line.Visible = False
    tr = shp.TextFrame2.TextRange
    tr.Text = rotulo
    tr.Font.Bold = True
    tr.Font.Size = 11
    tr.Font.Fill.ForeColor.RGB = cor((255, 255, 255))
    tr.ParagraphFormat.Alignment = 2   # centro
    shp.TextFrame2.VerticalAnchor = 3  # meio
    shp.OnAction = macro


def criar_botoes(ws):
    """Apaga os botões que existirem (forma com macro) e recria os de BOTOES."""
    for i in range(ws.Shapes.Count, 0, -1):
        if ws.Shapes(i).OnAction:
            ws.Shapes(i).Delete()
    esq = 4
    for rotulo, macro, rgb in BOTOES:
        largura = max(100, len(rotulo) * 8 + 24)
        botao(ws, rotulo, macro, rgb, esq, 4, largura)
        esq += largura + 8


def atualizar(excel):
    """Troca macros, botões e o COMO USAR, e tira da CONFIG as linhas que
    deixaram de existir. Os valores que o usuário preencheu ficam."""
    wb = excel.Workbooks.Open(SAIDA)
    importar_modulos(wb)
    criar_botoes(wb.Worksheets("DESTINATARIOS"))
    escrever_como_usar(wb.Worksheets("COMO USAR"))

    # A aba MENSAGEM existiu até 27/10/2026; o texto agora é um rascunho do Outlook.
    for i in range(wb.Worksheets.Count, 0, -1):
        if wb.Worksheets(i).Name == "MENSAGEM":
            wb.Worksheets(i).Delete()

    # CONFIG redesenhada na ordem atual, levando os valores já preenchidos.
    ws = wb.Worksheets("CONFIG")
    antes = {ws.Cells(r, 1).Value: ws.Cells(r, 2).Value
             for r in range(2, ws.Cells(ws.Rows.Count, 1).End(-4162).Row + 1)}
    ws.Cells.Clear()
    aba_rotulo_valor(ws, ["Configuração", "Valor", "Para que serve"],
                     [(rot, antes.get(rot, val) if antes.get(rot) is not None else val, ajuda)
                      for rot, val, ajuda in CONFIG], 45)
    wb.Save()
    wb.Close(False)


def main():
    so_atualizar = "--atualizar" in sys.argv
    if so_atualizar and not os.path.exists(SAIDA):
        print(f"[ERRO] '{os.path.basename(SAIDA)}' não existe. Rode sem --atualizar para criar.")
        sys.exit(1)
    if not so_atualizar and os.path.exists(SAIDA):
        print(f"[ERRO] '{os.path.basename(SAIDA)}' já existe. Apague ou renomeie antes de montar de novo.")
        sys.exit(1)

    k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, CHAVE_VBOM)
    try:
        antes = winreg.QueryValueEx(k, "AccessVBOM")[0]
    except FileNotFoundError:
        antes = None
    winreg.SetValueEx(k, "AccessVBOM", 0, winreg.REG_DWORD, 1)

    excel = None
    try:
        excel = win32.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        if so_atualizar:
            atualizar(excel)
            print(f"Macros atualizadas em: {SAIDA}")
        else:
            montar(excel)
            print(f"Pronto: {SAIDA}")
    finally:
        if excel is not None:
            excel.Quit()
        if antes is None:
            winreg.DeleteValue(k, "AccessVBOM")
        else:
            winreg.SetValueEx(k, "AccessVBOM", 0, winreg.REG_DWORD, antes)
        winreg.CloseKey(k)
        print("Opção de acesso ao VBA devolvida ao que era.")


if __name__ == "__main__":
    main()
