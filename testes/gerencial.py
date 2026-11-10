"""Dados gerenciais para revisão local; não envia emails nem altera as bases."""
from pathlib import Path
import re
import unicodedata

from openpyxl import load_workbook


FIELDS = ('gestor', 'email', 'negocios_nome', 'negocios_email', 'infra_nome',
          'infra_email', 'academico_nome', 'academico_email')
EMAIL = re.compile(r'[^\s@<>;,]+@[^\s@<>;,]+\.[^\s@<>;,]+')


def text(value):
    return '' if value is None else str(value).strip()


def key(value):
    return ' '.join(unicodedata.normalize('NFKD', text(value)).encode('ascii', 'ignore').decode().upper().split())


def person(value):
    value = text(value)
    return '' if key(value) in ('', '-', 'TOTAL', 'NAO INFORMADO') or 'TBD' in key(value) else value


def rows(path, sheet='Export'):
    book = load_workbook(path, read_only=True, data_only=True)
    try:
        values = iter(book[sheet].values)
        headers = [text(h) for h in next(values, ())]
        for values_row in values:
            if not values_row or not any(v is not None for v in values_row):
                continue
            if any(text(v).casefold().startswith(('filtros aplicados:', 'applied filters:')) for v in values_row):
                continue
            yield dict(zip(headers, values_row))
    finally:
        book.close()


def emails(value):
    values = [v.strip() for v in text(value).split(';') if v.strip()]
    if any(not EMAIL.fullmatch(v) or len(v) > 254 for v in values):
        return ''
    return ';'.join(dict.fromkeys(v.lower() for v in values))


def load_directory(folder):
    folder = Path(folder)
    contacts = {}
    for row in rows(folder / 'auditoria-base-gerencial-contatos.xlsx'):
        name = person(row.get('Nome'))
        if name:
            contacts.setdefault(key(name), []).append(row)
    auditors = {}
    for row in rows(folder / 'auditoria-base-gerencial.xlsx', 'AUDITORES'):
        name, email = person(row.get('NOME')), emails(row.get('EMAIL'))
        if name and email:
            if key(name) in auditors and auditors[key(name)]['email'] != email:
                raise ValueError('Auditor acadêmico com emails conflitantes no cadastro')
            auditors[key(name)] = {'nome': name, 'email': email}

    def contact(name):
        found = {emails(r.get('E-mail')) for r in contacts.get(key(name), [])} - {''}
        return next(iter(found)) if len(found) == 1 else ''

    polos = {}
    required = {'NOME UNIDADE SISTEMA', 'GESTOR DE POLO / DIRETOR UNIDADE',
                'EMAIL GESTOR PRISMA / EMAIL DIRETOR DE UNIDADE', 'GRUPO ECONOMICO',
                'GER. COM. / GER. NEG.', 'CONSULTOR DE INFRA', 'AUDITOR ACADEMICO'}
    for row in rows(folder / 'auditoria-base-gerencial.xlsx'):
        if not required.issubset(row):
            raise ValueError('Base gerencial: colunas obrigatórias ausentes')
        polo = person(row['NOME UNIDADE SISTEMA'])
        if not polo:
            continue
        academic = auditors.get(key(row['AUDITOR ACADEMICO']), {})
        negocios, infra = person(row['GER. COM. / GER. NEG.']), person(row['CONSULTOR DE INFRA'])
        record = {'polo': polo, 'gestor': person(row['GESTOR DE POLO / DIRETOR UNIDADE']),
                  'email': emails(row['EMAIL GESTOR PRISMA / EMAIL DIRETOR DE UNIDADE']),
                  'grupo': person(row['GRUPO ECONOMICO']),
                  'negocios_nome': negocios, 'negocios_email': contact(negocios),
                  'infra_nome': infra, 'infra_email': contact(infra),
                  'academico_nome': academic.get('nome', ''), 'academico_email': academic.get('email', '')}
        if key(polo) in polos and polos[key(polo)] != record:
            raise ValueError('Polo duplicado com dados gerenciais conflitantes: ' + polo)
        polos[key(polo)] = record
    return {'polos': polos, 'auditores': sorted(auditors.values(), key=lambda a: key(a['nome']))}


def recipients(polos, directory):
    return [dict(polo=polo, **{f: directory['polos'].get(key(polo), {}).get(f, '') for f in FIELDS})
            for polo in dict.fromkeys(polos)]


def review_recipients(submitted, polos, directory):
    if not isinstance(submitted, list) or len(submitted) > 500:
        raise ValueError('Destinatários: lista de até 500 polos obrigatória')
    wanted = set(polos)
    provided = {}
    auditors = {a['nome']: a['email'] for a in directory['auditores']}
    for row in submitted:
        if not isinstance(row, dict) or not isinstance(row.get('polo'), str):
            raise ValueError('Destinatário inválido')
        polo = row['polo']
        if polo not in wanted or polo in provided:
            raise ValueError('Destinatário duplicado ou fora da carteira selecionada')
        clean = {'polo': polo}
        for field in FIELDS:
            value = row.get(field, '')
            if not isinstance(value, str) or len(value) > 2000 or any(ord(c) < 32 for c in value):
                raise ValueError('Destinatário: texto inválido')
            clean[field] = value.strip()
            if field.endswith('email') or field == 'email':
                if value and not emails(value):
                    raise ValueError('Destinatário: email inválido')
                clean[field] = emails(value)
        if not person(clean['gestor']) or not clean['email']:
            raise ValueError(polo + ': complete o nome e email do gestor do polo')
        if clean['academico_nome'] not in auditors:
            raise ValueError(polo + ': escolha um auditor acadêmico cadastrado')
        clean['academico_email'] = auditors[clean['academico_nome']]
        provided[polo] = clean
    if set(provided) != wanted:
        raise ValueError('Revise os destinatários de todos os polos selecionados')
    return [provided[polo] for polo in dict.fromkeys(polos)]


def support_contacts(items):
    result = {}
    for row in items:
        for role, prefix in (('Gerente de negócios', 'negocios'), ('Consultor de infraestrutura', 'infra'),
                             ('Auditoria acadêmica', 'academico')):
            name, email = row[prefix + '_nome'], row[prefix + '_email']
            if name or email:
                for address in email.split(';'):
                    result[(role, name, address)] = {'funcao': role, 'nome': name, 'email': address, 'telefone': ''}
    return list(result.values())
