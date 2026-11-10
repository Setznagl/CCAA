"""
DISPARADOR DE EMAILS - AUDITORIA RGC (aulas práticas e laboratórios, por polo)

O que faz: monta e envia UM e-mail por polo com a situação da auditoria
acadêmica — aulas práticas previstas / comprovadas / pendentes em cada
sequência (1 a 4) e o % de aprovação dos laboratórios —, a partir das
exportações do Power BI "Auditoria Acadêmica EaD". Sem flag, só gera os
previews em HTML (nada é enviado).

Uso:
    python disparar_emails.py                       → Preview (salva HTMLs em ./previews/)
    python disparar_emails.py --mostrar             → Abre o email montado numa janela do Outlook (teste)
    python disparar_emails.py --rascunho            → Cria os emails na pasta Rascunhos do Outlook
    python disparar_emails.py --enviar              → Envia de verdade pelo Outlook
    python disparar_emails.py --enviar --smtp       → Envia via SMTP (Gmail / 365 com SMTP AUTH)
    python disparar_emails.py --polo "CAMPO MOURAO" → Filtra UM polo (combina com os modos acima)
    python disparar_emails.py --enviar --marcados   → Envia em lote só os polos elegíveis

Seleção em lote (--marcados): usa os polos elegíveis da Base Master, isto é,
CANAL = PARCEIRO e STATUS DA UNIDADE/POLO = UNIDADE EM OPERACAO/CAPTACAO.
Sem --marcados nem --polo, processa todos.

Envio padrão = Outlook desktop já logado (requer Outlook instalado + pywin32).
Use --smtp só se a TI tiver liberado SMTP AUTH.

Arquivos na mesma pasta:
    sequenciaa1.xlsx, sequenciaa2.xlsx, sequencia3.xlsx, sequencia4.xlsx
    labs.xlsx (uma linha por laboratório: Polo, Laboratório, Parecer Auditoria)
    emails.xlsx (colunas: Polo, Email, Enviar) — necessário para enviar/rascunhar
    Base de Polos - Master (1).xlsb:
        - aba principal: coluna U (GERENTE OPERACIONAL) = gerente de cada polo
        - aba CONTATOS_PARCEIROS: Nome / Cargo / E-mail (col E) dos gerentes

Cópia oculta (BCC): cada email vai oculto para o gerente operacional do polo. O nome vem
da col U da aba principal e o e-mail é buscado pelo nome na aba CONTATOS_PARCEIROS.
"""

import smtplib
import sys
import os
import re
import unicodedata
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Windows: console usa cp1252 e quebra com ═/emojis. Força UTF-8 na saída.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


# ══════════════════════════════════════════════
# CONFIGURAÇÕES
# ══════════════════════════════════════════════

# >>> Troque "SEU.EMAIL@cogna.com.br" pelo SEU e-mail antes de enviar. <<<
EMAIL_REMETENTE = "SEU.EMAIL@cogna.com.br"  # conta do Outlook usada no envio
NOME_REMETENTE = "Documentos Suporte e Controle"               # nome exibido dessa caixa
SENHA = "SUA_SENHA_AQUI"                                        # só com --smtp
SERVIDOR_SMTP = "smtp.office365.com"
PORTA_SMTP = 587

TITULO = "AGENDA_REGULARIZACAO_AUDITORIA_ACADEMICA"
SUBTITULO = ""

# E-mail dos auditores → entra em cópia (CC) em todos os disparos
EMAIL_AUDITORES = "auditoria.academica@kroton.com.br"
AREA_MACRO = "Regulação e Controle de Polos e Unidades"
SUB_AREA = "Aliança Jovens e Adultos"

# Gerente operacional → vai em cópia oculta (BCC)
ARQUIVO_MASTER = "Base de Polos - Master (1).xlsb"   # polo (col A) e gerente operacional (col U)
ABA_CONTATOS = "CONTATOS_PARCEIROS"                   # aba com Nome / Cargo / E-mail dos parceiros

