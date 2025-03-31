import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import calendar
from dotenv import load_dotenv
import os

# Configuração da página
st.set_page_config(page_title="Dashboard de Metas e Realizados", page_icon="📊", layout="wide")

# Carregando variáveis de ambiente
load_dotenv()

# Título e descrição
st.title("Dashboard de Metas e Realizados")
st.markdown("""
Este dashboard apresenta a análise de metas vs. realizados por faixa de dias, permitindo visualizar o desempenho atual e projeções futuras.
""")

# Carregar dados
@st.cache_data
def load_data():
    url = 'https://docs.google.com/spreadsheets/d/15WAIszw3nCjT2_01z_2DLeVG2ziVOMiA4s72l7Q1yzg/export?format=csv&gid=451427835'
    df = pd.read_csv(url)
    
    # Mostrar os dados brutos para debug
    st.write("Dados brutos:")
    st.write(df.head())
    
    # Processar todas as colunas numéricas
    for col in df.columns:
        if col != 'Dia':  # Pular a coluna de data
            # Converter para string primeiro
            df[col] = df[col].astype(str)
            
            # Remover R$, pontos e substituir vírgulas
            df[col] = df[col].str.replace('R\$', '', regex=True)
            df[col] = df[col].str.replace('\.', '', regex=True)
            df[col] = df[col].str.replace(',', '.', regex=True)
            
            # Limpar espaços
            df[col] = df[col].str.strip()
            
            # Converter para numérico
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Converter a coluna 'Dia' para datetime se não for a linha "Mensal"
    if 'Dia' in df.columns:
        # Definir a coluna Dia como índice
        df.set_index('Dia', inplace=True)
    
    # Mostrar os dados processados
    st.write("Dados processados:")
    st.write(df.head())
    
    return df

# Função para calcular projeções
def calcular_projecoes(df, dias_restantes):
    projecoes = {}
    gaps = {}
    
    # Verificar se existe a linha "Mensal"
    if 'Mensal' in df.index:
        mensal = df.loc['Mensal']
        
        # Colunas de realizados e metas
        colunas_realizados = [col for col in df.columns if 'Realizado' in col]
        colunas_metas = [col for col in df.columns if 'Meta' in col]
        
        # Garantir que todas as faixas estejam presentes
        faixas_esperadas = ['1-30', '31', '61', '121', '181', '361']
        
        # Verificar se as colunas esperadas existem
        for faixa in faixas_esperadas:
            col_realizado = f'Realizado {faixa}'
            col_meta = f'Meta {faixa}'
            
            if col_realizado in df.columns and col_meta in df.columns:
                # Dados históricos (excluindo a linha Mensal)
                df_historico = df.drop('Mensal', errors='ignore')
                
                # Se houver mais de 7 dias, pegar os últimos 7
                df_ultimos_dias = df_historico.iloc[-7:] if len(df_historico) > 7 else df_historico
                
                try:
                    # Calcular a média diária dos últimos dias
                    media_diaria = df_ultimos_dias[col_realizado].mean()
                    
                    # Obter a meta e o realizado atual do mensal
                    meta_total = float(mensal[col_meta])
                    realizado_atual = float(mensal[col_realizado])
                    
                    # Verificar se os valores são válidos
                    if pd.isna(meta_total) or pd.isna(realizado_atual) or pd.isna(media_diaria):
                        st.warning(f"Valores inválidos encontrados para a faixa {faixa}. Pulando...")
                        continue
                    
                    # Calcular projeção
                    projecao = realizado_atual + (media_diaria * dias_restantes)
                    
                    # Calcular gap diário necessário para atingir a meta
                    gap_total = meta_total - realizado_atual
                    gap_diario = gap_total / dias_restantes if dias_restantes > 0 else 0
                    
                    projecoes[faixa] = {
                        'meta_total': meta_total,
                        'realizado_atual': realizado_atual,
                        'media_diaria': media_diaria,
                        'projecao_fim_mes': projecao,
                        'percentual_projetado': (projecao / meta_total * 100) if meta_total > 0 else 0,
                        'gap_total': gap_total,
                        'gap_diario_necessario': gap_diario
                    }
                    
                    gaps[faixa] = gap_diario
                except Exception as e:
                    st.error(f"Erro ao processar a faixa {faixa}: {str(e)}")
                    st.write(f"Valores na coluna {col_realizado}:", df[col_realizado].head())
                    st.write(f"Valores na coluna {col_meta}:", df[col_meta].head())
            else:
                st.warning(f"Colunas para a faixa {faixa} não encontradas no DataFrame.")
    else:
        st.error("Linha 'Mensal' não encontrada no DataFrame.")
    
    return projecoes, gaps

