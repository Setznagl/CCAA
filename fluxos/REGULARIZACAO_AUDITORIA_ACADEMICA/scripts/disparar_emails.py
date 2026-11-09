"""
DISPARADOR DE EMAILS - AUDITORIA RGC — VERSÃO ANTIGA (só SMTP)

Primeira versão do disparo por polo (aulas por sequência + aprovação dos
laboratórios). A versão em uso é ../disparar_emails.py, que envia pelo Outlook;
esta fica só como referência.

Uso:
    python disparar_emails.py                       → Preview (salva HTMLs)
    python disparar_emails.py --enviar              → Envia emails
    python disparar_emails.py --polo "CAMPO MOURAO" → Filtra um polo

Arquivos na mesma pasta:
    sequencia1.xlsx até sequencia4.xlsx
    aprovacao.xlsx
    emails.xlsx (opcional - colunas: Polo, Email)
"""

import smtplib
import sys
import os
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


# ══════════════════════════════════════════════
# CONFIGURAÇÕES
# ══════════════════════════════════════════════

EMAIL_REMETENTE = "auditoria.rgc@cogna.com.br"
SENHA = "SUA_SENHA_DE_APP_AQUI"
SERVIDOR_SMTP = "smtp.gmail.com"
PORTA_SMTP = 587

TITULO = "Resultado da Auditoria de Infraestrutura"
SUBTITULO = "Relatório de Comprovação de Aulas — Semestre 2026.1"
AREA_MACRO = "Regulação e Controle de Polos e Unidades"
SUB_AREA = "Aliança Jovens e Adultos"

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
    """Extrai nome-base do polo para fazer match entre planilhas."""
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
                polos[ch] = {"nome": nome, "sequencias": {}, "email": "", "aprovacao": -1}

            polos[ch]["sequencias"][num] = {
                "previstas": int(row.get("Total de Aulas", 0) or 0),
                "comprovadas": int(row.get("Comprovadas", 0) or 0),
                "pendentes": int(row.get("Pendentes", 0) or 0),
            }

        print(f"  Seq {num}: {len(df)} polos ({arquivo})")

    return polos


def adicionar_aprovacao(polos):
    """Adiciona % aprovação do arquivo aprovacao.xlsx."""
    if not os.path.exists("aprovacao.xlsx"):
        return

    df = pd.read_excel("aprovacao.xlsx")
    df = df[df["Polo"].notna() & ~df["Polo"].astype(str).str.contains("Filtros|Total")]

    for _, row in df.iterrows():
        ch = chave(row["Polo"])
        if ch in polos:
            polos[ch]["aprovacao"] = float(row.get("% Aprovação", 0) or 0)

    print(f"  Aprovação carregada: {len(df)} registros")


def adicionar_emails(polos):
    """Adiciona emails do arquivo emails.xlsx."""
    if not os.path.exists("emails.xlsx"):
        return

    df = pd.read_excel("emails.xlsx")
    cols = {str(c).strip().lower(): str(c).strip() for c in df.columns}
    col_polo = next((cols[c] for c in cols if "polo" in c), None)
    col_email = next((cols[c] for c in cols if "email" in c), None)

    if not col_polo or not col_email:
        return

    for _, row in df.iterrows():
        ch = chave(str(row[col_polo]))
        if ch in polos:
            polos[ch]["email"] = str(row[col_email]).strip()

    print(f"  Emails carregados")


# ══════════════════════════════════════════════
# TEMPLATE HTML
# ══════════════════════════════════════════════

def gerar_html(polo):
    # Calcula totais
    total_prev = sum(s["previstas"] for s in polo["sequencias"].values())
    total_comp = sum(s["comprovadas"] for s in polo["sequencias"].values())
    total_pend = sum(s["pendentes"] for s in polo["sequencias"].values())
    pct_total = (total_comp / total_prev * 100) if total_prev > 0 else 0

    # Badge de aprovação
    pct = polo["aprovacao"]
    if pct < 0:
        cor_badge, status, pct_txt = "#757575", "SEM DADOS", "N/A"
    elif pct >= 0.75:
        cor_badge, status, pct_txt = "#4CAF50", "APROVADO", f"{pct*100:.1f}%"
    elif pct >= 0.50:
        cor_badge, status, pct_txt = "#E6A817", "ATENÇÃO", f"{pct*100:.1f}%"
    else:
        cor_badge, status, pct_txt = "#C62828", "CRÍTICO", f"{pct*100:.1f}%"

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

    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0f0f0;font-family:Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f0f0;padding:20px 0">
