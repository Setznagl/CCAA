"""Prévia acadêmica local: apenas dados do corpo, sem disparador ou transporte."""
from datetime import date
from copy import deepcopy
from html import escape
from math import isfinite
from numbers import Real
from pathlib import Path
import re

import pandas

TITULO = "AGENDA_REGULARIZACAO_AUDITORIA_ACADEMICA"
SUBTITULO = ""
AREA_MACRO = "Regulação e Controle de Polos e Unidades"
SUB_AREA = "Aliança Jovens e Adultos"


def chave(polo):
    codigos = re.findall(r"\((\d+)\)", polo)
    return codigos[-1] if codigos else polo.split(" - ")[0].strip().upper()


def registros(path, required):
    frame = pandas.read_excel(path)
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"Colunas ausentes em {path.name}: {', '.join(sorted(missing))}")
    nomes = frame['Polo'].fillna('').astype(str).str.strip()
    return frame[nomes.ne('') & ~nomes.str.match(r'(?i)^(applied filters|filtros aplicados)\s*:')]


def contagem(value):
    if pandas.isna(value):
        return None
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value) or value < 0 or int(value) != value:
        raise ValueError('Contagem inválida nas práticas: esperado inteiro não negativo')
    return int(value)


def load_aulas(databases_dir):
    databases_dir = Path(databases_dir)
    polos = {}
    for _, row in registros(databases_dir / 'auditoria-apps-prazo.xlsx',
                            ('Polo', 'Total de Aulas', 'Comprovadas', 'Pendentes')).iterrows():
        nome = str(row['Polo']).strip()
        if chave(nome) in polos:
            raise ValueError('Polo duplicado na base agregada de práticas')
        polos[chave(nome)] = {
            'nome': nome, 'label': nome, 'polo_count': 1,
            'praticas': dict(zip(('previstas', 'comprovadas', 'pendentes'),
                                (contagem(row[c]) for c in ('Total de Aulas', 'Comprovadas', 'Pendentes')))),
            'labs_lista': [],
        }
    for _, row in registros(databases_dir / 'auditoria-timeline-262.xlsx',
                            ('Polo', 'Laboratório', 'Parecer Auditoria')).iterrows():
        nome = str(row['Polo']).strip()
        model = polos.setdefault(chave(nome), {
            'nome': nome, 'label': nome, 'polo_count': 1,
            'praticas': None, 'labs_lista': [],
        })
        model['labs_lista'].append({
            'nome': None if pandas.isna(row['Laboratório']) else str(row['Laboratório']).strip(),
            'parecer': None if pandas.isna(row['Parecer Auditoria']) else str(row['Parecer Auditoria']).strip(),
        })
    return dict(sorted(polos.items(), key=lambda item: item[1]['label']))


def draft_aulas(polo):
    return {'praticas': deepcopy(polo['praticas']) or dict.fromkeys(('previstas', 'comprovadas', 'pendentes')),
            'praticas_aplicaveis': True, 'labs_lista': deepcopy(polo['labs_lista']),
            'labs_status': 'informado' if polo['labs_lista'] else '',
            'prazo_praticas': '', 'prazo_auditoria': '', 'reviewed': False}


def prazo_manual(polo, campo):
    if ((campo == 'prazo_praticas' and polo.get('praticas_aplicaveis') is False)
            or (campo == 'prazo_auditoria' and polo.get('labs_status') == 'nao_aplicavel')):
        return 'Não aplicável'
    value = polo.get(campo)
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError(f'Informe {campo} manualmente')
    return date.fromisoformat(value).strftime('%d/%m/%Y')