# Adicionar uma função para calcular totais conforme solicitado
def calcular_totais(df):
    totais = {}
    
    try:
        # Verificar se existe a linha "Mensal"
        if 'Mensal' in df.index:
            mensal = df.loc['Mensal']
            
            # Calcular totais mensais
            colunas_realizados = [col for col in df.columns if 'Realizado' in col]
            colunas_metas = [col for col in df.columns if 'Meta' in col]
            
            realizado_total = mensal[colunas_realizados].sum()
            meta_total = mensal[colunas_metas].sum()
            
            totais['realizado_total'] = realizado_total
            totais['meta_total'] = meta_total
            
            # Dados históricos (excluindo a linha Mensal e a última linha)
            df_historico = df.drop('Mensal', errors='ignore').iloc[:-2]
            
            # Calcular totais por faixa
            r1 = df_historico['Realizado 1-30'].sum() if 'Realizado 1-30' in df_historico.columns else 0
            r30 = df_historico['Realizado 31'].sum() if 'Realizado 31' in df_historico.columns else 0
            r61 = df_historico['Realizado 61'].sum() if 'Realizado 61' in df_historico.columns else 0
            r121 = df_historico['Realizado 121'].sum() if 'Realizado 121' in df_historico.columns else 0
            r181 = df_historico['Realizado 181'].sum() if 'Realizado 181' in df_historico.columns else 0
            r361 = df_historico['Realizado 361'].sum() if 'Realizado 361' in df_historico.columns else 0
            
            totais['r1_total'] = r1
            totais['r30_total'] = r30
            totais['r61_total'] = r61
            totais['r121_total'] = r121
            totais['r181_total'] = r181
            totais['r361_total'] = r361
            
            # Adicionar séries históricas
            totais['r1_serie'] = df_historico['Realizado 1-30'] if 'Realizado 1-30' in df_historico.columns else None
            totais['r30_serie'] = df_historico['Realizado 31'] if 'Realizado 31' in df_historico.columns else None
            totais['r61_serie'] = df_historico['Realizado 61'] if 'Realizado 61' in df_historico.columns else None
            totais['r121_serie'] = df_historico['Realizado 121'] if 'Realizado 121' in df_historico.columns else None
            totais['r181_serie'] = df_historico['Realizado 181'] if 'Realizado 181' in df_historico.columns else None
            totais['r361_serie'] = df_historico['Realizado 361'] if 'Realizado 361' in df_historico.columns else None
    except Exception as e:
        st.error(f"Erro ao calcular totais: {str(e)}")
    
    return totais

# Carregar dados
with st.spinner('Carregando dados...'):
    df = load_data()
    
    if df.empty:
        st.error("Não foi possível carregar os dados. Verifique a URL da planilha.")
        st.stop()
    
    st.success(f"Dados carregados com sucesso! Total de {len(df)} registros.")

# Determinar o mês atual e dias restantes
hoje = datetime.now()
ultimo_dia_mes = calendar.monthrange(hoje.year, hoje.month)[1]
dias_restantes = ultimo_dia_mes - hoje.day

# Calcular projeções e totais
projecoes, gaps = calcular_projecoes(df, dias_restantes)
totais = calcular_totais(df)

# Layout em abas
tab1, tab2, tab3, tab4 = st.tabs([
    "Visão Geral", 
    "Análise por Faixa", 
    "Histórico Diário",
    "Projeções"
])

