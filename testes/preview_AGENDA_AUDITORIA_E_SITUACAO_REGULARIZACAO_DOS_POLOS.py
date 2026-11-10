"""Prévia local do consolidado; nenhuma macro, transporte ou escrita nas fontes."""
from datetime import date, datetime
from html import escape
from pathlib import Path
from string import Template
import math
import json
import os
import tempfile
from openpyxl import Workbook, load_workbook
import re
from urllib.parse import quote, unquote, urlsplit
from zipfile import BadZipFile
import unicodedata

import pandas as pd

def _write_emails(data, names, contacts, operational):
    """Exportação derivada; nunca fornece dados ao HTML."""
    temporary = None
    try:
        signature = json.dumps([(name, (data / name).stat().st_mtime_ns,
                                 (data / name).stat().st_size) if (data / name).is_file()
                                else (name, None, None) for name in names])
        output = data / 'emails.xlsx'
        if output.is_file():
            try:
                previous = load_workbook(output, read_only=True)
                unchanged = previous.properties.description == signature
                previous.close()
                if unchanged:
                    return
            except (OSError, ValueError, BadZipFile):
                pass
        if not data.is_dir():
            return
        wb = Workbook()
        ws = wb.active
        ws.title = 'Emails'
        ws.append(['Polo', 'Email', 'Enviar'])
        for key in sorted(operational):
            rows = [r for r in contacts.get(key, []) if _flag(r['Perfil']) == 'GESTOR PRINCIPAL']
            emails = {}
            for row in rows:
                for email in _text(row['E-mail']).split(';'):
                    email = email.strip()
                    if email:
                        emails.setdefault(email.casefold(), email)
            polo = _text(rows[0]['Polo']) if rows else key
            values = [polo, ';'.join(emails[k] for k in sorted(emails)), '']
            # Excel interprets these prefixes even when the source is plain text.
            ws.append(["'" + v if v.lstrip().startswith(('=', '+', '-', '@')) else v for v in values])
        wb.properties.description = signature
        with tempfile.NamedTemporaryFile(prefix='.emails-', suffix='.xlsx', dir=data, delete=False) as handle:
            temporary = Path(handle.name)
        try:
            wb.save(temporary)
        finally:
            wb.close()
        os.replace(temporary, output)
    except (OSError, ValueError, TypeError, BadZipFile):
        return 'Não foi possível gravar emails.xlsx; a prévia continua usando as fontes originais.'
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass  # Uma falha de limpeza não pode impedir a prévia manual.


def _text(value):
    return '' if pd.isna(value) else str(value).strip()


def _key(value):
    return ' '.join(_text(value).upper().split())


def _flag(value):
    return unicodedata.normalize('NFKD', _key(value)).encode('ascii', 'ignore').decode()