def review_aulas(draft, source):
    if draft.get('reviewed') is not True:
        raise ValueError('Confirme a revisão dos dados do polo')
    if type(draft.get('praticas_aplicaveis')) is not bool:
        raise ValueError('Informe a aplicabilidade das práticas')
    result = deepcopy(source)
    for campo in ('prazo_praticas', 'prazo_auditoria'):
        prazo_manual(draft, campo)
        result[campo] = draft.get(campo, '')
    result['praticas'] = None
    if draft['praticas_aplicaveis']:
        counts = draft.get('praticas')
        if not isinstance(counts, dict):
            raise ValueError('Informe as contagens de práticas')
        result['praticas'] = {}
        for field in ('previstas', 'comprovadas', 'pendentes'):
            value = counts.get(field)
            if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
                raise ValueError(f'Informe práticas {field}; ausência não é zero')
            result['praticas'][field] = contagem(value)
    result['praticas_aplicaveis'] = draft['praticas_aplicaveis']
    status = draft.get('labs_status')
    if status not in ('informado', 'nao_aplicavel'):
        raise ValueError('Informe os laboratórios/pareceres ou confirme não aplicável')
    labs = draft.get('labs_lista')
    if not isinstance(labs, list) or len(labs) > 500:
        raise ValueError('Lista de laboratórios inválida')
    if status == 'informado' and not labs:
        raise ValueError('Informe ao menos um laboratório e parecer')
    result['labs_lista'] = []
    if status == 'informado':
        for lab in labs:
            if not isinstance(lab, dict):
                raise ValueError('Laboratório inválido')
            item = {}
            for field in ('nome', 'parecer'):
                value = lab.get(field)
                if not isinstance(value, str) or not value.strip() or len(value) > 300:
                    raise ValueError(f'Informe laboratório {field} (até 300 caracteres)')
                item[field] = value.strip()
            result['labs_lista'].append(item)
    result['labs_status'] = status
    return result