with tab1:
    st.header("Visão Geral - Meta vs. Realizado")
    
    # Resumo em cards
    st.subheader("Resumo do Mês")
    
    # Criar 3 colunas para os cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Meta Total", f"R$ {totais['meta_total']:,.2f}")
    
    with col2:
        st.metric("Realizado Total", f"R$ {totais['realizado_total']:,.2f}")
    
    with col3:
        percentual_total = (totais['realizado_total'] / totais['meta_total'] * 100) if totais['meta_total'] > 0 else 0
        st.metric("% Atingido", f"{percentual_total:.2f}%")
    
    # Adicionar informação sobre dias restantes
    st.info(f"Restam {dias_restantes} dias para o fim do mês.")
    
    # Criar dataframe para o gráfico de barras
    faixas = []
    metas = []
    realizados = []
    percentuais = []
    
    for faixa, dados in projecoes.items():
        faixas.append(faixa)
        metas.append(dados['meta_total'])
        realizados.append(dados['realizado_atual'])
        percentuais.append(dados['realizado_atual'] / dados['meta_total'] * 100 if dados['meta_total'] > 0 else 0)
    
    df_visao_geral = pd.DataFrame({
        'Faixa': faixas,
        'Meta': metas,
        'Realizado': realizados,
        'Percentual': percentuais
    })
    
    # Dividir em duas colunas
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de barras comparando meta e realizado
        fig = px.bar(
            df_visao_geral, 
            x='Faixa', 
            y=['Meta', 'Realizado'],
            barmode='group',
            title='Meta vs. Realizado por Faixa',
            labels={'value': 'Valor', 'variable': 'Tipo'},
            color_discrete_sequence=['#1f77b4', '#ff7f0e']
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Gráfico de percentual atingido
        fig = px.bar(
            df_visao_geral,
            x='Faixa',
            y='Percentual',
            title='Percentual da Meta Atingido por Faixa',
            labels={'Percentual': '% da Meta'},
            color='Percentual',
            color_continuous_scale=px.colors.sequential.Viridis
        )
        fig.update_layout(yaxis_range=[0, 100])
        fig.add_hline(y=100, line_dash="dash", line_color="red")
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header("Análise por Faixa")
    
    # Seletor de faixa
    faixas_disponiveis = list(projecoes.keys())
    faixa_selecionada = st.selectbox("Selecione a faixa para análise detalhada:", faixas_disponiveis)
    
    if faixa_selecionada:
        # Obter dados da faixa selecionada
        dados_faixa = projecoes[faixa_selecionada]
        
        # Criar colunas para métricas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Meta", f"R$ {dados_faixa['meta_total']:,.2f}")
            st.metric("Realizado", f"R$ {dados_faixa['realizado_atual']:,.2f}")
        
        with col2:
            percentual = dados_faixa['realizado_atual'] / dados_faixa['meta_total'] * 100 if dados_faixa['meta_total'] > 0 else 0
            st.metric("% Atingido", f"{percentual:.2f}%")
            st.metric("Média Diária", f"R$ {dados_faixa['media_diaria']:,.2f}")
        
        with col3:
            st.metric("Gap Total", f"R$ {dados_faixa['gap_total']:,.2f}")
            st.metric("Gap Diário Necessário", f"R$ {dados_faixa['gap_diario_necessario']:,.2f}")
        
        # Gráfico de progresso
        st.subheader("Progresso da Meta")
        
        # Criar dados para o gráfico de gauge
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=percentual,
            title={'text': f"Progresso da Meta - Faixa {faixa_selecionada}"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#1f77b4"},
                'steps': [
                    {'range': [0, 50], 'color': "#ffdd99"},
                    {'range': [50, 75], 'color': "#ffcc66"},
                    {'range': [75, 100], 'color': "#99ff99"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 100
                }
            }
        ))
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Gráfico de tendência diária para a faixa selecionada
        col_realizado = f"Realizado {faixa_selecionada}"
        
        if 'Dia' in df.columns:
            df_tendencia = df[['Dia', col_realizado]].copy()
        elif 'Dia' in df.index.names:
            # Se 'Dia' for o índice, resete-o para torná-lo uma coluna
            df_tendencia = df.reset_index()[['Dia', col_realizado]].copy()
        else:
            # Se 'Dia' não existir, use o índice atual como substituto
            df_tendencia = df.reset_index()
            df_tendencia.columns = ['Dia'] + list(df_tendencia.columns[1:])
            df_tendencia = df_tendencia[['Dia', col_realizado]].copy()
        
        # Calcular a diferença diária (incremento)
        df_tendencia['Incremento'] = df_tendencia[col_realizado].diff()
        
        # Substituir NaN por 0
        df_tendencia['Incremento'] = df_tendencia['Incremento'].fillna(0)
        
        # Gráfico de incremento diário
        st.subheader("Incremento Diário")
        fig = px.bar(
            df_tendencia,
            x='Dia',
            y='Incremento',
            title=f'Incremento Diário - Faixa {faixa_selecionada}',
            labels={'Incremento': 'Valor Incremental', 'Dia': 'Data'},
            color='Incremento',
            color_continuous_scale=px.colors.sequential.Viridis
        )
        
        # Adicionar linha de média móvel
        df_tendencia['Media_Movel'] = df_tendencia['Incremento'].rolling(window=7, min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=df_tendencia['Dia'],
            y=df_tendencia['Media_Movel'],
            mode='lines',
            name='Média Móvel (7 dias)',
            line=dict(color='red', width=2)
        ))
        
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.header("Histórico Diário")
    
    # Criar figura para o gráfico de linha histórico
    fig = go.Figure()
    
    # Adicionar séries temporais
    series_data = {
        'Realizado 1-30': totais['r1_serie'],
        'Realizado 31': totais['r30_serie'],
        'Realizado 61': totais['r61_serie'],
        'Realizado 121': totais['r121_serie'],
        'Realizado 181': totais['r181_serie'],
        'Realizado 361': totais['r361_serie']
    }
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    for i, (nome, serie) in enumerate(series_data.items()):
        if serie is not None and not serie.empty:
            fig.add_trace(go.Scatter(
                x=serie.index,
                y=serie.values,
                mode='lines+markers',
                name=nome,
                line=dict(color=colors[i % len(colors)], width=2)
            ))
    
    # Configurar layout
    fig.update_layout(
        title='Histórico de Realizados por Faixa',
        xaxis_title='Data',
        yaxis_title='Valor Realizado',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Mostrar totais por faixa
    st.subheader("Totais Realizados por Faixa")
    
    # Criar dataframe para os totais
    df_totais = pd.DataFrame({
        'Faixa': ['1-30', '31', '61', '121', '181', '361'],
        'Total Realizado': [
            totais['r1_total'],
            totais['r30_total'],
            totais['r61_total'],
            totais['r121_total'],
            totais['r181_total'],
            totais['r361_total']
        ]
    })
    
    # Gráfico de barras para os totais
    fig = px.bar(
        df_totais,
        x='Faixa',
        y='Total Realizado',
        title='Total Realizado por Faixa',
        color='Total Realizado',
        color_continuous_scale=px.colors.sequential.Viridis
    )
    
    st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.header("Projeções e Análise de Gap")
    
    # Seletor de faixa para projeções
    faixa_projecao = st.selectbox("Selecione a faixa para visualizar projeções:", faixas_disponiveis, key="projecao_faixa")
    
    if faixa_projecao and faixa_projecao in projecoes:
        dados_projecao = projecoes[faixa_projecao]
        
        # Criar colunas para métricas de projeção
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Projeção para Fim do Mês", f"R$ {dados_projecao['projecao_fim_mes']:,.2f}")
            st.metric("Meta", f"R$ {dados_projecao['meta_total']:,.2f}")
            
            # Calcular delta para a meta
            delta = dados_projecao['projecao_fim_mes'] - dados_projecao['meta_total']
            delta_percentual = delta / dados_projecao['meta_total'] * 100 if dados_projecao['meta_total'] > 0 else 0
            
            st.metric(
                "Diferença Projetada", 
                f"R$ {delta:,.2f}", 
                delta=f"{delta_percentual:.2f}%",
                delta_color="normal"
            )
        
        with col2:
            st.metric("% Projetado da Meta", f"{dados_projecao['percentual_projetado']:.2f}%")
            st.metric("Gap Diário Necessário", f"R$ {dados_projecao['gap_diario_necessario']:,.2f}")
            st.metric("Média Diária Atual", f"R$ {dados_projecao['media_diaria']:,.2f}")
        
        # Gráfico de projeção
        st.subheader("Projeção Linear")
        
        # Criar dados para o gráfico de projeção
        col_realizado = f"Realizado {faixa_projecao}"
        
        if 'Dia' in df.columns:
            df_tendencia = df[['Dia', col_realizado]].copy()
        elif 'Dia' in df.index.names:
            # Se 'Dia' for o índice, resete-o para torná-lo uma coluna
            df_tendencia = df.reset_index()[['Dia', col_realizado]].copy()
        else:
            # Se 'Dia' não existir, use o índice atual como substituto
            df_tendencia = df.reset_index()
            df_tendencia.columns = ['Dia'] + list(df_tendencia.columns[1:])
            df_tendencia = df_tendencia[['Dia', col_realizado]].copy()
        
        # Obter o último valor realizado
        ultimo_realizado = df[col_realizado].iloc[-1]
        
        # Criar datas futuras
        if 'Dia' in df.columns:
            ultima_data = df['Dia'].max()
        else:
            # Se 'Dia' for o índice
            ultima_data = df.index.max()
            if ultima_data == 'Mensal':
                # Se o índice máximo for 'Mensal', pegar o penúltimo
                ultima_data = sorted(df.index)[len(df.index)-2]

        if isinstance(ultima_data, str):
            # Se for string, converter para data
            ultima_data = datetime.now().date()
        datas_futuras = [ultima_data + timedelta(days=i+1) for i in range(dias_restantes)]
        
        # Criar valores projetados
        valores_projetados = [ultimo_realizado + dados_projecao['media_diaria'] * (i+1) for i in range(dias_restantes)]
        
        # Criar dataframe para o gráfico
        df_projecao = pd.DataFrame({
            'Dia': datas_futuras,
            'Projeção': valores_projetados
        })
        
        # Criar figura
        fig = go.Figure()
        
        # Adicionar linha histórica
        fig.add_trace(go.Scatter(
            x=df_tendencia['Dia'],
            y=df_tendencia[col_realizado],
            mode='lines+markers',
            name='Realizado',
            line=dict(color='#1f77b4', width=2)
        ))
        
        # Adicionar linha de projeção
        fig.add_trace(go.Scatter(
            x=df_projecao['Dia'],
            y=df_projecao['Projeção'],
            mode='lines',
            name='Projeção',
            line=dict(color='#ff7f0e', width=2, dash='dash')
        ))
        
        # Adicionar linha da meta
        fig.add_trace(go.Scatter(
            x=[df_tendencia['Dia'].min(), df_projecao['Dia'].max()],
            y=[dados_projecao['meta_total'], dados_projecao['meta_total']],
            mode='lines',
            name='Meta',
            line=dict(color='red', width=2, dash='dot')
        ))
        
        # Configurar layout
        fig.update_layout(
            title=f'Projeção Linear - Faixa {faixa_projecao}',
            xaxis_title='Data',
            yaxis_title='Valor',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Gráfico de gap diário
        st.subheader("Análise de Gap Diário")
        
        # Calcular gap entre média atual e necessária
        gap_media = dados_projecao['gap_diario_necessario'] - dados_projecao['media_diaria']
        gap_percentual = gap_media / dados_projecao['gap_diario_necessario'] * 100 if dados_projecao['gap_diario_necessario'] > 0 else 0
        
        # Criar dados para o gráfico de comparação
        df_gap = pd.DataFrame({
            'Tipo': ['Média Atual', 'Necessário Diário'],
            'Valor': [dados_projecao['media_diaria'], dados_projecao['gap_diario_necessario']]
        })
        
        # Criar gráfico de barras
        fig = px.bar(
            df_gap,
            x='Tipo',
            y='Valor',
            title=f'Comparação: Média Atual vs. Necessário Diário - Faixa {faixa_projecao}',
            color='Tipo',
            color_discrete_sequence=['#1f77b4', '#ff7f0e']
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Adicionar análise textual
        if gap_media > 0:
            st.warning(f"""
            **Análise de Gap:**
            
            Para atingir a meta na faixa {faixa_projecao}, é necessário aumentar a média diária em **R$ {gap_media:,.2f}** 
            (aumento de {abs(gap_percentual):.2f}% em relação à média atual).
            
            Com a média atual, a projeção indica que chegaremos a **{dados_projecao['percentual_projetado']:.2f}%** da meta.
            """)
        else:
            st.success(f"""
            **Análise de Gap:**
            
            A média diária atual está **R$ {abs(gap_media):,.2f}** acima do necessário para atingir a meta na faixa {faixa_projecao}.
            
            Com a média atual, a projeção indica que superaremos a meta, chegando a **{dados_projecao['percentual_projetado']:.2f}%**.
            """)

# Adicionar rodapé
st.markdown("---")
st.markdown("© 2023 Dashboard de Metas e Realizados - Todos os direitos reservados")

