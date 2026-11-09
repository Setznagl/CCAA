"""Isolated literal port of Mari's LinhaTabela/MontarHTML (no VBA/transport).

Static markup follows Modulo1_NOVO.bas, checked against the saved preview.
Dates use explicit pt-BR weekday names, independent of the host locale.
"""
from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook


def load_mari(data_dir: Path) -> dict[str, dict]:
    """Read the fixed workbook's cached A:H values only; never refresh formulas."""
    workbook = load_workbook(data_dir / 'Disparador_auditoria_automatizado_FINAL(1).xlsm',
                             read_only=True, data_only=True)
    grouped = {}
    try:
        sheet = workbook['Aba de auditorias']
        for values in sheet.iter_rows(min_row=10, max_col=8, values_only=True):
            polo, _, group, day, manager, email, _, _ = values
            polo = _text(polo).strip(' ')
            email = _text(email).replace('\xa0', ' ').lower().strip(' ').rstrip(';, ')
            at, dot = email.find('@'), email.rfind('.')
            # Keep VBA's deliberately weak EmailValido; this is not address validation.
            if not polo or 'encontrado' in email or not (at > 0 and dot > at + 1):
                continue
            if email not in grouped:
                grouped[email] = {'label': _text(manager).strip(' '), 'polo_count': 0, 'rows': []}
            model = grouped[email]
            model['rows'].append({'polo': polo, 'grupo': _text(group).strip(' '), 'date': day})
            model['polo_count'] += 1
    finally:
        workbook.close()
    return {str(index): grouped[email] for index, email in enumerate(sorted(grouped), 1)}

_WEEKDAYS = ('segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira',
             'sexta-feira', 'sábado', 'domingo')


def _text(value):
    return '' if value is None else str(value)