<tr><td align="center">
<table width="660" cellpadding="0" cellspacing="0" style="background:#fff;border-right:4px solid #E8870E">

  <!-- HEADER -->
  <tr><td style="padding:24px 32px 0">
    <table width="100%"><tr>
      <td>
        <table cellpadding="0" cellspacing="0"><tr>
          <td style="width:70px;height:70px;background:#E8870E;border-radius:50%;text-align:center;vertical-align:middle">
            <span style="color:#fff;font-size:22px;font-weight:bold">RGC</span>
          </td>
          <td style="width:8px"></td>
          <td style="width:70px;height:70px;background:#4CAF50;border-radius:50%;text-align:center;vertical-align:middle">
            <span style="color:#fff;font-size:28px">&#9960;</span>
          </td>
        </tr></table>
      </td>
      <td style="text-align:right;vertical-align:top">
        <td style="border:2px solid #E8870E;padding:6px 16px">
          <span style="color:#E8870E;font-size:11px;font-weight:bold;text-transform:uppercase">Documento Oficial</span>
        </td>
      </td>
    </tr></table>
  </td></tr>

  <tr><td style="padding:18px 32px 0">
    <span style="font-size:20px;font-weight:bold;color:#4CAF50;text-transform:uppercase;letter-spacing:3px">Auditoria de Infraestrutura</span>
  </td></tr>

  <tr><td style="padding:10px 32px 0">
    <span style="font-size:26px;font-weight:bold;color:#333">{TITULO}</span><br/>
    <span style="font-size:15px;color:#888;font-style:italic">{SUBTITULO}</span>
    <table width="200"><tr><td style="border-bottom:3px solid #E8870E">&nbsp;</td></tr></table>
  </td></tr>

  <!-- CONTEÚDO -->
  <tr><td style="padding:20px 32px">
    <table width="100%" style="border:1px solid #e0e0e0">

      <!-- POLO -->
      <tr><td style="padding:20px 24px 16px">
        <table width="100%" style="background:#FFF8F0;border-left:4px solid #E8870E">
          <tr><td style="padding:12px 16px">
            <span style="font-size:10px;color:#E8870E;text-transform:uppercase;font-weight:bold">Polo</span><br/>
            <span style="font-size:16px;color:#333;font-weight:bold">{polo['nome']}</span>
          </td></tr>
        </table>
      </td></tr>

      <!-- TABELA SEQUÊNCIAS -->
      <tr><td style="padding:0 18px 12px">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr style="background:#E8870E">
            <td style="padding:8px 12px;text-align:center"><span style="color:#fff;font-size:11px;font-weight:bold">SEQ</span></td>
            <td style="padding:8px 12px;text-align:center"><span style="color:#fff;font-size:11px;font-weight:bold">PREVISTAS</span></td>
            <td style="padding:8px 12px;text-align:center"><span style="color:#fff;font-size:11px;font-weight:bold">COMPROV.</span></td>
            <td style="padding:8px 12px;text-align:center"><span style="color:#fff;font-size:11px;font-weight:bold">PENDENTES</span></td>
            <td style="padding:8px 12px;text-align:center"><span style="color:#fff;font-size:11px;font-weight:bold">COMPROVAÇÃO</span></td>
          </tr>
          {linhas_seq}
        </table>
      </td></tr>

      <!-- BADGE -->
      <tr><td style="padding:12px 24px 20px;text-align:center">
        <table style="margin:0 auto"><tr>
          <td style="background:{cor_badge};padding:8px 24px">
            <span style="color:#fff;font-size:12px;font-weight:bold">{status} — Aprovação Labs: {pct_txt}</span>
          </td>
        </tr></table>
      </td></tr>

      <!-- TEXTO -->
      <tr><td style="padding:0 24px 20px">
        <table width="100%" style="border-top:1px solid #eee">
          <tr><td style="padding:16px 0 0;font-size:12px;color:#666;line-height:1.6">
            Comunicação gerada automaticamente pela área de <strong>{AREA_MACRO}</strong>.
            Em caso de dúvidas, entre em contato com a equipe de <strong>{SUB_AREA}</strong>.
          </td></tr>
        </table>
      </td></tr>

    </table>
  </td></tr>

  <!-- FOOTER -->
  <tr><td style="background:#4a4a4a;padding:18px 32px">
    <table width="100%"><tr>
      <td><span style="font-size:12px;font-weight:bold;color:#E8870E">{AREA_MACRO}<br/>{SUB_AREA}</span></td>
      <td style="text-align:right"><span style="font-size:22px;font-weight:bold;color:#E8870E">cogna</span>
        <span style="font-size:9px;color:#bbb;vertical-align:top">EDUCAÇÃO</span></td>
    </tr></table>
  </td></tr>

  <tr><td style="padding:8px 32px"><span style="font-size:9px;color:#bbb">Comunicado interno • Gerado em {agora}</span></td></tr>

</table>
</td></tr></table>
</body></html>"""


# ══════════════════════════════════════════════
# ENVIO
# ══════════════════════════════════════════════

def enviar_email(destinatario, assunto, html):
    msg = MIMEMultipart("alternative")
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = destinatario
    msg["Subject"] = assunto
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(SERVIDOR_SMTP, PORTA_SMTP) as srv:
        srv.starttls()
        srv.login(EMAIL_REMETENTE, SENHA)
        srv.sendmail(EMAIL_REMETENTE, destinatario, msg.as_string())


# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════

if __name__ == "__main__":
    modo_envio = "--enviar" in sys.argv

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
    adicionar_aprovacao(polos)
    adicionar_emails(polos)
    print(f"\nTotal: {len(polos)} polos")

    # Filtra se necessário
    if filtro:
        polos = {k: v for k, v in polos.items() if filtro in k}
        print(f"Filtro '{filtro}': {len(polos)} polo(s)")

    # Processa
    os.makedirs("previews", exist_ok=True)
    enviados = 0

    for ch, polo in sorted(polos.items()):
        assunto = f"[RGC] {TITULO} — {polo['nome']}"
        html = gerar_html(polo)

        if modo_envio:
            if not polo["email"]:
                continue
            try:
                enviar_email(polo["email"], assunto, html)
                print(f"  ✅ {polo['nome']}")
                enviados += 1
            except Exception as e:
                print(f"  ❌ {polo['nome']}: {e}")
        else:
            nome_arq = polo["nome"].replace("/", "_").replace(" ", "_")[:40]
            with open(f"previews/{nome_arq}.html", "w", encoding="utf-8") as f:
                f.write(html)
            enviados += 1

    print(f"\n{'Enviados' if modo_envio else 'Previews'}: {enviados}")
    if not modo_envio:
        print("Abra os HTMLs em ./previews/ para conferir")
        print("Quando OK → python disparar_emails.py --enviar")