def _source_date(value):
    if pd.isna(value):
        return ''
    if isinstance(value, (datetime, date)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    text = _text(value)
    if not text:
        return ''
    return date.fromisoformat(text).isoformat()


def _cycle(value):
    text = str(value).strip()
    if re.fullmatch(r'\d{2}[12]', text):
        return text
    if re.fullmatch(r'\d{2}\.[12]', text):
        return text.replace('.', '')
    if re.fullmatch(r'\d{2}[12]\.0', text):
        return text[:-2]
    raise ValueError('Ciclo deve usar 261/26.1 ou 262/26.2 (semestre 1 ou 2).')


def _empty_draft():
    return {
        'gestor': '', 'ciclo': '', 'polos': [], 'checklist': [], 'agenda': [],
        'praticas': [], 'laboratorios': [], 'reprovados_sem_retorno': None,
        'prazo_praticas': '', 'prazo_auditorias': '',
        'link_relatorio': 'https://prisma.kroton.com.br/comunicados/10484',
        'link_atendimento': 'https://app.smartsheet.com/b/publish?EQBCT=fbc7e2e80e684398ba2a34ec61cee9f6',
        'contatos': [{'funcao': 'Auditoria acadêmica e laboratórios', 'nome': '',
                      'email': 'auditoria.academica@kroton.com.br', 'telefone': ''}],
    }


def load_consolidado(root: Path) -> dict:
    records = {'manual': {'label': 'Preenchimento manual', 'polo_count': 0,
                          'draft': _empty_draft(), 'source_cycles': [],
                          'warnings': ['Prévia manual: dados não conferidos com bases operacionais.']}}
    data = Path(root) / 'databases/09-11-26'
    warnings = ['Checklist CL2026 sem base preenchida; informe nota, status, observação e auditor manualmente. Vereditos não equivalem ao checklist.',
                'Prazos e contatos de apoio sem fonte ficam manuais; confirme antes de usar.']
    names = ('auditoria-tabela-contatos.xlsx', 'auditoria-apps-prazo.xlsx',
             'auditoria-timeline-262.xlsx', 'auditoria-polos-acompanhamento-262.xlsx')
    columns = (
        ['Polo', 'Nome', 'E-mail', 'Perfil'],
        ['Polo', 'Total de Aulas', 'Comprovadas', 'Pendentes'],
        ['Polo', 'semestre_operacional_x', 'Laboratório', 'Tipo auditoria', 'Auditor',
         'Agendada', 'Data agendada', 'Realizada', 'Data realização', 'Finalizada', 'Parecer Auditoria'],
        ['Polo', 'Rep. Sem Retorno'])
    sources, export_cycles = {}, {}
    for name, required in zip(names, columns):
        grouped, cycles = {}, set()
        try:
            frame = pd.read_excel(data / name, sheet_name='Export', usecols=required)
            for row in frame.to_dict('records'):
                polo = _text(row['Polo'])
                if not polo:
                    continue
                if polo.startswith(('Applied filters:', 'Filtros aplicados:')):
                    cycles.update(_cycle(c) for c in re.findall(
                        r'semestre_operacional(?:_x)?\s+(?:is|é|=)\s*(\d{2}\.?[12])\b', polo))
                    continue
                grouped.setdefault(_key(polo), []).append(row)
            sources[name] = grouped
        except (OSError, ValueError, KeyError, TypeError, OverflowError, BadZipFile, ImportError):
            sources[name] = {}
            warnings.append(f'Fonte {name} ausente ou inválida; complete a seção manualmente.')
        export_cycles[name] = cycles
    contacts, apps, timeline, followup = (sources[n] for n in names)
    operational = set(apps) | set(timeline) | set(followup)
    groups, manager_emails = {}, {}
    association_warnings = []
    for key in sorted(operational):
        found = False
        for row in contacts.get(key, []):
            if _flag(row['Perfil']) != 'GESTOR PRINCIPAL':
                continue
            manager = _text(row['Nome'])
            if not manager:
                association_warnings.append(f'{_text(row["Polo"])}: gestor principal sem nome; associação ambígua, complete manualmente.')
                continue
            found = True
            identity = _key(manager)
            group = groups.setdefault(identity, {'name': manager, 'polos': {}})
            group['polos'].setdefault(key, _text(row['Polo']))
            email = _text(row['E-mail'])
            if email:
                manager_emails.setdefault(identity, set()).add(email.casefold())
        if not found:
            association_warnings.append(f'{key}: sem gestor principal identificado; carteira manual necessária.')
    export_warning = _write_emails(data, names, contacts, operational)
    if export_warning:
        warnings.append(export_warning)
    records['manual']['warnings'].extend(warnings + association_warnings)
    for index, (identity, group) in enumerate(sorted(groups.items()), 1):
        draft = _empty_draft()
        draft.update(gestor=group['name'], polos=sorted(group['polos'].values()))
        record_warnings, cycles, approval = list(warnings), set(), []
        if len(manager_emails.get(identity, ())) > 1:
            record_warnings.append('Identidade preservada pelo nome, mas há múltiplos emails; associação potencialmente ambígua, revise a carteira.')
        for polo in draft['polos']:
            key = _key(polo)
            draft['checklist'].append({'polo': polo, 'nota': None, 'status': '', 'observacao': '', 'auditor': ''})
            rows = apps.get(key, [])
            if len(rows) == 1:
                counts = {}
                for field, column in zip(('previstas', 'comprovadas', 'pendentes'), columns[1][1:]):
                    try:
                        value = rows[0][column]
                        counts[field] = _number(None if pd.isna(value) else value, column, integer=True)
                    except ValueError:
                        counts[field] = None
                    if counts[field] is None:
                        record_warnings.append(f'{polo}: {column} ausente ou inválida; preenchimento manual necessário.')
                draft['praticas'].append(dict(polo=polo, **counts))
                cycles.update(export_cycles[names[1]])
                if not export_cycles[names[1]]:
                    record_warnings.append(f'{polo}: apps com ciclo não declarado; não inferido de outras fontes.')
            else:
                record_warnings.append(f'{polo}: práticas sem fonte única; preenchimento manual necessário.')
            labs = timeline.get(key, [])
            if not labs:
                record_warnings.append(f'{polo}: agenda e pareceres sem fonte correspondente.')
            for row in labs:
                try:
                    cycles.add(_cycle(row['semestre_operacional_x']))
                except ValueError:
                    cycles.update(export_cycles[names[2]])
                    record_warnings.append(f'{polo}: timeline com semestre da linha ausente ou inválido; confira a origem.')
                performed = _flag(row['Realizada']) == 'SIM'
                status = 'Finalizada' if _flag(row['Finalizada']) == 'SIM' else 'Realizada' if performed else 'Agendada' if _flag(row['Agendada']) == 'SIM' else ''
                try:
                    when = _source_date(row['Data realização'] if performed else row['Data agendada'])
                except (ValueError, TypeError):
                    when = ''
                    record_warnings.append(f'{polo}: data da timeline inválida; complete manualmente.')
                draft['agenda'].append({'polo': polo, 'tipo': _text(row['Tipo auditoria']),
                    'ambiente': _text(row['Laboratório']), 'data': when,
                    'auditor': _text(row['Auditor']), 'status': status})
                draft['laboratorios'].append({'polo': polo, 'laboratorio': _text(row['Laboratório']),
                                             'parecer': _text(row['Parecer Auditoria'])})
            rows = followup.get(key, [])
            value = None
            if len(rows) == 1:
                try:
                    raw = rows[0]['Rep. Sem Retorno']
                    value = _number(None if pd.isna(raw) else raw, 'Rep. Sem Retorno', integer=True)
                except ValueError:
                    pass
            if value is None:
                record_warnings.append(f'{polo}: indicador Rep. Sem Retorno sem fonte única e completa; não equivale ao total de reprovados.')
            else:
                approval.append(value)
                cycles.update(export_cycles[names[3]])
                if not export_cycles[names[3]]:
                    record_warnings.append(f'{polo}: acompanhamento com ciclo não declarado; não inferido de outras fontes.')
        if len(approval) == len(draft['polos']):
            draft['reprovados_sem_retorno'] = sum(approval)
        draft['ciclo'] = min(cycles) if cycles else ''
        if len(cycles) > 1:
            record_warnings.append('Fontes de ciclos mistos; confirme a compatibilidade antes de usar.')
        records[str(index)] = {'label': group['name'], 'polo_count': len(draft['polos']),
                               'draft': draft, 'warnings': record_warnings, 'source_cycles': sorted(cycles)}
    return records


def _string(value, field, limit=2000, required=False):
    if (not isinstance(value, str) or len(value) > limit or
            re.search(r'[\x00-\x08\x0b-\x1f\x7f\ud800-\udfff]', value) or (required and not value.strip())):
        raise ValueError(f'{field}: texto inválido (limite {limit} caracteres).')
    return value


def _number(value, field, integer=False):
    if value is None:
        return None
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or
            not 0 <= value <= 1_000_000_000 or not math.isfinite(value) or
            (integer and value != int(value))):
        raise ValueError(f'{field}: informe número finito não negativo' + (' inteiro.' if integer else '.'))
    return value


