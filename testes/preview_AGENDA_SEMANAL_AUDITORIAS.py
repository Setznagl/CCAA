"""Isolated literal port of Mari's LinhaTabela/MontarHTML (no VBA/transport).

Static markup follows Modulo1_NOVO.bas, checked against the saved preview.
Dates use explicit pt-BR weekday names, independent of the host locale.
"""
from datetime import date, datetime
from pathlib import Path

import re

from openpyxl import load_workbook


def _records(path, required):
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        values = iter(workbook.active.values)
        headers = next(values, ())
        if not set(required).issubset(headers):
            raise ValueError(f'{path.name}: colunas obrigatórias ausentes')
        for index, row in enumerate(values, 2):
            if not row or not row[0]:
                continue
            if str(row[0]).lower().startswith(('applied filters:', 'filtros aplicados:')):
                break
            yield index, dict(zip(headers, row))
    finally:
        workbook.close()


def _manager(value):
    text = _text(value).strip()
    if not text or 'tbd' in text.casefold() or text.casefold() in {'-', 'não informado', 'nao informado'}:
        return ''
    return text


def load_mari(root: Path) -> dict[str, dict]:
    """Timeline owns the roster; contact emails belong to poles, never to GOs."""
    folder = Path(root) / 'databases/09-11-26'
    contacts = {}
    for _, row in _records(folder / 'auditoria-tabela-contatos.xlsx', ('Polo', 'Gerente Operacional')):
        polo = _text(row['Polo']).strip()
        contacts.setdefault(polo, set()).add(_manager(row['Gerente Operacional']))
    grouped = {}
    for index, row in _records(folder / 'auditoria-timeline-262.xlsx', ('Polo', 'Laboratório', 'Data agendada', 'semestre_operacional_x')):
        polo = _text(row['Polo']).strip()
        names = contacts.get(polo, set())
        manager = next(iter(names)) if len(names) == 1 and '' not in names else ''
        key = manager.casefold()
        if key not in grouped:
            grouped[key] = {'label': manager or 'Revisão manual — GO ausente/TBD/ambíguo',
                            'draft': {'label': manager, 'email': '', 'reviewed': False, 'rows': []},
                            'warnings': [], 'source_cycles': [], 'polo_count': 0}
        model = grouped[key]
        parsed = _date(row['Data agendada'])
        model['draft']['rows'].append({'id': str(index), 'polo': polo,
            'laboratorio': _text(row['Laboratório']).strip(), 'grupo': '',
            'date': parsed.isoformat(timespec='minutes') if parsed else '', 'selected': True})
        cycle = _text(row['semestre_operacional_x']).strip()
        if cycle and cycle not in model['source_cycles']:
            model['source_cycles'].append(cycle)
        if not manager:
            warning = f'{polo}: GO ausente, TBD ou ambíguo; informe o GO e selecione apenas sua carteira.'
            if warning not in model['warnings']: model['warnings'].append(warning)
        if not parsed:
            model['warnings'].append(f'{polo}: data de agendamento ausente ou inválida; preencher ou desmarcar a linha.')
    result = {}
    for index, key in enumerate(sorted(grouped), 1):
        model = grouped[key]
        model['polo_count'] = len({r['polo'] for r in model['draft']['rows']})
        model['warnings'][:0] = [
            'Todas as datas/laboratórios estão selecionados; não há filtro automático de semana. Revise e desmarque as linhas fora do período desejado.',
            'Grupo econômico por polo e email do GO não constam das novas bases: preenchimento manual obrigatório. O email dos contatos é do gestor de polo e não será reutilizado.']
        result[str(index)] = model
    return result