# Gerentes operacionais que faltam na aba CONTATOS_PARCEIROS (nome → e-mail).
# Use só para gerentes operacionais ausentes da planilha; o ideal é cadastrá-los na aba.
EMAILS_GERENTES_EXTRA = {
    "JAQUELINE JANDIROBA": "jaqueline.jandiroba@cogna.com.br",
    "SIDNEI CASAGRANDE": "sidnei.casagrande@cogna.com.br",
    "ANDRE DUARTE": "andre.mduarte@cogna.com.br",
    # Constam na aba com outro cargo, mas são os gerentes operacionais (col U):
    "MARCOS SANTOS": "marcos.c.santos@cogna.com.br",
    "ALESSANDRA FRANCA": "alessandra.franca@cogna.com.br",
}

# Arquivos de sequência (ajuste os nomes conforme necessário)
ARQUIVOS_SEQ = {
    1: "sequenciaa1.xlsx",
    2: "sequenciaa2.xlsx",
    3: "sequencia3.xlsx",
    4: "sequencia4.xlsx",
}


# ══════════════════════════════════════════════
# LEITURA DOS DADOS
# ══════════════════════════════════════════════

def chave(polo):
    """Chave única da UNIDADE para match entre planilhas: o código numérico entre
    parênteses (ex.: 'BELEM/PA - III(3416206)U' → '3416206'). Sem código, cai no
    nome-base em maiúsculas (compatibilidade)."""
    cods = re.findall(r"\((\d+)\)", str(polo))
    if cods:
        return cods[-1]
    return str(polo).split(" - ")[0].strip().upper()


def ler_sequencias():
    """Lê as 4 planilhas e monta dicionário {polo: {seq: dados}}."""
    polos = {}

    for num, arquivo in ARQUIVOS_SEQ.items():
        if not os.path.exists(arquivo):
            print(f"  ⚠️  {arquivo} não encontrado, pulando seq {num}")
            continue

        df = pd.read_excel(arquivo)
        df = df[df["Polo"].notna() & ~df["Polo"].astype(str).str.contains("Filtros")]

        for _, row in df.iterrows():
            nome = str(row["Polo"]).strip()
            ch = chave(nome)

            if ch not in polos:
                polos[ch] = {"nome": nome, "sequencias": {}, "email": "",
                             "marcado": False, "bcc": "", "gerente": ""}

            polos[ch]["sequencias"][num] = {
                "previstas": int(row.get("Total de Aulas", 0) or 0),
                "comprovadas": int(row.get("Comprovadas", 0) or 0),
                "pendentes": int(row.get("Pendentes", 0) or 0),
            }

        print(f"  Seq {num}: {len(df)} polos ({arquivo})")

    return polos


def adicionar_labs(polos):
    """Lê labs.xlsx (uma linha por laboratório) e anexa a lista de labs de cada polo,
    com nome e parecer (Aprovado / Reprovado / Pendente)."""
    if not os.path.exists("labs.xlsx"):
        return

    df = pd.read_excel("labs.xlsx")
    cols = {str(c).strip().lower(): c for c in df.columns}

    def col(*chaves):
        for k in cols:
            if all(p in k for p in chaves):
                return cols[k]
        return None

    c_polo = col("polo")
    c_nome = col("laborat")        # nome do laboratório
    c_parecer = col("parecer")     # Parecer Auditoria

    if not c_polo or not c_nome:
        return

    n = 0
    for _, row in df.iterrows():
        ch = chave(str(row[c_polo]))
        if ch not in polos:
            continue
        nome = str(row[c_nome]).strip()
        if not nome or nome.lower() == "nan":
            continue
        parecer = str(row.get(c_parecer, "")).strip() if c_parecer else ""
        if parecer.lower() == "nan":
            parecer = ""
        polos[ch].setdefault("labs_lista", []).append({"nome": nome, "parecer": parecer})
        n += 1

    print(f"  Labs carregados: {n} laboratórios")