def _iso(value, field):
    _string(value, field, 10)
    if value:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            raise ValueError(f'{field}: use data ISO AAAA-MM-DD.')
        try:
            date.fromisoformat(value)
        except ValueError:
            raise ValueError(f'{field}: data inválida.') from None


def _url(value, field):
    _string(value, field, 2048)
    if not value:
        return
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme.lower() in ('http', 'https') and parsed.hostname and
                 not parsed.username and not parsed.password and parsed.port != 0 and
                 not re.search(r'[\s<>"\'\\\\\x00-\x1f\x7f]', unquote(value)))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError(f'{field}: URL http(s) inválida ou insegura.')


def _validate(draft):
    defaults = _empty_draft()
    if not isinstance(draft, dict) or draft.keys() - defaults.keys():
        raise ValueError('draft: objeto com campos conhecidos obrigatório; metadados não são editáveis.')
    result = defaults | draft
    _string(result['gestor'], 'gestor', 300, required=True)
    _string(result['ciclo'], 'ciclo', 4, required=True)
    if not re.fullmatch(r'\d{2}\.?[12]', result['ciclo']):
        raise ValueError('ciclo: use 261/26.1 ou 262/26.2 (semestre 1 ou 2).')
    polos = result['polos']
    if not isinstance(polos, list) or len(polos) > 500:
        raise ValueError('polos: lista de até 500 polos obrigatória.')
    for polo in polos:
        _string(polo, 'polos', 500, required=True)
    if len({_key(p) for p in polos}) != len(polos):
        raise ValueError('polos: carteira contém polos duplicados.')
    schema = {
        'checklist': {'polo': '', 'nota': None, 'status': '', 'observacao': '', 'auditor': ''},
        'agenda': {'polo': '', 'tipo': '', 'ambiente': '', 'data': '', 'auditor': '', 'status': ''},
        'praticas': {'polo': '', 'previstas': None, 'comprovadas': None, 'pendentes': None},
        'laboratorios': {'polo': '', 'laboratorio': '', 'parecer': ''},
        'contatos': {'funcao': '', 'nome': '', 'email': '', 'telefone': ''},
    }
    for section, fields in schema.items():
        rows = result[section]
        if not isinstance(rows, list) or len(rows) > 2000:
            raise ValueError(f'{section}: lista de até 2000 linhas obrigatória.')
        validated = []
        for index, row in enumerate(rows, 1):
            field = f'{section} linha {index}'
            if not isinstance(row, dict) or row.keys() - fields.keys():
                raise ValueError(f'{field}: objeto com campos conhecidos obrigatório.')
            row = fields | row
            for key, value in row.items():
                name = f'{field}, {key}'
                if key in ('nota', 'previstas', 'comprovadas', 'pendentes'):
                    _number(value, name, integer=key != 'nota')
                elif key == 'data':
                    _iso(value, name)
                else:
                    _string(value, name, 254 if key == 'email' else 100 if key == 'telefone' else 2000)
            if section != 'contatos' and row['polo'] not in polos:
                raise ValueError(f'{field}: polo não pertence à carteira selecionada.')
            if section == 'contatos' and row['email'] and not re.fullmatch(
                    r"[A-Za-z0-9.!#$%&'*+/=^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+", row['email']):
                raise ValueError(f'{field}: email inválido ou inseguro.')
            validated.append(row)
        result[section] = validated
    _number(result['reprovados_sem_retorno'], 'reprovados_sem_retorno', integer=True)
    for key in ('prazo_praticas', 'prazo_auditorias'):
        _iso(result[key], key)
    for key in ('link_relatorio', 'link_atendimento'):
        _url(result[key], key)
    return result