def review_mari(draft, record):
    """Validate only supplements; immutable source identity is read server-side."""
    def text(value, field, limit=300):
        if not isinstance(value, str) or not value.strip() or len(value) > limit or any(ord(c) < 32 for c in value):
            raise ValueError(f'{field}: preencha um texto válido (até {limit} caracteres)')
        return value.strip()

    if not isinstance(draft, dict) or draft.get('reviewed') is not True:
        raise ValueError('Confirme a revisão das linhas e do período antes de gerar')
    label = text(draft.get('label'), 'Gerente Operacional')
    if not _manager(label):
        raise ValueError('Gerente Operacional: substitua o placeholder por um nome válido')
    email = text(draft.get('email'), 'Email do GO', 254)
    if not re.fullmatch(r'[^\s@<>;,]+@[^\s@<>;,]+\.[^\s@<>;,]+', email):
        raise ValueError('Email do GO: informe um endereço válido')
    rows = draft.get('rows')
    source = {r['id']: r for r in record['draft']['rows']}
    if not isinstance(rows, list) or not rows or len(rows) > min(len(source), 10000):
        raise ValueError('Linhas: selecione ao menos uma linha da base (máximo 10000)')
    seen, groups, selected = set(), {}, []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or row['id'] not in source or row['id'] in seen:
            raise ValueError('Linha inválida, duplicada ou inexistente na base')
        seen.add(row['id'])
        original = source[row['id']]
        if any(row.get(key) != original[key] for key in ('polo', 'laboratorio')):
            raise ValueError('Polo/laboratório: a identificação da fonte não pode ser alterada')
        if not isinstance(row.get('selected'), bool):
            raise ValueError('Seleção da linha inválida')
        if not row['selected']:
            continue
        group = text(row.get('grupo'), 'Grupo econômico')
        if 'tbd' in group.casefold():
            raise ValueError('Grupo econômico: substitua o placeholder por um grupo válido')
        if original['polo'] in groups and groups[original['polo']] != group:
            raise ValueError('Grupo econômico deve ser o mesmo em todas as linhas de um polo')
        groups[original['polo']] = group
        value = text(row.get('date'), 'Data de agendamento', 16)
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}(T\d{2}:\d{2})?', value):
            raise ValueError('Data de agendamento: informe data/hora ISO válida')
        try:
            day = datetime.fromisoformat(value)
        except ValueError:
            raise ValueError('Data de agendamento inválida') from None
        selected.append({'polo': original['polo'], 'laboratorio': original['laboratorio'], 'grupo': group, 'date': day})
    if not selected:
        raise ValueError('Selecione ao menos uma linha de agendamento')
    return {'label': label, 'polo_count': len(groups), 'rows': selected}


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
    laboratory = row.get('laboratorio', '')
    polo = _esc(row['polo'])
    if laboratory:
        polo += f'<br/><span style="font-size:10.5px;color:#8a8a8a">{_esc(laboratory)}</span>'
        if day:
            cell = cell.replace('</td>', f'<br/><span style="font-size:10.5px;color:#8a8a8a">{day:%H:%M}</span></td>')
    group = _text(row['grupo']).strip(' ') or '-'
    return (f'<tr><td style="background:{background};padding:11px 0 11px 14px;border-bottom:1px solid #E3E3E3;'
            f'border-left:3px solid {stripe};font-size:12px;color:#a9a9a9">{index}</td>'
            f'<td style="{base}font-weight:bold;color:#5B2A86">{polo}</td>'
            f'<td style="{base}color:#444444">{_esc(group)}</td>{cell}</tr>')


