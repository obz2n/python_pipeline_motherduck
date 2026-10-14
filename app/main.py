"""Dashboard analítico de campanhas de anúncios — Streamlit.

Executar:  streamlit run app.py
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Dashboard de Anúncios", page_icon="📈", layout="wide")

DATA_PATH = Path(__file__).parent / "export.csv"  # plano B se o MotherDuck falhar
MD_DATABASE = "md:google_ads_db"
PALETTE = ["#2563EB", "#F59E0B", "#10B981", "#EF4444", "#8B5CF6", "#06B6D4"]
PRIMARY, ACCENT = PALETTE[0], PALETTE[1]

# Rótulos legíveis (os nomes originais têm erros de digitação)
CAMPAIGN_LABELS = {
    "cybersecurtyfundamentals": "Cybersecurity Fundamentals",
    "sqldatabsetraining": "SQL Database Training",
    "python4data": "Python 4 Data",
    "aimarketing": "AI Marketing",
    "machnelearningbasics": "Machine Learning Basics",
    "webdevmastery": "Web Dev Mastery",
    "deeplearnngpro": "Deep Learning Pro",
    "datasciencebootcamp": "Data Science Bootcamp",
    "businessanlyticsclass": "Business Analytics Class",
    "cloudcomputngcourse": "Cloud Computing Course",
}
KEYWORD_LABELS = {
    "data analitics online": "data analytics online",
    "online data analytic": "online data analytics",
    "data anaytics training": "data analytics training",
}


# ───────────────────────── Dados ─────────────────────────
def _secret(name: str, default: str = "") -> str:
    """Lê de st.secrets (se existir) ou de variável de ambiente."""
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.environ.get(name, default)


@st.cache_data(ttl=600, show_spinner="Consultando MotherDuck…")
def load_from_motherduck(database: str, table: str) -> tuple[pd.DataFrame, str]:
    import duckdb

    token = _secret("MOTHERDUCK_TOKEN") or _secret("motherduck_token")
    if token:
        os.environ["motherduck_token"] = token
    con = duckdb.connect(database)
    try:
        if not table:  # detecta automaticamente a tabela, só no banco conectado
            tables = con.execute(
                "SELECT table_schema, table_name FROM information_schema.tables "
                "WHERE table_catalog = current_database() "
                "AND table_schema NOT IN ('information_schema', 'pg_catalog') "
                "AND table_type = 'BASE TABLE' "
                "ORDER BY table_name ILIKE '%google_ads%' DESC, "
                "table_schema = 'main' DESC, table_name"
            ).fetchall()
            if not tables:
                raise RuntimeError(f"Nenhuma tabela encontrada em {database}.")
            schema, name = tables[0]
            table = f'"{schema}"."{name}"'
        df = con.execute(f"SELECT * FROM {table}").df()
    finally:
        con.close()
    return df, table


@st.cache_data
def load_from_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def prepare(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = df.copy()
    notes = {}
    # Aceita variações de nome de coluna (ex.: Conversion_Rate)
    df = df.rename(columns={"Conversion_Rate": "Conversion Rate"})
    df["Ad_Date"] = pd.to_datetime(df["Ad_Date"])
    for col in ["Clicks", "Impressions", "Cost", "Leads", "Conversions", "Conversion Rate", "Sale_Amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Datas: parte dos registros pode ter dia e mês invertidos (ex.: 2024-04-11 é
    # 11/04 lido como 04/11). A correção só é aplicada quando, após trocar, todas
    # as datas caem em um único mês — assim não altera bases com datas legítimas.
    d = df["Ad_Date"]
    mode_month = d.dt.month.mode().iloc[0]
    swapped = (d.dt.day == mode_month) & (d.dt.month != mode_month)
    fixed = pd.to_datetime(
        {
            "year": d.dt.year,
            "month": np.where(swapped, d.dt.day, d.dt.month),
            "day": np.where(swapped, d.dt.month, d.dt.day),
        }
    )
    if swapped.any() and fixed.dt.to_period("M").nunique() == 1:
        df["Date"] = fixed
        notes["dates_fixed"] = int(swapped.sum())
    else:
        df["Date"] = d
        notes["dates_fixed"] = 0

    df["Campaign"] = df["Campaign_Name"].map(CAMPAIGN_LABELS).fillna(df["Campaign_Name"])
    df["Keyword"] = df["Keyword"].replace(KEYWORD_LABELS)
    df["Location"] = df["Location"].replace({"New Delhi": "Delhi"})
    notes["missing"] = df[["Clicks", "Cost", "Conversion Rate", "Sale_Amount"]].isna().sum().to_dict()
    return df, notes


def ratio(df: pd.DataFrame, num: str, den: str) -> float:
    """Razão entre somas usando só linhas em que numerador e denominador existem."""
    m = df[num].notna() & df[den].notna()
    d = df.loc[m, den].sum()
    return df.loc[m, num].sum() / d if d else np.nan


def kpis(df: pd.DataFrame) -> dict:
    return {
        "impressions": df["Impressions"].sum(),
        "clicks": df["Clicks"].sum(),
        "cost": df["Cost"].sum(),
        "leads": df["Leads"].sum(),
        "conversions": df["Conversions"].sum(),
        "revenue": df["Sale_Amount"].sum(),
        "ctr": ratio(df, "Clicks", "Impressions"),
        "cpc": ratio(df, "Cost", "Clicks"),
        "cpl": ratio(df, "Cost", "Leads"),
        "cpa": ratio(df, "Cost", "Conversions"),
        "cvr": ratio(df, "Conversions", "Clicks"),
        "lead_conv": ratio(df, "Conversions", "Leads"),
        "roas": ratio(df, "Sale_Amount", "Cost"),
    }


def summarize(df: pd.DataFrame, by: str) -> pd.DataFrame:
    rows = []
    for key, g in df.groupby(by):
        k = kpis(g)
        k[by] = key
        k["ads"] = len(g)
        rows.append(k)
    return pd.DataFrame(rows).set_index(by)


# ───────────────────────── Formatação ─────────────────────────
def num(x, dec=0):
    return "–" if pd.isna(x) else f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, dec=1):
    return "–" if pd.isna(x) else num(x * 100, dec) + "%"


def style(fig, height=360):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=40, b=10),
        template="plotly_white",
        font=dict(size=13),
        legend=dict(orientation="h", y=-0.2),
    )
    return fig


# ───────────────────────── Sidebar ─────────────────────────
st.sidebar.header("Fonte de dados")
md_db = _secret("MOTHERDUCK_DATABASE", MD_DATABASE)
md_table = st.sidebar.text_input(
    "Tabela (vazio = detectar)", value=_secret("MOTHERDUCK_TABLE"),
    help="Ex.: ads ou main.ads. Também pode ser definida em MOTHERDUCK_TABLE.",
)
try:
    raw, used_table = load_from_motherduck(md_db, md_table.strip())
    st.sidebar.success(f"MotherDuck: {md_db} · {used_table}")
except Exception as e:
    raw = load_from_csv(DATA_PATH)
    st.sidebar.warning(f"MotherDuck indisponível, usando o CSV local.\n\n{type(e).__name__}: {str(e)[:200]}")
df_all, notes = prepare(raw)

st.sidebar.header("Filtros")
cur = st.sidebar.text_input("Símbolo da moeda", value="", help="Ex.: R$, $, ₹ (opcional)")
cur = (cur + " ") if cur else ""

dmin, dmax = df_all["Date"].min().date(), df_all["Date"].max().date()
date_range = st.sidebar.date_input("Período", (dmin, dmax), min_value=dmin, max_value=dmax)


def multi(label, col):
    opts = sorted(df_all[col].unique())
    return st.sidebar.multiselect(label, opts, default=opts)


sel_campaign = multi("Campanha", "Campaign")
sel_location = multi("Cidade", "Location")
sel_device = multi("Dispositivo", "Device")
sel_keyword = multi("Palavra-chave", "Keyword")

df = df_all[
    df_all["Campaign"].isin(sel_campaign)
    & df_all["Location"].isin(sel_location)
    & df_all["Device"].isin(sel_device)
    & df_all["Keyword"].isin(sel_keyword)
]
if isinstance(date_range, tuple) and len(date_range) == 2:
    df = df[(df["Date"].dt.date >= date_range[0]) & (df["Date"].dt.date <= date_range[1])]

with st.sidebar.expander("Qualidade dos dados"):
    st.markdown(
        f"- **{notes['dates_fixed']}** datas com dia/mês invertidos foram corrigidas\n"
        f"- Valores ausentes: Cost **{notes['missing']['Cost']}**, "
        f"Conversion Rate **{notes['missing']['Conversion Rate']}**, "
        f"Sale_Amount **{notes['missing']['Sale_Amount']}**, "
        f"Clicks **{notes['missing']['Clicks']}**\n"
        "- Nomes de campanhas/palavras-chave com erros de digitação foram padronizados\n"
        "- “New Delhi” foi unificada com “Delhi”\n"
        "- Razões (CTR, CPA, ROAS…) usam só linhas em que numerador e denominador existem\n"
        "- A taxa de conversão é recalculada (Conversões ÷ Cliques), pois a coluna original tem 21% de vazios"
    )

# ───────────────────────── Cabeçalho ─────────────────────────
st.title("📈 Dashboard de Campanhas de Anúncios")
if df.empty:
    st.warning("Nenhum registro para os filtros selecionados.")
    st.stop()
st.caption(f"{len(df)} anúncios · {df['Date'].min():%d/%m/%Y} a {df['Date'].max():%d/%m/%Y}")

K = kpis(df)
c = st.columns(6)
c[0].metric("Custo", cur + num(K["cost"]))
c[1].metric("Receita", cur + num(K["revenue"]))
c[2].metric("ROAS", num(K["roas"], 2) + "x", help="Receita ÷ Custo")
c[3].metric("Conversões", num(K["conversions"]))
c[4].metric("CPA", cur + num(K["cpa"], 2), help="Custo por conversão")
c[5].metric("CPL", cur + num(K["cpl"], 2), help="Custo por lead")
c = st.columns(6)
c[0].metric("Impressões", num(K["impressions"]))
c[1].metric("Cliques", num(K["clicks"]))
c[2].metric("CTR", pct(K["ctr"], 2), help="Cliques ÷ Impressões")
c[3].metric("CPC", cur + num(K["cpc"], 2))
c[4].metric("Leads", num(K["leads"]))
c[5].metric("Conv. / Clique", pct(K["cvr"], 2))

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Visão geral", "Campanhas", "Dispositivo e cidade", "Palavras-chave", "Dados"]
)

# ───────────────────────── Visão geral ─────────────────────────
with tab1:
    left, right = st.columns([3, 2])

    daily = df.groupby("Date").agg(Custo=("Cost", "sum"), Receita=("Sale_Amount", "sum"),
                                   Conversões=("Conversions", "sum")).reset_index()
    fig = go.Figure()
    fig.add_bar(x=daily["Date"], y=daily["Receita"], name="Receita", marker_color=PRIMARY)
    fig.add_scatter(x=daily["Date"], y=daily["Custo"], name="Custo", mode="lines+markers",
                    line=dict(color=ACCENT, width=3))
    fig.update_layout(title="Receita e custo por dia")
    left.plotly_chart(style(fig), width="stretch")

    funnel = go.Figure(go.Funnel(
        y=["Impressões", "Cliques", "Leads", "Conversões"],
        x=[K["impressions"], K["clicks"], K["leads"], K["conversions"]],
        textinfo="value+percent previous",
        marker=dict(color=[PALETTE[0], PALETTE[5], PALETTE[2], PALETTE[1]]),
    ))
    funnel.update_layout(title="Funil de conversão")
    right.plotly_chart(style(funnel), width="stretch")

    left, right = st.columns(2)
    wk = df.assign(Semana=df["Date"].dt.to_period("W").dt.start_time).groupby("Semana").apply(
        lambda g: pd.Series({"ROAS": ratio(g, "Sale_Amount", "Cost"), "CPA": ratio(g, "Cost", "Conversions")}),
        include_groups=False,
    ).reset_index()
    f = px.line(wk, x="Semana", y="ROAS", markers=True, title="ROAS semanal",
                color_discrete_sequence=[PRIMARY])
    left.plotly_chart(style(f, 320), width="stretch")
    f = px.line(wk, x="Semana", y="CPA", markers=True, title="CPA semanal",
                color_discrete_sequence=[ACCENT])
    right.plotly_chart(style(f, 320), width="stretch")

# ───────────────────────── Campanhas ─────────────────────────
with tab2:
    camp = summarize(df, "Campaign").reset_index()
    left, right = st.columns(2)
    f = px.bar(camp.sort_values("roas"), x="roas", y="Campaign", orientation="h",
               title="ROAS por campanha", color_discrete_sequence=[PRIMARY],
               labels={"roas": "ROAS", "Campaign": ""})
    left.plotly_chart(style(f, 420), width="stretch")
    f = px.bar(camp.sort_values("cpa", ascending=False), x="cpa", y="Campaign", orientation="h",
               title="CPA por campanha (menor é melhor)", color_discrete_sequence=[ACCENT],
               labels={"cpa": "CPA", "Campaign": ""})
    right.plotly_chart(style(f, 420), width="stretch")

    f = px.scatter(camp, x="cpa", y="cvr", size="cost", color="Campaign", text="Campaign",
                   title="Eficiência: CPA × conversão por clique (tamanho = custo)",
                   labels={"cpa": "CPA", "cvr": "Conversões por clique"},
                   color_discrete_sequence=px.colors.qualitative.Safe)
    f.update_traces(textposition="top center")
    f.update_layout(showlegend=False)
    f.update_yaxes(tickformat=".1%")
    st.plotly_chart(style(f, 440), width="stretch")

    show = camp.rename(columns={
        "ads": "Anúncios", "impressions": "Impressões", "clicks": "Cliques", "cost": "Custo",
        "leads": "Leads", "conversions": "Conversões", "revenue": "Receita", "ctr": "CTR",
        "cpc": "CPC", "cpl": "CPL", "cpa": "CPA", "cvr": "Conv./Clique", "roas": "ROAS",
    })[["Campaign", "Anúncios", "Impressões", "Cliques", "Custo", "Leads", "Conversões",
        "Receita", "CTR", "CPC", "CPL", "CPA", "Conv./Clique", "ROAS"]]
    show["CTR"] = show["CTR"] * 100
    show["Conv./Clique"] = show["Conv./Clique"] * 100
    st.dataframe(
        show.sort_values("ROAS", ascending=False),
        hide_index=True, width="stretch",
        column_config={
            "CTR": st.column_config.NumberColumn(format="%.2f%%"),
            "Conv./Clique": st.column_config.NumberColumn(format="%.2f%%"),
            "Custo": st.column_config.NumberColumn(format="%.0f"),
            "Receita": st.column_config.NumberColumn(format="%.0f"),
            "CPC": st.column_config.NumberColumn(format="%.2f"),
            "CPL": st.column_config.NumberColumn(format="%.2f"),
            "CPA": st.column_config.NumberColumn(format="%.2f"),
            "ROAS": st.column_config.NumberColumn(format="%.2f"),
        },
    )

# ───────────────────────── Dispositivo e cidade ─────────────────────────
with tab3:
    dev = summarize(df, "Device").reset_index()
    loc = summarize(df, "Location").reset_index()

    left, right = st.columns(2)
    f = px.pie(dev, names="Device", values="conversions", hole=0.55,
               title="Conversões por dispositivo", color_discrete_sequence=PALETTE)
    left.plotly_chart(style(f, 340), width="stretch")
    f = px.bar(dev, x="Device", y="roas", title="ROAS por dispositivo",
               color_discrete_sequence=[PRIMARY], labels={"roas": "ROAS", "Device": ""})
    right.plotly_chart(style(f, 340), width="stretch")

    left, right = st.columns(2)
    f = px.bar(loc.sort_values("conversions"), x="conversions", y="Location", orientation="h",
               title="Conversões por cidade", color_discrete_sequence=[PALETTE[2]],
               labels={"conversions": "Conversões", "Location": ""})
    left.plotly_chart(style(f, 340), width="stretch")
    f = px.bar(loc.sort_values("cpa", ascending=False), x="cpa", y="Location", orientation="h",
               title="CPA por cidade", color_discrete_sequence=[ACCENT],
               labels={"cpa": "CPA", "Location": ""})
    right.plotly_chart(style(f, 340), width="stretch")

    heat = df.groupby(["Location", "Device"]).apply(
        lambda g: ratio(g, "Sale_Amount", "Cost"), include_groups=False
    ).unstack()
    f = px.imshow(heat, text_auto=".2f", aspect="auto", color_continuous_scale="Blues",
                  title="ROAS: cidade × dispositivo", labels=dict(color="ROAS"))
    st.plotly_chart(style(f, 380), width="stretch")

# ───────────────────────── Palavras-chave ─────────────────────────
with tab4:
    kw = summarize(df, "Keyword").reset_index()
    left, right = st.columns(2)
    f = px.bar(kw.sort_values("conversions"), x="conversions", y="Keyword", orientation="h",
               title="Conversões por palavra-chave", color_discrete_sequence=[PRIMARY],
               labels={"conversions": "Conversões", "Keyword": ""})
    left.plotly_chart(style(f, 380), width="stretch")
    f = px.bar(kw.sort_values("roas"), x="roas", y="Keyword", orientation="h",
               title="ROAS por palavra-chave", color_discrete_sequence=[PALETTE[2]],
               labels={"roas": "ROAS", "Keyword": ""})
    right.plotly_chart(style(f, 380), width="stretch")

    f = px.scatter(kw, x="cpc", y="ctr", size="clicks", text="Keyword",
                   title="CPC × CTR (tamanho = cliques)",
                   labels={"cpc": "CPC", "ctr": "CTR"}, color_discrete_sequence=[PRIMARY])
    f.update_traces(textposition="top center")
    f.update_yaxes(tickformat=".1%")
    st.plotly_chart(style(f, 420), width="stretch")

# ───────────────────────── Dados ─────────────────────────
with tab5:
    cols = ["Ad_ID", "Date", "Campaign", "Location", "Device", "Keyword", "Impressions",
            "Clicks", "Cost", "Leads", "Conversions", "Sale_Amount"]
    st.dataframe(df[cols].sort_values("Date"), hide_index=True, width="stretch")
    st.download_button("⬇️ Baixar dados filtrados (CSV)",
                       df[cols].to_csv(index=False).encode("utf-8"),
                       "anuncios_filtrados.csv", "text/csv")