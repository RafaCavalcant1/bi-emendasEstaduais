# -- coding: utf-8 --
"""
BI - Emendas (Streamlit)
- Filtros encadeados (1º → 4º) com opção (Todos)
- Indicadores
- Abas: Visão Geral, Por Parlamentar, Temporal, Mapa de Calor, Execução
- Seletor de tipo de gráfico para cada aba
- Exportação do recorte filtrado (CSV)
- Visão Geral também mostra Por Parlamentar, Temporal, Mapa de Calor e Execução (subseções abertas)
- FIX: keys únicos em todos os st.plotly_chart (evita StreamlitDuplicateElementId)
"""

import unicodedata
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ==========================
# CONFIGURAÇÃO GERAL
# ==========================
st.set_page_config(page_title="BI - Emendas", page_icon="📊", layout="wide")

# Carregar CSS personalizado
with open("style.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

SHEET_ID = "1fyzyrSsRuUm8d6jNSeaTIVm8Zps2jLAO5u_xxUF5ox0"
GID = "1186502103"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&gid={GID}"

CONFIG_MODEBAR = {
    "displaylogo": False,
    "modeBarButtonsToRemove": [
        "pan2d", "select2d", "lasso2d",
        "zoomIn2d", "zoomOut2d", "autoScale2d",
        "hoverClosestCartesian", "hoverCompareCartesian",
        "toggleSpikelines", "zoom2d", "resetScale2d"
    ],
    "modeBarButtonsToAdd": ["toImage"]
}

# ==========================
# HELPERS
# ==========================
def normalizar_txt(s: str) -> str:
    """Remove acentos e padroniza minúsculas para mapeamentos de texto."""
    s = str(s).strip().lower()
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("utf-8")

@st.cache_data(ttl=300)
def carregar_dados(url: str) -> pd.DataFrame:
    """Carrega CSV do Google Sheets e limpa cabeçalhos."""
    df = pd.read_csv(url)
    df.columns = [c.strip() for c in df.columns]
    return df

def agrega_por_dimensao(df_base: pd.DataFrame, dim: str, how: str) -> pd.DataFrame:
    """
    Agrega valores por dimensão.
    how: "Contagem" ou "Soma de VALOR"
    """
    if df_base.empty:
        return pd.DataFrame(columns=[dim, "Métrica"])
    if how == "Soma de VALOR" and "VALOR" in df_base.columns:
        out = df_base.groupby(dim, dropna=False, as_index=False)["VALOR"].sum().rename(columns={"VALOR": "Métrica"})
    else:
        out = df_base.groupby(dim, dropna=False, as_index=False).size().rename(columns={"size": "Métrica"})
    out[dim] = out[dim].fillna("(Sem valor)")
    return out.sort_values("Métrica", ascending=False)

def grafico_generico(df_agregado: pd.DataFrame, dim: str, tipo: str, titulo: str, key: str):
    if df_agregado.empty:
        st.info("Sem dados para exibir neste gráfico.")
        return

    if "Métrica" in df_agregado.columns:
        df_agregado = df_agregado.rename(columns={"Métrica": "QUANTIDADE"})

    if tipo == "Barras":
        fig = px.bar(df_agregado, x=dim, y="QUANTIDADE", text_auto=True, title=titulo)
    elif tipo == "Barras Horizontais":
        fig = px.bar(df_agregado, y=dim, x="QUANTIDADE", text_auto=True, orientation="h", title=titulo)
    elif tipo == "Pizza":
        fig = px.pie(df_agregado, names=dim, values="QUANTIDADE", title=titulo, hole=0.0)
    elif tipo == "Linha":
        fig = px.line(df_agregado, x=dim, y="QUANTIDADE", markers=True, title=titulo)
    elif tipo == "Área":
        fig = px.area(df_agregado, x=dim, y="QUANTIDADE", title=titulo)
    elif tipo == "Coluna 100%":
        total = df_agregado["QUANTIDADE"].sum()
        base = df_agregado.copy()
        base["%"] = (base["QUANTIDADE"] / total * 100).round(2) if total else 0
        fig = px.bar(base, x=dim, y="%", text_auto=True, title=titulo)
    else:
        fig = px.bar(df_agregado, x=dim, y="QUANTIDADE", text_auto=True, title=titulo)

    st.plotly_chart(fig, use_container_width=True, key=key, config=CONFIG_MODEBAR)

def render_por_parlamentar(df_filtrado: pd.DataFrame, top_n_parl: int, tipo_grafico_parl: str, key_prefix: str):
    if {"PARLAMENTAR", "MUNICÍPIO"}.issubset(df_filtrado.columns):
        base_tree = df_filtrado.copy()
        base_tree["VAL_PLOT"] = base_tree["VALOR"].fillna(0) if "VALOR" in base_tree.columns else 1

        metrica_parl = "Soma de VALOR" if ("VALOR" in df_filtrado.columns) else "Contagem"
        base_parl = agrega_por_dimensao(df_filtrado, "PARLAMENTAR", metrica_parl).head(top_n_parl)
        base_parl = base_parl.rename(columns={"Métrica": "QUANTIDADE"})

        fig = px.bar(
            base_parl,
            x="PARLAMENTAR",
            y="QUANTIDADE",
            text_auto=True,
            title=f"QUANTIDADE DE ANÁLISES POR PARLAMENTAR (TOP {len(base_parl)})"
        )
        st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_agg", config=CONFIG_MODEBAR)

def render_temporal(df_filtrado: pd.DataFrame, tipo_grafico_temp: str, key_prefix: str):
    if "DATA OB MS" in df_filtrado.columns and df_filtrado["DATA OB MS"].notna().any():
        base_tempo = df_filtrado.dropna(subset=["DATA OB MS"]).copy()
        base_tempo["Ano-Mês"] = base_tempo["DATA OB MS"].dt.to_period("M").dt.to_timestamp()

        if "VALOR" in base_tempo.columns:
            serie_val = (base_tempo.groupby("Ano-Mês", as_index=False)["VALOR"].sum()
                         .rename(columns={"VALOR": "Métrica"}))
            y_label = "Soma de VALOR"
        else:
            serie_val = (base_tempo.groupby("Ano-Mês", as_index=False).size()
                         .rename(columns={"size": "Métrica"}))
            y_label = "Contagem"

        if tipo_grafico_temp == "Linha":
            fig_time = px.line(serie_val, x="Ano-Mês", y="Métrica", markers=True, title=f"{y_label} por mês")
        elif tipo_grafico_temp == "Área":
            fig_time = px.area(serie_val, x="Ano-Mês", y="Métrica", title=f"{y_label} por mês")
        else:
            fig_time = px.bar(serie_val, x="Ano-Mês", y="Métrica", text_auto=True, title=f"{y_label} por mês")

        st.plotly_chart(fig_time, use_container_width=True, key=f"{key_prefix}_time", config=CONFIG_MODEBAR)
    else:
        st.info("Coluna 'DATA OB MS' ausente ou sem dados válidos.")

def render_barraAgrupada(df_filtrado: pd.DataFrame, agregacao_hm: str, top_n_ano: int, key_prefix: str):
    if {"ANO DA EMENDA", "STATUS GERAL"}.issubset(df_filtrado.columns):
        base = df_filtrado.copy()
        base["ANO DA EMENDA"] = pd.to_numeric(base["ANO DA EMENDA"], errors="coerce")
        base = base.dropna(subset=["ANO DA EMENDA"])

        if agregacao_hm == "Soma de VALOR" and "VALOR" in base.columns:
            df_agg = (
                base.groupby(["ANO DA EMENDA", "STATUS GERAL"], as_index=False)["VALOR"]
                .sum()
                .rename(columns={"VALOR": "Métrica"})
            )
        else:
            df_agg = (
                base.groupby(["ANO DA EMENDA", "STATUS GERAL"], as_index=False)
                .size()
                .rename(columns={"size": "Métrica"})
            )

        anos_disponiveis = sorted(df_agg["ANO DA EMENDA"].unique())
        anos_top = anos_disponiveis[-top_n_ano:] if len(anos_disponiveis) > top_n_ano else anos_disponiveis
        df_agg = df_agg[df_agg["ANO DA EMENDA"].isin(anos_top)]
        df_agg = df_agg.sort_values("ANO DA EMENDA")

        if not df_agg.empty:
            fig = px.bar(
                df_agg,
                x="ANO DA EMENDA",
                y="Métrica",
                color="STATUS GERAL",
                barmode="group",
                text_auto=True,
                title=f"QUANTIDADE POR ANO E STATUS GERAL DA EMENDA (ÚLTIMOS {len(anos_top)} ANOS)"
            )
            fig.update_layout(
                xaxis_title="ANO",
                yaxis_title="QUANTIDADE",
                legend_title="Status Geral",
                bargap=0.15,
                bargroupgap=0.1,
            )
            st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_barras", config=CONFIG_MODEBAR)
        else:
            st.info("Sem dados suficientes para gerar o gráfico.")
    else:
        st.info("São necessárias as colunas 'ANO DA EMENDA' e 'STATUS GERAL'.")

def render_execucao(df_filtrado: pd.DataFrame, key_prefix: str):
    if "EXECUÇÃO DA EMENDA" in df_filtrado.columns:
        exec_norm = df_filtrado["EXECUÇÃO DA EMENDA"].dropna().map(normalizar_txt)
        mapa_exec = {
            "executada": "Executada",
            "em execucao": "Em Execução",
            "em execução": "Em Execução",
            "nao executada": "Não Executada",
            "não executada": "Não Executada"
        }

        exec_padrao = exec_norm.map(mapa_exec).fillna("Outros/Indef.")
        categorias = ["Em Execução", "Executada", "Não Executada", "Outros/Indef."]

        execucoes = (
            exec_padrao.value_counts()
            .reindex(categorias, fill_value=0)
            .reset_index()
            .rename(columns={"index": "SITUAÇÃO", 0: "QUANTIDADE"})
        )
        execucoes.columns = ["SITUAÇÃO", "QUANTIDADE"]

        fig_exec = px.pie(
            execucoes,
            names="SITUAÇÃO",
            values="QUANTIDADE",
            title="SITUAÇÃO DAS EMENDAS",
            hole=0.0,
        )
        fig_exec.update_traces(textinfo="label+value", textfont_size=14)
        st.plotly_chart(fig_exec, use_container_width=True, key=f"{key_prefix}_exec", config=CONFIG_MODEBAR)
    else:
        st.info("Coluna 'EXECUÇÃO DA EMENDA' não encontrada.")
        
# ==========================
# CARGA E PRÉ-PROCESSAMENTO
# ==========================
try:
    df = carregar_dados(CSV_URL)
except Exception as e:
    st.error("❌ Não consegui carregar a planilha. Verifique se está pública (Qualquer pessoa com o link - Leitor).\n\n"
             f"Detalhes: {e}")
    st.stop()

colunas_desejadas = [
    "STATUS GERAL", "ANO DA EMENDA", "Nº EMENDA", "Nº REMANEJAMENTO", "SEI",
    "DATA OB MS", "MUNICÍPIO", "ENTIDADE", "SUBAÇÃO", "GRUPO DE DESPESA",
    "MODALIDADE", "VALOR", "PARLAMENTAR", "PARTIDO DO PARLAMENTAR",
    "PENDÊNCIAS", "SETOR ATUAL ROBÔ", "EXECUÇÃO DA EMENDA"
]
colunas_existentes = [c for c in colunas_desejadas if c in df.columns]
df = df[colunas_existentes].copy()

if "VALOR" in df.columns:
    df["VALOR"] = pd.to_numeric(df["VALOR"], errors="coerce")

if "DATA OB MS" in df.columns:
    df["DATA OB MS"] = pd.to_datetime(df["DATA OB MS"], errors="coerce", dayfirst=True)

# ==========================
# FILTROS (SIDEBAR) — COM (Todos)
# ==========================
st.sidebar.header("Filtros")

def select_valor_com_todos(rotulo: str, serie: pd.Series):
    """Select de valores com (Todos) que retorna None quando (Todos) for escolhido."""
    valores_unicos = sorted(serie.dropna().unique().tolist())
    opcoes = ["(Todos)"] + valores_unicos
    escolha = st.sidebar.selectbox(rotulo, opcoes)
    return None if escolha == "(Todos)" else escolha

PRIMEIRAS_OPCOES = ["Nº EMENDA", "SUBAÇÃO", "ANO DA EMENDA", "PARLAMENTAR"]
opcoes_presentes = [c for c in PRIMEIRAS_OPCOES if c in df.columns]

if not opcoes_presentes:
    st.sidebar.warning("⚠️ Nenhuma das colunas de filtro iniciais existe na planilha.")
    df_filtrado = df.copy()
    filtro1 = filtro2 = filtro3 = filtro4 = None
    valor1 = valor2 = valor3 = valor4 = None
else:
    filtro1 = st.sidebar.selectbox("1º filtro:", opcoes_presentes)
    valor1 = select_valor_com_todos(f"Escolha {filtro1}:", df[filtro1])
    df_filtrado = df[df[filtro1] == valor1] if valor1 is not None else df.copy()

    opcoes_segundo = [c for c in opcoes_presentes if c != filtro1]
    filtro2 = st.sidebar.selectbox("2º filtro (opcional):", ["(Nenhum)"] + opcoes_segundo)
    if filtro2 != "(Nenhum)" and filtro2 in df_filtrado.columns:
        valor2 = select_valor_com_todos(f"Escolha {filtro2}:", df_filtrado[filtro2])
        if valor2 is not None:
            df_filtrado = df_filtrado[df_filtrado[filtro2] == valor2]
    else:
        filtro2 = None
        valor2 = None

    opcoes_terceiro = [c for c in opcoes_presentes if c not in [filtro1, filtro2] and c != "(Nenhum)"]
    filtro3 = st.sidebar.selectbox("3º filtro (opcional):", ["(Nenhum)"] + opcoes_terceiro)
    if filtro3 != "(Nenhum)" and filtro3 in df_filtrado.columns:
        valor3 = select_valor_com_todos(f"Escolha {filtro3}:", df_filtrado[filtro3])
        if valor3 is not None:
            df_filtrado = df_filtrado[df_filtrado[filtro3] == valor3]
    else:
        filtro3 = None
        valor3 = None

    opcoes_quarto = [c for c in opcoes_presentes if c not in [filtro1, filtro2, filtro3] and c != "(Nenhum)"]
    filtro4 = st.sidebar.selectbox("4º filtro (opcional):", ["(Nenhum)"] + opcoes_quarto)
    if filtro4 != "(Nenhum)" and filtro4 in df_filtrado.columns:
        valor4 = select_valor_com_todos(f"Escolha {filtro4}:", df_filtrado[filtro4])
        if valor4 is not None:
            df_filtrado = df_filtrado[df_filtrado[filtro4] == valor4]
    else:
        filtro4 = None
        valor4 = None

def fmt(filtro, valor):
    if not filtro:
        return None
    return f"{filtro}: {('Todos' if valor is None else valor)}"

valor_selecionado = " • ".join([x for x in [
    fmt(filtro1, valor1),
    fmt(filtro2, valor2),
    fmt(filtro3, valor3),
    fmt(filtro4, valor4),
] if x])

# ==========================
# TÍTULO / AÇÕES
# ==========================

# --- Adicionar imagem institucional no topo (lado direito) ---

col1, col2 = st.columns([4, 1])

with col1:
    st.title("📊 Painel de Emendas Parlamentares")
    if valor_selecionado:
        st.caption(f"Filtros aplicados: {valor_selecionado}")

with col2:
    st.markdown("<div style='margin-top: 35px;'></div>", unsafe_allow_html=True)
    st.image("logo.svg", width=200)


st.download_button(
    "⬇️ Exportar Dados",
    data=df_filtrado.to_csv(index=False).encode("utf-8"),
    file_name="emendas_filtrado.csv",
    mime="text/csv",
)

st.subheader("Dados Filtrados")
st.caption(f"{len(df_filtrado)} registros exibidos após os filtros aplicados.")
st.dataframe(df_filtrado, use_container_width=True)

# ==========================
# CONFIGURAÇÃO DE GRÁFICOS (COM SELECTOR)
# ==========================
st.sidebar.header("Gráficos (configuração)")

candidatos_dim = [c for c in df_filtrado.columns if c not in ["VALOR", "DATA OB MS"]]
if not candidatos_dim:
    candidatos_dim = [c for c in df.columns if c not in ["VALOR", "DATA OB MS"]]

dimensao_geral = st.sidebar.selectbox(
    "Dimensão (Visão Geral):",
    options=candidatos_dim,
    index=(candidatos_dim.index("ENTIDADE") if "ENTIDADE" in candidatos_dim else 0)
)
metrica_geral = "Contagem"
tipo_grafico_geral = "Barras"
top_n_geral = st.sidebar.slider("Top N (Visão Geral):", 3, 50, 15)

# Por Parlamentar
tipo_grafico_parl = "Barras"
top_n_parl = st.sidebar.slider("Top N Parlamentares:", 3, 50, 12)

# Gráfico de barras agrupadas
agregacao_hm = "Contagem"
top_n_ano = st.sidebar.slider("Top N Ano:", 3, 50, 5)
# Execução
tipo_grafico_exec = "Barras"

# ==========================
# ABAS
# ==========================
tab_visao, tab_parlamentar, tab_heatmap, tab_execucao = st.tabs(
    ["📊 Panorama Geral", "🧑‍⚖️ Análise por Parlamentar", "📅 Status por ano", "⚙️ Situação das Emendas"]
)

# ---- Aba: Visão Geral (subseções abertas) ----
with tab_visao:
    base = agrega_por_dimensao(df_filtrado, dimensao_geral, metrica_geral).head(top_n_geral)
    grafico_generico(
        base, dimensao_geral, tipo_grafico_geral,
        f"QUANTIDADE POR {dimensao_geral} (TOP {len(base)})",
        key="vg_main"
    )

    render_por_parlamentar(df_filtrado, top_n_parl, tipo_grafico_parl, key_prefix="vg_parl")

    render_barraAgrupada(df_filtrado, agregacao_hm, top_n_ano, key_prefix="vg_hm")

    render_execucao(df_filtrado, key_prefix="vg_exec")

# ---- Aba: Por Parlamentar ----
with tab_parlamentar:
    render_por_parlamentar(df_filtrado, top_n_parl, tipo_grafico_parl, key_prefix="tab_parl")

# ---- Aba: Barra Agrupada ----
with tab_heatmap:
    render_barraAgrupada(df_filtrado, agregacao_hm, top_n_ano, key_prefix="tab_hm")

# ---- Aba: Execução ----
with tab_execucao:
    render_execucao(df_filtrado,  key_prefix="tab_exec")