def adicionar_emails(polos):
    """Adiciona emails (e marcação de envio) do arquivo emails.xlsx.

    Colunas reconhecidas: Polo, Email, Enviar (opcional).
    Na coluna Enviar, valores como X / SIM / S / 1 / OK marcam o polo
    para disparo em lote. Em branco = não dispara.
    """
    if not os.path.exists("emails.xlsx"):
        return

    df = pd.read_excel("emails.xlsx")
    cols = {str(c).strip().lower(): str(c).strip() for c in df.columns}
    col_polo = next((cols[c] for c in cols if "polo" in c), None)
    col_email = next((cols[c] for c in cols if "email" in c), None)
    col_enviar = next((cols[c] for c in cols if "enviar" in c or "disparar" in c or "selecion" in c), None)

    if not col_polo or not col_email:
        return

    marcados = {"x", "sim", "s", "1", "ok", "true", "verdadeiro"}
    n_marcados = 0
    for _, row in df.iterrows():
        ch = chave(str(row[col_polo]))
        if ch in polos:
            polos[ch]["email"] = str(row[col_email]).strip()
            if col_enviar:
                val = str(row[col_enviar]).strip().lower()
                polos[ch]["marcado"] = val in marcados
                if polos[ch]["marcado"]:
                    n_marcados += 1

    if col_enviar:
        print(f"  Emails carregados ({n_marcados} marcados na coluna '{col_enviar}')")
    else:
        print(f"  Emails carregados (sem coluna de seleção)")


def _norm_nome(nome):
    """Normaliza nome para casar entre abas: sem acento, maiúsculo, espaços colapsados,
    e remove prefixos de 'a definir' (TBD/TDB - ...)."""
    n = unicodedata.normalize("NFKD", str(nome)).encode("ascii", "ignore").decode("ascii")
    n = " ".join(n.upper().split())
    for pref in ("TBD - ", "TDB - ", "TBD-", "TDB-", "TBD ", "TDB "):
        if n.startswith(pref):
            n = n[len(pref):].strip()
    return n


def _buscar_email(nome_norm, mapa_op):
    """Acha o e-mail do gerente OPERACIONAL (e só dele). Tenta match exato e, em seguida,
    nome contido (um prefixo do outro) para grafias parciais. Nunca usa outros cargos."""
    if nome_norm in mapa_op:
        return mapa_op[nome_norm]
    for cand, email in mapa_op.items():
        if cand.startswith(nome_norm) or nome_norm.startswith(cand):
            return email
    return ""