def render_aulas(polo):
    prazo_praticas = prazo_manual(polo, 'prazo_praticas')
    prazo_auditoria = prazo_manual(polo, 'prazo_auditoria')
    totais = polo['praticas'] or {}
    total_prev = totais.get('previstas')
    total_comp = totais.get('comprovadas')
    total_pend = totais.get('pendentes')
    pct_total = None
    if total_prev is not None and total_comp is not None:
        pct_total = total_comp / total_prev * 100 if total_prev > 0 else 0

    # Cada linha da timeline informa laboratório e parecer, sem suplementos inferidos.
    lista_labs = polo.get("labs_lista") or []
    lab_total = len(lista_labs)

    # Cor / rótulo / "o que falta" por parecer da auditoria
    def info_parecer(parecer):
        p = (parecer or '').strip().lower()
        if p.startswith("aprov"):
            return "#4CAF50", "Aprovado", "Regularizado — nenhuma ação necessária."
        if p.startswith("reprov"):
            return "#C62828", "Reprovado", "Verificar e regularizar as pendências apontadas na auditoria."
        if p.startswith("pend"):
            return "#E6A817", "Pendente", "Agendar e realizar a auditoria do laboratório."
        return "#757575", "Sem parecer", "Aguardando definição da auditoria."

    lab_aprov = sum(1 for l in lista_labs if (l["parecer"] or "").lower().startswith("aprov"))
    lab_repr = sum(1 for l in lista_labs if (l["parecer"] or "").lower().startswith("reprov"))
    lab_pend = sum(1 for l in lista_labs if (l["parecer"] or "").lower().startswith("pend"))
    plural = "laboratório" if lab_total == 1 else "laboratórios"

    if lab_total > 0:
        partes = [f"<b>{lab_total}</b> {plural} no total"]
        if lab_aprov:
            partes.append(f'<span style="color:#4CAF50;font-weight:bold">{lab_aprov} aprovado(s)</span>')
        if lab_repr:
            partes.append(f'<span style="color:#C62828;font-weight:bold">{lab_repr} reprovado(s)</span>')
        if lab_pend:
            partes.append(f'<span style="color:#E6A817;font-weight:bold">{lab_pend} pendente(s)</span>')
        labs_txt = " — ".join(partes)

    # Tabela com cada laboratório, parecer e o que falta para aprovar
    linhas_labs = ""
    for l in sorted(lista_labs, key=lambda x: x["nome"] or ""):
        cor, rotulo, falta = info_parecer(l["parecer"])
        linhas_labs += f"""
        <tr>
          <td style="padding:9px 12px;border-bottom:1px solid #f0f0f0;font-size:13px;color:#333">{escape(l['nome']) if l['nome'] else 'Não informado'}</td>
          <td style="padding:9px 12px;border-bottom:1px solid #f0f0f0;text-align:center;white-space:nowrap">
            <span style="background:{cor};color:#fff;font-size:11px;font-weight:bold;padding:3px 10px;border-radius:3px">{rotulo}</span>
          </td>
          <td style="padding:9px 12px;border-bottom:1px solid #f0f0f0;font-size:12px;color:#555">{falta}</td>
        </tr>"""

    # Sem linhas na exportação não permite inferir o escopo de auditoria do polo.
    tem_labs = bool(lista_labs)
    if tem_labs:
        li_labs = f"<li>A situação dos laboratórios: {labs_txt}.</li>"
        secao_labs = f"""
      <!-- TÍTULO SEÇÃO: SITUAÇÃO DOS LABORATÓRIOS -->
      <tr><td style="padding:18px 22px 4px">
        <span style="font-size:15px;font-weight:bold;color:#E6007E;text-transform:uppercase;letter-spacing:1px">🔬 Situação dos Laboratórios</span>
        <table width="100%" cellpadding="0" cellspacing="0"><tr><td style="border-bottom:2px solid #E6007E;font-size:0;line-height:0">&nbsp;</td></tr></table>
      </td></tr>

      <!-- TABELA LABORATÓRIOS -->
      <tr><td style="padding:4px 18px 14px">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr style="background:#E6007E">
            <td style="padding:8px 12px"><span style="color:#fff;font-size:11px;font-weight:bold">LABORATÓRIO</span></td>
            <td style="padding:8px 12px;text-align:center"><span style="color:#fff;font-size:11px;font-weight:bold">PARECER</span></td>
            <td style="padding:8px 12px"><span style="color:#fff;font-size:11px;font-weight:bold">O QUE FALTA PARA APROVAR</span></td>
          </tr>
          {linhas_labs}
        </table>
      </td></tr>"""
    else:
        li_labs = ('<li>Laboratórios: não aplicável — confirmado manualmente.</li>'
                   if polo.get('labs_status') == 'nao_aplicavel' else
                   '<li>Sem registros na timeline; isso não comprova ausência de auditoria.</li>')
        secao_labs = ""

    barra_total = 'Não informado'
    if pct_total is not None:
        barra_total = f"""<table width="100%" cellpadding="0" cellspacing="0" style="background:#e8e8e8">
              <tr><td style="width:{max(1,pct_total):.0f}%;background:#4CAF50;padding:3px 0;text-align:center">
                <span style="font-size:10px;color:#fff;font-weight:bold">{pct_total:.0f}%</span>
              </td><td></td></tr>
            </table>"""

    li_praticas = '<li>As <b>Ações Padrão de Prática</b> (aulas) — situação detalhada na tabela abaixo.</li>'
    if polo.get('praticas_aplicaveis') is False:
        li_praticas = '<li>Práticas: não aplicável — confirmado manualmente.</li>'
        barra_total = 'Não aplicável'
    sem_contagem = 'Não aplicável' if polo.get('praticas_aplicaveis') is False else 'Não informado'
    linhas_seq = f"""
        <tr style="background:#f5f5f5">
          <td style="padding:10px 12px;text-align:center;font-weight:bold;font-size:14px">Total</td>
          <td style="padding:10px 12px;text-align:center;font-weight:bold;font-size:14px">{format(total_prev, ',') if total_prev is not None else sem_contagem}</td>
          <td style="padding:10px 12px;text-align:center;font-weight:bold;color:#4CAF50;font-size:14px">{format(total_comp, ',') if total_comp is not None else sem_contagem}</td>
          <td style="padding:10px 12px;text-align:center;font-weight:bold;color:#C62828;font-size:14px">{format(total_pend, ',') if total_pend is not None else sem_contagem}</td>
          <td style="padding:10px 12px">
            {barra_total}
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#ffffff;font-family:Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;padding:0">
<tr><td align="center">
<table width="680" cellpadding="0" cellspacing="0" style="background:#ffffff">

  <!-- HEADER (faixa cinza) -->
  <tr><td style="background:#ececec;padding:18px 28px">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="vertical-align:top;width:120px">&nbsp;</td>
      <td style="text-align:center;vertical-align:middle">
        <table cellpadding="0" cellspacing="0" style="margin:0 auto"><tr>
          <td style="width:78px;height:78px;background:#ffffff;border-radius:50%;text-align:center;vertical-align:middle;border:1px solid #e0e0e0">
            <span style="color:#F39200;font-size:24px;font-weight:bold;font-style:italic">RGC</span>
          </td>
          <td style="width:62px;height:62px;background:#F39200;border-radius:50%"></td>
          <td style="width:82px;height:82px;background:#E6007E;border-radius:50%;text-align:center;vertical-align:middle">
            <span style="color:#fff;font-size:34px">&#127891;</span>
          </td>
        </tr></table>
      </td>
      <td style="text-align:right;vertical-align:top;width:120px">
        <table cellpadding="0" cellspacing="0" align="right" style="background:#ffffff;border-radius:18px"><tr>
          <td style="padding:8px 18px">
            <span style="color:#4B3F8F;font-size:11px;font-weight:bold;letter-spacing:1px">DOCUMENTO OFICIAL</span>
          </td>
        </tr></table>
      </td>
    </tr></table>
  </td></tr>

  <!-- linha laranja -->
  <tr><td style="background:#F39200;height:4px;line-height:4px;font-size:0">&nbsp;</td></tr>

  <!-- AUDITORIA ACADÊMICA -->
  <tr><td style="padding:22px 32px 0;text-align:center">
    <span style="font-size:22px;font-weight:bold;color:#E6007E;text-transform:uppercase;letter-spacing:4px">Auditoria Acadêmica</span>
  </td></tr>

  <!-- TÍTULO + SUBTÍTULO -->
  <tr><td style="padding:14px 32px 0">
    <span style="font-size:28px;font-weight:bold;color:#222">{TITULO}</span>
    {f'<br/><span style="font-size:16px;color:#777;font-style:italic">{SUBTITULO}</span>' if SUBTITULO else ''}
    <table width="170" cellpadding="0" cellspacing="0"><tr><td style="border-bottom:3px solid #E6007E;font-size:0;line-height:0">&nbsp;</td></tr></table>
  </td></tr>

  <!-- CONTEÚDO (caixa tracejada) -->
  <tr><td style="padding:18px 32px 26px">
    <table width="100%" cellpadding="0" cellspacing="0" style="border:1px dashed #cccccc">

      <!-- POLO -->
      <tr><td style="padding:20px 22px 14px">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:#FFF6EC;border-left:4px solid #F39200">
          <tr><td style="padding:12px 16px">
            <span style="font-size:10px;color:#F39200;text-transform:uppercase;font-weight:bold;letter-spacing:1px">Polo</span><br/>
            <span style="font-size:16px;color:#333;font-weight:bold">{escape(polo['nome'])}</span>
          </td></tr>
        </table>
      </td></tr>

      <!-- MENSAGEM DE ABERTURA -->
      <tr><td style="padding:4px 22px 6px">
        <p style="font-size:14px;color:#333;line-height:1.6;margin:0 0 12px">
          Olá! Passando para alinhar um ponto bem importante sobre a qualidade do nosso Polo. 🤝
        </p>
        <p style="font-size:14px;color:#333;line-height:1.6;margin:0 0 12px">
          Precisamos avançar com a regularização da nossa <b>Auditoria Acadêmica</b>. Para garantir que a
          unidade opere em total conformidade e sem riscos de sanções judiciais ou administrativas,
          precisamos regularizar:
        </p>
        <ul style="font-size:14px;color:#333;line-height:1.6;margin:0 0 12px;padding-left:20px">
          {li_praticas}
          {li_labs}
        </ul>
        <p style="font-size:14px;color:#333;line-height:1.6;margin:0">
          Você pode acompanhar o andamento da regularização pelo relatório:<br/>
          <a href="https://prisma.kroton.com.br/relatorio/135" style="color:#E6007E;font-weight:bold">https://prisma.kroton.com.br/relatorio/135</a>
        </p>
      </td></tr>

      <!-- TÍTULO SEÇÃO: AÇÕES PADRÃO DE PRÁTICA -->
      <tr><td style="padding:6px 22px 4px">
        <span style="font-size:15px;font-weight:bold;color:#F39200;text-transform:uppercase;letter-spacing:1px">📋 Ações Padrão de Prática (Aulas)</span>
        <table width="100%" cellpadding="0" cellspacing="0"><tr><td style="border-bottom:2px solid #F39200;font-size:0;line-height:0">&nbsp;</td></tr></table>
      </td></tr>

      <!-- TABELA SEQUÊNCIAS -->
      <tr><td style="padding:8px 18px 14px">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr style="background:#F39200">
            <td style="padding:8px 12px;text-align:center"><span style="color:#fff;font-size:11px;font-weight:bold">ESCOPO</span></td>
            <td style="padding:8px 12px;text-align:center"><span style="color:#fff;font-size:11px;font-weight:bold">PREVISTAS</span></td>
            <td style="padding:8px 12px;text-align:center"><span style="color:#fff;font-size:11px;font-weight:bold">COMPROV.</span></td>
            <td style="padding:8px 12px;text-align:center"><span style="color:#fff;font-size:11px;font-weight:bold">PENDENTES</span></td>
            <td style="padding:8px 12px;text-align:center"><span style="color:#fff;font-size:11px;font-weight:bold">COMPROVAÇÃO</span></td>
          </tr>
          {linhas_seq}
        </table>
      </td></tr>

      {secao_labs}

      <!-- PRAZOS -->
      <tr><td style="padding:0 22px 18px">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:#FFF6EC;border-left:4px solid #C62828">
          <tr><td style="padding:14px 16px">
            <p style="font-size:14px;color:#333;font-weight:bold;margin:0 0 8px">⚠️ Anote os prazos na agenda:</p>
            <p style="font-size:14px;color:#333;line-height:1.6;margin:0">
              <b>{prazo_praticas}</b> – Limite para postagem das Ações Padrão de Prática.<br/>
              <b>{prazo_auditoria}</b> – Limite para regularizar as pendências da Auditoria Acadêmica.
            </p>
          </td></tr>
        </table>
      </td></tr>

      <!-- FECHAMENTO -->
      <tr><td style="padding:0 22px 20px">
        <p style="font-size:14px;color:#333;line-height:1.6;margin:0 0 12px">
          Contamos com o seu compromisso para resolvermos isso dentro do prazo, para evitar sanções
          previstas no seu contrato. Se tiver alguma dificuldade, nos avise o quanto antes para que
          possamos ajudar!
        </p>
        <p style="font-size:14px;color:#333;line-height:1.6;margin:0">
          Canal de Atendimento ao Polo:<br/>
          <a href="https://app.smartsheet.com/b/form/019c71b513a67973be44a973a3ee479a"
             style="color:#F39200;font-weight:bold">https://app.smartsheet.com/b/form/019c71b513a67973be44a973a3ee479a</a>
        </p>
      </td></tr>

    </table>
  </td></tr>

  <!-- FOOTER -->
  <tr><td style="background:#F39200;height:3px;line-height:3px;font-size:0">&nbsp;</td></tr>
  <tr><td style="padding:16px 32px 22px">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="vertical-align:middle">
        <span style="font-size:13px;font-weight:bold;color:#4B3F8F;letter-spacing:1px">{AREA_MACRO}<br/>{SUB_AREA}</span>
      </td>
      <td style="text-align:right;vertical-align:bottom">
        <span style="font-size:24px;font-weight:bold;color:#b5b5b5">cogna</span>
        <span style="font-size:9px;color:#c8c8c8;vertical-align:top">EDUCAÇÃO</span>
      </td>
    </tr></table>
  </td></tr>

  <tr><td style="padding:0 32px 14px">
    <span style="font-size:9px;color:#bbb">Público</span>
    <span style="font-size:9px;color:#bbb;font-style:italic">&nbsp;&nbsp;•&nbsp;&nbsp;Comunicado interno • Modelo institucional</span>
  </td></tr>

</table>
</td></tr></table>
</body></html>"""