def render_mari(model: dict, today: date) -> str:
    """Return HTMLBody only; today replaces VBA Date without reading the clock."""
    name = _esc(_text(model['label']).strip(' ') or 'Gerente Operacional')
    count = len({row['polo'] for row in model['rows']})
    noun = 'polo' if count == 1 else 'polos'
    dates = [day for row in model['rows'] if (day := _date(row['date'])) is not None]
    period = 'A definir'
    preheader = f'{len(model["rows"])} auditoria(s) de laboratório na sua carteira.'
    if dates:
        first, last = min(dates), max(dates)
        period = first.strftime('%d/%m/%Y') if first == last else first.strftime('%d/%m') + ' a ' + last.strftime('%d/%m/%Y')
        preheader += f' Próxima: {_WEEKDAYS[first.weekday()]}, {first:%d/%m}.'
    preheader = _esc(preheader)
    rows_html = ''.join(_row(row, index, today) for index, row in enumerate(model['rows'], 1))
    return f'''<html><head><meta charset="UTF-8"></head><body style="margin:0;padding:0;background:#eef0f2;font-family:Arial,Helvetica,sans-serif"><div style="display:none;font-size:1px;color:#eef0f2;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden">{preheader}</div><table width="100%" cellpadding="0" cellspacing="0" style="background:#eef0f2;padding:24px 0"><tr><td align="center"><table width="780" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:6px"><tr><td style="background:#F1EBF8;padding:18px 34px"><table width="100%"><tr><td><span style="font-size:15px;font-weight:bold;color:#5B2A86">-RGC &nbsp;&#9679;&#9679;</span><br/><span style="font-size:13px;font-weight:bold;color:#5B2A86">Regularização e Gestão de Contratos</span><br/><span style="font-size:12px;color:#6b6b6b">Auditoria de Laboratórios</span></td><td style="text-align:right;vertical-align:middle"><span style="font-size:11px;font-weight:bold;color:#5B2A86;letter-spacing:1px">DOCUMENTO OFICIAL</span></td></tr></table></td></tr><tr><td style="padding:22px 34px 0"><span style="font-size:11px;font-weight:bold;color:#5C3D9E;letter-spacing:1px">AGENDA SEMANAL DE AUDITORIAS</span><br/><span style="font-size:21px;font-weight:bold;color:#222">Auditoria de Laboratórios &mdash; Polos da sua carteira</span></td></tr><tr><td style="padding:16px 34px 0"><table width="100%" cellpadding="0" cellspacing="0" style="background:#F1EBF8;border-radius:5px"><tr><td width="46%" style="padding:14px 20px;border-right:1px solid #ddd2ec"><span style="font-size:10px;font-weight:bold;color:#5B2A86;letter-spacing:0.5px">GERENTE OPERACIONAL</span><br/><span style="font-size:15px;font-weight:bold;color:#222">{name}</span></td><td width="32%" style="padding:14px 20px;border-right:1px solid #ddd2ec"><span style="font-size:10px;font-weight:bold;color:#5B2A86;letter-spacing:0.5px">PERÍODO</span><br/><span style="font-size:15px;font-weight:bold;color:#222">{period}</span></td><td width="22%" style="padding:14px 20px"><span style="font-size:10px;font-weight:bold;color:#5B2A86;letter-spacing:0.5px">AUDITORIAS</span><br/><span style="font-size:24px;font-weight:bold;color:#5B2A86;line-height:1.1">{count}</span> <span style="font-size:13px;color:#6b6b6b">{noun}</span></td></tr></table></td></tr><tr><td style="padding:18px 34px 0"><span style="font-size:13.5px;color:#444444;line-height:1.65">Olá, {name}! Segue a relação dos polos da sua carteira que serão auditados pela equipe de <b>Auditoria de Laboratórios</b>. Pedimos que reforce diretamente com os gestores a importância do recebimento e do apoio às equipes em campo.</span></td></tr><tr><td style="padding:26px 34px 0"><span style="font-size:14px;font-weight:bold;color:#5C3D9E;letter-spacing:0.5px">&#128197;&nbsp; AUDITORIAS PROGRAMADAS</span><span style="font-size:11.5px;color:#8a8a8a">&nbsp; &middot; &nbsp;em ordem de data</span></td></tr><tr><td style="padding:9px 34px 0"><table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #E3E3E3;border-collapse:collapse"><tr style="background:#5C3D9E"><td width="34" style="padding:9px 0 9px 14px"><span style="color:#c9b8e6;font-size:11px;font-weight:bold">#</span></td><td style="padding:9px 14px"><span style="color:#fff;font-size:11px;font-weight:bold">POLO</span></td><td style="padding:9px 14px"><span style="color:#fff;font-size:11px;font-weight:bold">GRUPO ECONÔMICO</span></td><td width="150" style="padding:9px 14px;text-align:center"><span style="color:#fff;font-size:11px;font-weight:bold">DATA DA AUDITORIA</span></td></tr>{rows_html}</table></td></tr><tr><td style="padding:26px 34px 0"><table width="100%" cellpadding="0" cellspacing="0" style="background:#F7F4FC;border:1px solid #e4dcf2;border-radius:5px"><tr><td style="padding:16px 20px"><span style="font-size:13px;font-weight:bold;color:#5B2A86">&#9989;&nbsp; REFORCE COM OS GESTORES DOS POLOS</span><table cellpadding="0" cellspacing="0" style="margin-top:10px"><tr><td style="padding:3px 8px 3px 0;vertical-align:top"><span style="color:#5C3D9E;font-size:13px">&#9679;</span></td><td style="padding:3px 0;font-size:13px;color:#444444;line-height:1.55">Disponibilizar acesso facilitado às instalações no dia e horário agendados;</td></tr><tr><td style="padding:3px 8px 3px 0;vertical-align:top"><span style="color:#5C3D9E;font-size:13px">&#9679;</span></td><td style="padding:3px 0;font-size:13px;color:#444444;line-height:1.55">Garantir a presença de um responsável pelo polo durante todo o período da auditoria;</td></tr><tr><td style="padding:3px 8px 3px 0;vertical-align:top"><span style="color:#5C3D9E;font-size:13px">&#9679;</span></td><td style="padding:3px 0;font-size:13px;color:#444444;line-height:1.55">Manter a documentação de infraestrutura (laudos, ARTs, licenças) organizada e disponível;</td></tr><tr><td style="padding:3px 8px 3px 0;vertical-align:top"><span style="color:#5C3D9E;font-size:13px">&#9679;</span></td><td style="padding:3px 0;font-size:13px;color:#444444;line-height:1.55">Assegurar que laboratórios, insumos e equipamentos estejam limpos e em condições de uso.</td></tr></table></td></tr></table></td></tr><tr><td style="padding:24px 34px 0"><table cellpadding="0" cellspacing="0"><tr><td style="background:#5C3D9E;border-radius:4px;padding:11px 22px"><a href="https://app.smartsheet.com/b/form/019c71b513a67973be44a973a3ee479a" style="font-size:13px;font-weight:bold;color:#ffffff;text-decoration:none">Abrir chamado com a equipe de auditoria</a></td><td style="padding-left:16px"><span style="font-size:11.5px;color:#8a8a8a">Reagendamentos e impedimentos por aqui</span></td></tr></table></td></tr><tr><td style="padding:20px 34px 0"><table width="100%" cellpadding="0" cellspacing="0" style="background:#fafafa;border:1px solid #eee;border-radius:5px"><tr><td style="padding:16px 20px"><span style="font-size:13px;color:#444444;line-height:1.65">Qualquer reagendamento ou impedimento deve ser comunicado à nossa equipe com a maior antecedência possível, para não impactarmos o cronograma. Contamos com o seu apoio.</span></td></tr></table></td></tr><tr><td style="padding:22px 34px"><table width="100%" style="border-top:1px solid #eee"><tr><td style="padding-top:14px"><span style="font-size:12px;font-weight:bold;color:#5B2A86">Regularização e Gestão de Contratos<br/>Auditoria de Laboratórios</span></td><td style="padding-top:14px;text-align:right;vertical-align:bottom"><span style="font-size:20px;color:#9b8fc4">cogna</span><span style="font-size:20px;font-weight:bold;color:#5B2A86">educação</span></td></tr></table><span style="font-size:9px;color:#bbb">Público &middot; Comunicado interno &middot; Modelo institucional</span></td></tr></table></td></tr></table></body></html>'''