def adicionar_gerentes(polos):
    """Resolve o email de BCC (gerente operacional) de cada polo a partir da Base Master.

    - Aba principal: polo (col A) → nome do gerente operacional (col U).
    - Aba CONTATOS_PARCEIROS: nome → e-mail (col E) dos contatos de cargo Gerente Operacional.
    """
    if not os.path.exists(ARQUIVO_MASTER):
        print(f"  ⚠️  {ARQUIVO_MASTER} não encontrado — BCC do gerente desativado")
        return

    # polo (chave) → nome do gerente operacional (col U)
    df = pd.read_excel(ARQUIVO_MASTER, engine="pyxlsb")
    cols = {str(c).strip().lower(): c for c in df.columns}
    c_polo = next((cols[c] for c in cols if "nome unidade sistema" in c), df.columns[0])
    c_ger = next((cols[c] for c in cols if "gerente operacional" in c), None)
    c_email = next((cols[c] for c in cols if "email" in c and "gestor prisma" in c), None)
    c_canal = next((cols[c] for c in cols if c.strip() == "canal"), None)
    c_status = next((cols[c] for c in cols if "status da unidade" in c), None)
    if not c_ger:
        print("  ⚠️  Coluna 'GERENTE OPERACIONAL' não encontrada na Master — BCC desativado")
        return

    nome_por_polo = {}
    email_destino = {}  # polo → e-mail do gestor Prisma / diretor de unidade (destinatário)
    elegivel = {}       # polo → True se CANAL=PARCEIRO e STATUS=UNIDADE EM OPERACAO/CAPTACAO
    for _, row in df.iterrows():
        ch = chave(str(row[c_polo]))
        nome = str(row[c_ger]).strip()
        if ch and nome and nome.lower() != "nan" and ch not in nome_por_polo:
            nome_por_polo[ch] = nome
        if c_email and ch and ch not in email_destino:
            em = str(row[c_email]).strip()
            if "@" in em:
                email_destino[ch] = em
        if ch and ch not in elegivel:
            canal = str(row[c_canal]).strip().upper() if c_canal else ""
            status = str(row[c_status]).strip().upper() if c_status else ""
            elegivel[ch] = (canal == "PARCEIRO" and "OPERACAO/CAPTACAO" in status)

    # nome (normalizado) → e-mail, da aba CONTATOS_PARCEIROS
    # Layout: linhas iniciais vazias; cabeçalho com Nome(B) / Cargo(C) / E-mail(E).
    dc = pd.read_excel(ARQUIVO_MASTER, engine="pyxlsb", sheet_name=ABA_CONTATOS, header=None)
    mapa_op = {}   # SOMENTE gerentes operacionais
    for _, r in dc.iterrows():
        nome, cargo, email = r.get(1), r.get(2), r.get(4)
        nome, email = str(nome).strip(), str(email).strip()
        if not nome or nome.lower() == "nan" or "@" not in email:
            continue
        if "operacional" in str(cargo).lower():
            mapa_op[_norm_nome(nome)] = email

    # Complemento manual (gerentes operacionais ausentes da aba de contatos)
    for nome, email in EMAILS_GERENTES_EXTRA.items():
        mapa_op.setdefault(_norm_nome(nome), email)

    # Aplica BCC (gerente operacional) e destinatário (gestor Prisma) em cada polo
    n_bcc = 0
    n_dest = 0
    sem_match = set()
    for ch in polos:
        nome = nome_por_polo.get(ch, "")
        email = _buscar_email(_norm_nome(nome), mapa_op) if nome else ""
        polos[ch]["gerente"] = nome
        polos[ch]["bcc"] = email
        if email:
            n_bcc += 1
        elif nome:
            sem_match.add(nome)

        dest = email_destino.get(ch, "")
        if dest:
            polos[ch]["email"] = dest  # destinatário = gestor Prisma / diretor de unidade
            n_dest += 1

        # Seleção de envio: PARCEIRO + UNIDADE EM OPERACAO/CAPTACAO (sobrepõe a coluna Enviar)
        polos[ch]["marcado"] = bool(elegivel.get(ch, False))

    n_marc = sum(1 for v in polos.values() if v.get("marcado"))
    print(f"  Gerentes: {len(mapa_op)} contatos operacionais, BCC em {n_bcc} polo(s)")
    print(f"  Destinatários (gestor Prisma) da Master: {n_dest} polo(s)")
    print(f"  Elegíveis p/ envio (PARCEIRO + OPERAÇÃO/CAPTAÇÃO): {n_marc} polo(s)")
    if sem_match:
        print(f"  ⚠️  Sem e-mail na aba {ABA_CONTATOS} para: {', '.join(sorted(sem_match))}")


# ══════════════════════════════════════════════
# TEMPLATE HTML
# ══════════════════════════════════════════════