def _link(value, email=False):
    if not value:
        return 'Não informado'
    href = 'mailto:' + quote(value, safe='@') if email else value
    return f'<a href="{escape(href, quote=True)}" style="font-size:12.5px;color:#7B2D8E">{escape(value, quote=True)}</a>'


def _display(value):
    return escape('Não informado' if value is None or value == '' else str(value), quote=True)


def _rows(rows, columns):
    if not rows:
        return f'<tr><td colspan="{len(columns)}" style="padding:10px 14px;font-size:13px;color:#444444">Não informado — seção vazia</td></tr>'
    result = []
    for row in rows:
        cells = []
        for index, column in enumerate(columns):
            color = '#5B2A86' if index == 0 else '#444444'
            weight = 'bold' if index == 0 or column in ('nota', 'pendentes', 'percentual', 'parecer', 'data', 'status') else 'normal'
            align = 'center' if column in ('nota', 'previstas', 'comprovadas', 'pendentes', 'percentual', 'parecer', 'data', 'status') else 'left'
            cells.append(f'<td style="padding:10px 14px;border-bottom:1px solid #E3E3E3;text-align:{align};font-size:13px;font-weight:{weight};color:{color}">{_display(row.get(column))}</td>')
        result.append('<tr>' + ''.join(cells) + '</tr>')
    return ''.join(result)