def _esc(value):
    return _text(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _date(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    # shortcut: pt-BR numeric strings only; extend if another cached format appears.
    if isinstance(value, str):
        for pattern in ('%d/%m/%Y', '%d/%m/%Y %H:%M', '%d/%m/%Y %H:%M:%S'):
            try:
                return datetime.strptime(value.strip(' '), pattern)
            except ValueError:
                pass
    return None


def _row(row, index, today):
    value = row['date']
    day = _date(value)
    text = day.strftime('%d/%m/%Y') if day else _text(value).strip(' ')
    background = '#FAF8FD' if index % 2 == 0 else '#ffffff'
    base = f'background:{background};padding:11px 14px;border-bottom:1px solid #E3E3E3;font-size:13px;'
    stripe = '#5B2A86'
    if text == '':
        stripe = '#B26A00'
        cell = f'<td style="{base}text-align:center;font-weight:bold;color:#B26A00">A marcar</td>'
    elif day:
        if day < datetime.combine(today, datetime.min.time()):
            stripe = '#C62828'
            color, detail_color, detail = '#C62828', '#C62828', 'data já passou'
        else:
            color, detail_color, detail = '#444444', '#8a8a8a', _WEEKDAYS[day.weekday()]
        cell = (f'<td style="{base}text-align:center"><span style="font-weight:bold;color:{color}">{text}</span><br/>'
                f'<span style="font-size:10.5px;color:{detail_color}">{detail}</span></td>')
    else:
        cell = f'<td style="{base}text-align:center;color:#444444">{_esc(text)}</td>'
    group = _text(row['grupo']).strip(' ') or '-'
    return (f'<tr><td style="background:{background};padding:11px 0 11px 14px;border-bottom:1px solid #E3E3E3;'
            f'border-left:3px solid {stripe};font-size:12px;color:#a9a9a9">{index}</td>'
            f'<td style="{base}font-weight:bold;color:#5B2A86">{_esc(row["polo"])}</td>'
            f'<td style="{base}color:#444444">{_esc(group)}</td>{cell}</tr>')


def render_mari(model: dict, today: date) -> str:
    """Return HTMLBody only; today replaces VBA Date without reading the clock."""
    name = _esc(_text(model['label']).strip(' ') or 'Gerente Operacional')
    count = len(model['rows'])
    noun = 'polo' if count == 1 else 'polos'
    dates = [day for row in model['rows'] if (day := _date(row['date'])) is not None]
    period = 'A definir'
    preheader = f'{count} auditoria(s) de laboratório na sua carteira.'
    if dates:
        first, last = min(dates), max(dates)
        period = first.strftime('%d/%m/%Y') if first == last else first.strftime('%d/%m') + ' a ' + last.strftime('%d/%m/%Y')
        preheader += f' Próxima: {_WEEKDAYS[first.weekday()]}, {first:%d/%m}.'
    preheader = _esc(preheader)
    rows_html = ''.join(_row(row, index, today) for index, row in enumerate(model['rows'], 1))
    return f'''<html><head><meta charset="UTF-8"></head><body style="margin:0;padding:0;background:#eef0f2;font-family:Arial,Helvetica,sans-serif"><div style="display:none;font-size:1px;color:#eef0f2;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden">{preheader}</div><table width="100%" cellpadding="0" cellspacing="0" style="background:#eef0f2;padding:24px 0"><tr><td align="center"><table width="780" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:6px"><tr><td style="background:#F1EBF8;padding:18px 34px"><table width="100%"><tr><td><span style="font-size:15px;font-weight:bold;color:#5B2A86">-RGC &nbsp;&#9679;&#9679;</span><br/><span style="font-size:13px;font-weight:bold;color:#5B2A86">Regularização e Gestão de Contratos</span><br/><span style="font-size:12px;color:#6b6b6b">Auditoria de Laboratórios</span></td><td style="text-align:right;vertical-align:middle"><span style="font-size:11px;font-weight:bold;color:#5B2A86;letter-spacing:1px">DOCUMENTO OFICIAL</span></td></tr></table></td></tr><tr><td style="padding:22px 34px 0"><span style="font-size:11px;font-weight:bold;color:#5C3D9E;letter-spacing:1px">AGENDA SEMANAL DE AUDITORIAS</span><br/><span style="font-size:21px;font-weight:bold;color:#222">Auditoria de Laboratórios &mdash; Polos da sua carteira</span></td></tr><tr><td style="padding:16px 34px 0"><table width="100%" cellpadding="0" cellspacing="0" style="background:#F1EBF8;border-radius:5px"><tr><td width="46%" style="padding:14px 20px;border-right:1px solid #ddd2ec"><span style="font-size:10px;font-weight:bold;color:#5B2A86;letter-spacing:0.5px">GERENTE OPERACIONAL</span><br/><span style="font-size:15px;font-weight:bold;color:#222">{name}</span></td><td width="32%" style="padding:14px 20px;border-right:1px solid #ddd2ec"><span style="font-size:10px;font-weight:bold;color:#5B2A86;letter-spacing:0.5px">PERÍODO</span><br/><span style="font-size:15px;font-weight:bold;color:#222">{period}</span></td><td width="22%" style="padding:14px 20px"><span style="font-size:10px;font-weight:bold;color:#5B2A86;letter-spacing:0.5px">AUDITORIAS</span><br/><span style="font-size:24px;font-weight:bold;color:#5B2A86;line-height:1.1">{count}</span> <span style="font-size:13px;color:#6b6b6b">{noun}</span></td></tr></table></td></tr><tr><td style="padding:18px 34px 0"><span style="font-size:13.5px;color:#444444;line-height:1.65">Olá, {name}! Segue a relação dos polos da sua carteira que serão auditados pela equipe de <b>Auditoria de Laboratórios</b>. Pedimos que reforce diretamente com os gestores a importância do recebimento e do apoio às equipes em campo.</span></td></tr><tr><td style="padding:26px 34px 0"><span style="font-size:14px;font-weight:bold;color:#5C3D9E;letter-spacing:0.5px">&#128197;&nbsp; AUDITORIAS PROGRAMADAS</span><span style="font-size:11.5px;color:#8a8a8a">&nbsp; &middot; &nbsp;em ordem de data</span></td></tr><tr><td style="padding:9px 34px 0"><table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #E3E3E3;border-collapse:collapse"><tr style="background:#5C3D9E"><td width="34" style="padding:9px 0 9px 14px"><span style="color:#c9b8e6;font-size:11px;font-weight:bold">#</span></td><td style="padding:9px 14px"><span style="color:#fff;font-size:11px;font-weight:bold">POLO</span></td><td style="padding:9px 14px"><span style="color:#fff;font-size:11px;font-weight:bold">GRUPO ECONÔMICO</span></td><td width="150" style="padding:9px 14px;text-align:center"><span style="color:#fff;font-size:11px;font-weight:bold">DATA DA AUDITORIA</span></td></tr>{rows_html}</table></td></tr><tr><td style="padding:26px 34px 0"><table width="100%" cellpadding="0" cellspacing="0" style="background:#F7F4FC;border:1px solid #e4dcf2;border-radius:5px"><tr><td style="padding:16px 20px"><span style="font-size:13px;font-weight:bold;color:#5B2A86">&#9989;&nbsp; REFORCE COM OS GESTORES DOS POLOS</span><table cellpadding="0" cellspacing="0" style="margin-top:10px"><tr><td style="padding:3px 8px 3px 0;vertical-align:top"><span style="color:#5C3D9E;font-size:13px">&#9679;</span></td><td style="padding:3px 0;font-size:13px;color:#444444;line-height:1.55">Disponibilizar acesso facilitado às instalações no dia e horário agendados;</td></tr><tr><td style="padding:3px 8px 3px 0;vertical-align:top"><span style="color:#5C3D9E;font-size:13px">&#9679;</span></td><td style="padding:3px 0;font-size:13px;color:#444444;line-height:1.55">Garantir a presença de um responsável pelo polo durante todo o período da auditoria;</td></tr><tr><td style="padding:3px 8px 3px 0;vertical-align:top"><span style="color:#5C3D9E;font-size:13px">&#9679;</span></td><td style="padding:3px 0;font-size:13px;color:#444444;line-height:1.55">Manter a documentação de infraestrutura (laudos, ARTs, licenças) organizada e disponível;</td></tr><tr><td style="padding:3px 8px 3px 0;vertical-align:top"><span style="color:#5C3D9E;font-size:13px">&#9679;</span></td><td style="padding:3px 0;font-size:13px;color:#444444;line-height:1.55">Assegurar que laboratórios, insumos e equipamentos estejam limpos e em condições de uso.</td></tr></table></td></tr></table></td></tr><tr><td style="padding:24px 34px 0"><table cellpadding="0" cellspacing="0"><tr><td style="background:#5C3D9E;border-radius:4px;padding:11px 22px"><a href="https://app.smartsheet.com/b/form/019c71b513a67973be44a973a3ee479a" style="font-size:13px;font-weight:bold;color:#ffffff;text-decoration:none">Abrir chamado com a equipe de auditoria</a></td><td style="padding-left:16px"><span style="font-size:11.5px;color:#8a8a8a">Reagendamentos e impedimentos por aqui</span></td></tr></table></td></tr><tr><td style="padding:20px 34px 0"><table width="100%" cellpadding="0" cellspacing="0" style="background:#fafafa;border:1px solid #eee;border-radius:5px"><tr><td style="padding:16px 20px"><span style="font-size:13px;color:#444444;line-height:1.65">Qualquer reagendamento ou impedimento deve ser comunicado à nossa equipe com a maior antecedência possível, para não impactarmos o cronograma. Contamos com o seu apoio.</span></td></tr></table></td></tr><tr><td style="padding:22px 34px"><table width="100%" style="border-top:1px solid #eee"><tr><td style="padding-top:14px"><span style="font-size:12px;font-weight:bold;color:#5B2A86">Regularização e Gestão de Contratos<br/>Auditoria de Laboratórios</span></td><td style="padding-top:14px;text-align:right;vertical-align:bottom"><span style="font-size:20px;color:#9b8fc4">cogna</span><span style="font-size:20px;font-weight:bold;color:#5B2A86">educação</span></td></tr></table><span style="font-size:9px;color:#bbb">Público &middot; Comunicado interno &middot; Modelo institucional</span></td></tr></table></td></tr></table></body></html>'''
