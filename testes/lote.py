"""Prepare reviewed Outlook packages in memory; never load a mail transport."""
import base64
import binascii
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import zipfile

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

COLUMNS = ['Enviar', 'Polo', 'Para', 'CC', 'CCO', 'Assunto']
MAX_ROWS = 500


def spreadsheet_template():
    book = Workbook()
    sheet = book.active
    sheet.title = 'DESTINATARIOS'
    sheet.append(COLUMNS)
    for cell in sheet[1]:
        cell.font = Font(color='FFFFFF', bold=True)
        cell.fill = PatternFill('solid', fgColor='173D27')
    for column, width in zip('ABCDEF', (12, 32, 48, 48, 48, 65)):
        sheet.column_dimensions[column].width = width
    sheet.freeze_panes = 'A2'
    choice = DataValidation(type='list', formula1='"SIM,NAO"', allow_blank=True)
    sheet.add_data_validation(choice)
    choice.add('A2:A501')
    help_sheet = book.create_sheet('INSTRUCOES')
    for text in (
        'Uma linha selecionada corresponde a uma mensagem. Não há agrupamento automático por polo ou gestor.',
        'Marque Enviar = SIM ou X para pré-selecionar. Vazio ou NAO não seleciona.',
        'Use apenas endereços de email separados por ; em Para, CC e CCO. Não use fórmulas.',
        'Assunto por linha é opcional quando houver assunto padrão na tela.',
        'As linhas e as cópias podem ser revisadas na página antes de baixar o lote.',
        'Nenhuma mensagem é enviada pelo site. O pacote deve ser extraído no Windows com Outlook clássico.',
    ):
        help_sheet.append([text])
    help_sheet.column_dimensions['A'].width = 125
    output = BytesIO()
    book.save(output)
    return output.getvalue()


def import_spreadsheet(encoded):
    if not isinstance(encoded, str) or len(encoded) > 2 * 1024 * 1024:
        raise ValueError('Envie uma planilha .xlsx de até 1 MiB')
    try:
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > 1024 * 1024:
            raise ValueError('Planilha excede 1 MiB')
        with zipfile.ZipFile(BytesIO(raw)) as archive:
            if len(archive.infolist()) > 200 or sum(entry.file_size for entry in archive.infolist()) > 10 * 1024 * 1024:
                raise ValueError('Planilha expandida excede o limite permitido')
        book = load_workbook(BytesIO(raw), read_only=True, data_only=False, keep_links=False)
    except (binascii.Error, zipfile.BadZipFile, KeyError, OSError) as exc:
        raise ValueError('Arquivo .xlsx inválido') from exc
    try:
        if 'DESTINATARIOS' not in book.sheetnames:
            raise ValueError('Use a aba DESTINATARIOS do modelo fornecido')
        sheet = book['DESTINATARIOS']
        if sheet.max_row > MAX_ROWS + 1 or sheet.max_column > len(COLUMNS):
            raise ValueError('Use até 500 linhas e as seis colunas do modelo')
        cells = sheet.iter_rows(max_row=MAX_ROWS + 1, max_col=6)
        header = [str(cell.value or '').strip() for cell in next(cells)]
        if header != COLUMNS:
            raise ValueError('Cabeçalho esperado: ' + ', '.join(COLUMNS))
        rows = []
        for line, row in enumerate(cells, 2):
            if any(cell.data_type == 'f' for cell in row):
                raise ValueError(f'Linha {line}: fórmulas não são aceitas; use valores')
            values = [str(cell.value).strip() if cell.value is not None else '' for cell in row]
            if not any(values):
                continue
            if any(len(value) > 2000 for value in values):
                raise ValueError(f'Linha {line}: campo excede 2000 caracteres')
            selected, polo, para, cc, cco, assunto = values
            if selected.upper() not in {'', 'SIM', 'X', 'NAO', 'NÃO', 'N'}:
                raise ValueError(f'Linha {line}: Enviar deve ser SIM, X, NAO ou vazio')
            rows.append(dict(selecionado=selected.upper() in {'SIM', 'X'}, polo=polo,
                             para=para, cc=cc, cco=cco, assunto=assunto))
        if not rows:
            raise ValueError('A planilha não contém destinatários para revisão')
        return rows
    finally:
        book.close()


def text(value, label, limit=2000):
    if not isinstance(value, str) or len(value) > limit or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError(f'{label}: texto inválido ou excede {limit} caracteres')
    return value.strip()


def addresses(value, label, required=False):
    value = text(value, label)
    result = []
    for address in value.split(';'):
        address = address.strip()
        if not address:
            continue
        if len(address) > 254 or not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@(?:[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,63}", address):
            raise ValueError(f'{label}: use emails válidos separados por ;')
        local = address.split('@', 1)[0]
        if local.startswith('.') or local.endswith('.') or '..' in local or len(local) > 64:
            raise ValueError(f'{label}: use emails válidos separados por ;')
        if address.lower() not in {entry.lower() for entry in result}:
            result.append(address)
    if required and not result:
        raise ValueError(f'{label}: informe ao menos um email')
    return ';'.join(sorted(result, key=str.lower))


def approved_html(payload):
    html = payload.get('html')
    if not isinstance(html, str) or not html.strip() or '\x00' in html or len(html.encode('utf-8')) > 1024 * 1024:
        raise ValueError('Carregue um HTML UTF-8 não vazio de até 1 MiB')
    return html


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def build_package(payload):
    if payload.get('aprovado') is not True:
        raise ValueError('Confirme a revisão do conteúdo, prazo e destinatários')
    html = approved_html(payload)
    sender = addresses(payload.get('remetente', ''), 'Remetente')
    if ';' in sender:
        raise ValueError('Remetente: informe uma única conta do Outlook')
    default_subject = text(payload.get('assunto', ''), 'Assunto padrão', 255)
    source_rows = payload.get('rows')
    if not isinstance(source_rows, list) or not 1 <= len(source_rows) <= MAX_ROWS:
        raise ValueError('Revise entre 1 e 500 linhas de destinatários')
    rows, ids = [], set()
    for index, source in enumerate(source_rows, 1):
        if not isinstance(source, dict) or type(source.get('selecionado')) is not bool:
            raise ValueError(f'Linha {index}: seleção inválida')
        if not source['selecionado']:
            continue
        row = {field: addresses(source.get(field, ''), f'Linha {index} — {field}', field == 'para')
               for field in ('para', 'cc', 'cco')}
        row['assunto'] = text(source.get('assunto', ''), f'Linha {index} — assunto', 255) or default_subject
        if not row['assunto']:
            raise ValueError(f'Linha {index}: informe o assunto ou o assunto padrão')
        identity = digest({key: value.lower() if key != 'assunto' else value for key, value in row.items()})
        if identity in ids:
            raise ValueError(f'Linha {index}: mensagem duplicada; desmarque a repetição')
        ids.add(identity)
        rows.append(dict(id=identity, **row))
    if not rows:
        raise ValueError('Selecione explicitamente ao menos uma mensagem')
    manifest = dict(version=1, html_sha256=hashlib.sha256(html.encode('utf-8')).hexdigest(),
                    remetente=sender, rows=sorted(rows, key=lambda row: row['id']))
    # Same content and routing retain the local history even after a fresh download.
    manifest['batch_id'] = digest(manifest)
    output = BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('lote.json', json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8'))
        archive.writestr('mensagem.html', html.encode('utf-8'))
        for filename in ('executar.ps1', 'abrir.cmd', 'LEIA-ME.txt'):
            archive.writestr(filename, (Path(__file__).parent / 'lote_outlook' / filename).read_bytes())
    return output.getvalue()