def render_consolidado(draft: dict, sample_path: Path, source_cycles=(), warnings=()) -> str:
    """Usa a cópia parametrizada da arte; nunca os dados preenchidos de sample_path."""
    draft = _validate(draft)
    cycle = _cycle(draft['ciclo'])
    values = {key: _display(value) for key, value in draft.items() if not isinstance(value, list)}
    values.update(ciclo=cycle[:2] + '.' + cycle[2:], polo_count=len(draft['polos']),
                  polos='; '.join(_display(p) for p in draft['polos']) or 'Não informado')
    for section, columns in {
        'checklist': ('polo', 'nota', 'status', 'observacao', 'auditor'),
        'agenda': ('polo', 'tipo', 'ambiente', 'data', 'auditor', 'status'),
        'praticas': ('polo', 'previstas', 'comprovadas', 'pendentes', 'percentual'),
        'laboratorios': ('polo', 'laboratorio', 'parecer'),
    }.items():
        rows = draft[section]
        if section == 'praticas':
            if rows:
                totals = {key: sum(row[key] for row in rows) if all(row[key] is not None for row in rows) else None
                          for key in ('previstas', 'comprovadas', 'pendentes')}
                rows = [*rows, dict(polo='TOTAL INFORMADO', **totals)]
            rows = [dict(row, percentual=(f"{row['comprovadas'] / row['previstas'] * 100:.0f}%"
                                         if row.get('previstas') and row.get('comprovadas') is not None else None)) for row in rows]
        values[section] = _rows(rows, columns)
    for key in ('link_relatorio', 'link_atendimento'):
        values[key] = _link(draft[key])
    values['contatos'] = '<br/>'.join(
        ' — '.join(_link(row[k], email=True) if k == 'email' else _display(row[k])
                   for k in ('funcao', 'nome', 'email', 'telefone'))
        for row in draft['contatos']) or 'Não informado'
    cycles = sorted({_cycle(c) for c in source_cycles})
    notices = ['PRÉVIA — dados editáveis, sem certificação operacional.',
               'Fonte real: ' + (', '.join(cycles) if cycles else 'semestre não identificado ou preenchimento manual')]
    if cycles and (cycles != [cycle]):
        notices.append('Ciclo do título alterado ou fontes de ciclos mistos: não atualiza nem certifica a base original.')
    notices.extend(warnings)
    values['aviso'] = '<br/>'.join(_display(w) for w in notices)
    return Template((Path(__file__).parent / 'templates/consolidado.html').read_text(encoding='utf-8')).substitute(values)