def gerar_html(polo):
    # Calcula totais
    total_prev = sum(s["previstas"] for s in polo["sequencias"].values())
    total_comp = sum(s["comprovadas"] for s in polo["sequencias"].values())
    total_pend = sum(s["pendentes"] for s in polo["sequencias"].values())
    pct_total = (total_comp / total_prev * 100) if total_prev > 0 else 0

    # Detalhamento dos laboratórios — lista nomeada vinda de labs.xlsx
    lista_labs = polo.get("labs_lista") or []
    lab_total = len(lista_labs)

    # Cor / rótulo / "o que falta" por parecer da auditoria
    def info_parecer(parecer):
        p = parecer.strip().lower()
        if p.startswith("aprov"):
            return "#4CAF50", "Aprovado", "Regularizado — nenhuma ação necessária."
        if p.startswith("reprov"):
            return "#C62828", "Reprovado", "Verificar e regularizar as pendências apontadas na auditoria."
        if p.startswith("pend"):
            return "#E6A817", "Pendente", "Agendar e realizar a auditoria do laboratório."
        return "#757575", "Sem parecer", "Aguardando definição da auditoria."

    lab_aprov = sum(1 for l in lista_labs if l["parecer"].lower().startswith("aprov"))
    lab_repr = sum(1 for l in lista_labs if l["parecer"].lower().startswith("reprov"))
    lab_pend = lab_total - lab_aprov - lab_repr
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
    else:
        labs_txt = "Sem laboratórios registrados para esta unidade."

    # Tabela com cada laboratório, parecer e o que falta para aprovar
    linhas_labs = ""
    for l in sorted(lista_labs, key=lambda x: x["nome"]):
        cor, rotulo, falta = info_parecer(l["parecer"])
        linhas_labs += f"""
        <tr>
          <td style="padding:9px 12px;border-bottom:1px solid #f0f0f0;font-size:13px;color:#333">{l['nome']}</td>
          <td style="padding:9px 12px;border-bottom:1px solid #f0f0f0;text-align:center;white-space:nowrap">
            <span style="background:{cor};color:#fff;font-size:11px;font-weight:bold;padding:3px 10px;border-radius:3px">{rotulo}</span>
          </td>
          <td style="padding:9px 12px;border-bottom:1px solid #f0f0f0;font-size:12px;color:#555">{falta}</td>
        </tr>"""

    # Seção de laboratórios (cabeçalho + tabela) — só aparece se a unidade tem labs.
    # Unidades vindas só das Ações Padrão de Prática (fora do escopo da auditoria de
    # labs) não têm laboratório e a seção é omitida.
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
        li_labs = ""
        secao_labs = ""

    # Linhas da tabela por sequência
    linhas_seq = ""
    for num in sorted(polo["sequencias"]):
        s = polo["sequencias"][num]
        pct_s = (s["comprovadas"] / s["previstas"] * 100) if s["previstas"] > 0 else 0
        cor_barra = "#4CAF50" if pct_s >= 90 else "#E6A817" if pct_s >= 70 else "#C62828"

        linhas_seq += f"""
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0;text-align:center;font-weight:bold;color:#E8870E;font-size:16px">{num}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0;text-align:center;font-size:14px">{s['previstas']:,}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0;text-align:center;font-size:14px;color:#4CAF50;font-weight:bold">{s['comprovadas']:,}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0;text-align:center;font-size:14px;color:#C62828;font-weight:bold">{s['pendentes']:,}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #f0f0f0;width:30%">
            <table width="100%" cellpadding="0" cellspacing="0" style="background:#e8e8e8">
              <tr><td style="width:{max(1,pct_s):.0f}%;background:{cor_barra};padding:3px 0;text-align:center">
                <span style="font-size:10px;color:#fff;font-weight:bold">{pct_s:.0f}%</span>
              </td><td></td></tr>
            </table>
          </td>
        </tr>"""

    # Linha de total
    linhas_seq += f"""
        <tr style="background:#f5f5f5">
          <td style="padding:10px 12px;text-align:center;font-weight:bold;font-size:14px">Total</td>
          <td style="padding:10px 12px;text-align:center;font-weight:bold;font-size:14px">{total_prev:,}</td>
          <td style="padding:10px 12px;text-align:center;font-weight:bold;color:#4CAF50;font-size:14px">{total_comp:,}</td>
          <td style="padding:10px 12px;text-align:center;font-weight:bold;color:#C62828;font-size:14px">{total_pend:,}</td>
          <td style="padding:10px 12px">
            <table width="100%" cellpadding="0" cellspacing="0" style="background:#e8e8e8">
              <tr><td style="width:{max(1,pct_total):.0f}%;background:#4CAF50;padding:3px 0;text-align:center">
                <span style="font-size:10px;color:#fff;font-weight:bold">{pct_total:.0f}%</span>
              </td><td></td></tr>
            </table>
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
            <span style="font-size:16px;color:#333;font-weight:bold">{polo['nome']}</span>
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
          <li>As <b>Ações Padrão de Prática</b> (aulas) — situação detalhada na tabela abaixo.</li>
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
            <td style="padding:8px 12px;text-align:center"><span style="color:#fff;font-size:11px;font-weight:bold">SEQ</span></td>
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
              <b>31/05/2026</b> – Limite para postagem das Ações Padrão de Prática.<br/>
              <b>26/06/2026</b> – Limite para regularizar as pendências da Auditoria Acadêmica.
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


# ══════════════════════════════════════════════
# ENVIO
# ══════════════════════════════════════════════

def enviar_email_smtp(destinatario, assunto, html, bcc="", cc=""):
    """Envia via SMTP (Gmail, ou 365 com SMTP AUTH liberado pela TI)."""
    msg = MIMEMultipart("alternative")
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = destinatario
    if cc:
        msg["Cc"] = cc  # CC aparece no cabeçalho (visível)
    msg["Subject"] = assunto
    msg.attach(MIMEText(html, "html", "utf-8"))

    # To + Cc (visíveis) + Bcc (oculto) entram todos na lista de entrega
    destinatarios = [destinatario] + ([cc] if cc else []) + ([bcc] if bcc else [])

    with smtplib.SMTP(SERVIDOR_SMTP, PORTA_SMTP) as srv:
        srv.starttls()
        srv.login(EMAIL_REMETENTE, SENHA)
        srv.sendmail(EMAIL_REMETENTE, destinatarios, msg.as_string())


# Cache da instância do Outlook (criar uma vez só)
_outlook = None


def _get_outlook():
    global _outlook
    if _outlook is None:
        import win32com.client
        _outlook = win32com.client.Dispatch("Outlook.Application")
    return _outlook


def _conta_remetente(app):
    """Retorna a conta do Outlook cujo endereço bate com EMAIL_REMETENTE (ou None)."""
    try:
        for conta in app.Session.Accounts:
            if str(conta.SmtpAddress).strip().lower() == EMAIL_REMETENTE.strip().lower():
                return conta
    except Exception:
        pass
    return None


def _drafts_da_conta(app, conta):
    """Pasta Rascunhos (olFolderDrafts=16) do store da conta — sincroniza com o servidor,
    então o rascunho aparece também no 'novo Outlook'. Cai para os Rascunhos padrão se falhar."""
    try:
        if conta is not None:
            return conta.DeliveryStore.GetDefaultFolder(16)
    except Exception:
        pass
    return app.Session.GetDefaultFolder(16)


def enviar_email_outlook(destinatario, assunto, html, modo="enviar", bcc="", cc=""):
    """Usa o Outlook clássico já logado. Sem senha/SMTP.

    modo="enviar"   → envia de verdade
    modo="rascunho" → salva nos Rascunhos da conta remetente (sincroniza com o servidor)
    modo="mostrar"  → abre o email numa janela na tela (não envia nem salva)
    """
    app = _get_outlook()
    conta = _conta_remetente(app)
    mail = app.CreateItem(0)  # 0 = olMailItem
    if conta is not None:
        mail.SendUsingAccount = conta  # conta com login próprio
    else:
        # Caixa compartilhada (sem conta própria no perfil): define o remetente
        # representado via PR_SENT_REPRESENTING_* — resolve no GAL e fixa no envio
        # (Send As / Send on Behalf, conforme a permissão concedida à conta logada).
        pa = mail.PropertyAccessor
        pa.SetProperty("http://schemas.microsoft.com/mapi/proptag/0x0042001F", NOME_REMETENTE)
        pa.SetProperty("http://schemas.microsoft.com/mapi/proptag/0x0065001F", EMAIL_REMETENTE)
        pa.SetProperty("http://schemas.microsoft.com/mapi/proptag/0x0064001F", "SMTP")
    mail.To = destinatario
    if cc:
        mail.CC = cc
    if bcc:
        mail.BCC = bcc
    mail.Subject = assunto
    mail.HTMLBody = html
    if modo == "mostrar":
        mail.Display(False)  # abre a janela do email na tela
    elif modo == "rascunho":
        # Move para os Rascunhos da conta (server-side) p/ aparecer no novo Outlook
        mail.Save()
        try:
            mail.Move(_drafts_da_conta(app, conta))
        except Exception:
            pass  # já está salvo nos Rascunhos padrão
    else:
        mail.Send()


# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════

if __name__ == "__main__":
    modo_envio = "--enviar" in sys.argv
    modo_rascunho = "--rascunho" in sys.argv
    modo_mostrar = "--mostrar" in sys.argv
    usar_smtp = "--smtp" in sys.argv
    so_marcados = "--marcados" in sys.argv  # só os polos com X na coluna Enviar
    ativo = modo_envio or modo_rascunho or modo_mostrar  # age em vez de só preview
    if ativo and "SEU.EMAIL" in EMAIL_REMETENTE.upper():
        print("\n[ERRO] Troque SEU.EMAIL@cogna.com.br pelo seu e-mail em EMAIL_REMETENTE, "
              "no topo do arquivo.")
        sys.exit(1)

    # Pega filtro de polo (se houver)
    filtro = None
    for i, a in enumerate(sys.argv):
        if a == "--polo" and i + 1 < len(sys.argv):
            filtro = sys.argv[i + 1].upper()

    print("═" * 50)
    print("  DISPARADOR DE EMAILS — AUDITORIA RGC")
    print("═" * 50)

    # Carrega dados
    print("\nCarregando...")
    polos = ler_sequencias()
    adicionar_labs(polos)
    adicionar_emails(polos)
    adicionar_gerentes(polos)
    print(f"\nTotal: {len(polos)} polos")

    # Filtra se necessário (pelo nome do polo ou pelo código)
    if filtro:
        polos = {k: v for k, v in polos.items()
                 if filtro in v["nome"].upper() or filtro in k}
        print(f"Filtro '{filtro}': {len(polos)} polo(s)")

    # Seleção em lote pela coluna Enviar do emails.xlsx
    if so_marcados:
        polos = {k: v for k, v in polos.items() if v.get("marcado")}
        print(f"Apenas elegíveis (PARCEIRO + OPERAÇÃO/CAPTAÇÃO): {len(polos)} polo(s)")

    # Processa
    os.makedirs("previews", exist_ok=True)
    enviados = 0

    sem_email = 0
    for ch, polo in sorted(polos.items()):
        assunto = f"[RGC] {TITULO} — {polo['nome']}"
        html = gerar_html(polo)

        if ativo:
            if not polo["email"]:
                sem_email += 1
                continue
            bcc = polo.get("bcc", "")
            cc = EMAIL_AUDITORES
            try:
                if usar_smtp:
                    enviar_email_smtp(polo["email"], assunto, html, bcc=bcc, cc=cc)
                else:
                    modo = "mostrar" if modo_mostrar else "rascunho" if modo_rascunho else "enviar"
                    enviar_email_outlook(polo["email"], assunto, html, modo=modo, bcc=bcc, cc=cc)
                bcc_info = f" (BCC: {bcc})" if bcc else " (sem gerente)"
                print(f"  ✅ {polo['nome']} → {polo['email']} (CC: {cc}){bcc_info}")
                enviados += 1
            except Exception as e:
                print(f"  ❌ {polo['nome']}: {e}")
        else:
            nome_arq = polo["nome"].replace("/", "_").replace(" ", "_")[:40]
            with open(f"previews/{nome_arq}.html", "w", encoding="utf-8") as f:
                f.write(html)
            enviados += 1

    if ativo:
        verbo = "Abertos na tela" if modo_mostrar else "Rascunhos criados" if modo_rascunho else "Enviados"
        print(f"\n{verbo}: {enviados}")
        if sem_email:
            print(f"Pulados (sem email em emails.xlsx): {sem_email}")
    else:
        print(f"\nPreviews: {enviados}")
        print("Abra os HTMLs em ./previews/ para conferir")
        print("Próximo passo seguro → python disparar_emails.py --rascunho --polo \"CAMPO MOURAO\"")