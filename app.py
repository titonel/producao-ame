import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import openpyxl
import plotly.express as px
from io import BytesIO
import os 
import json # Importar para carregar dados geojson

# Importa as funções de processamento de upload do arquivo uploads.py
from uploads import normalizar_especialidade, process_siresp_upload, process_contratos_upload, process_cdr_upload

# --- Gestão de Usuários (para demonstração, usar método seguro em produção) ---
USERS = {
    "ame_user": "ame_password",  # Substitua por uma forma segura de armazenar/recuperar credenciais
    "admin": "admin_password"
}

def authenticate(username, password):
    """
    Função para autenticar o usuário.
    Em uma aplicação real, verificar com senhas hash.
    """
    if username in USERS and USERS[username] == password:
        return True
    return False

# Função para carregar o GeoJSON com cache
@st.cache_data
def load_geojson(path):
    """
    Carrega um arquivo GeoJSON do caminho especificado e o armazena em cache.
    Retorna os dados GeoJSON ou None em caso de erro.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"❌ Erro: O arquivo '{path}' não foi encontrado. Por favor, certifique-se de que ele está no mesmo diretório do seu aplicativo.")
        return None
    except json.JSONDecodeError:
        st.error(f"❌ Erro: O arquivo '{path}' não é um JSON válido ou está corrompido.")
        return None
    except Exception as e:
        st.error(f"❌ Erro inesperado ao carregar o GeoJSON: {e}")
        return None

# Lista de meses para ordenação correta
meses_ordem = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
               'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

# --- Configuração da página ---
st.set_page_config(page_title="Produção Médica AME", layout="wide")

# --- Lógica da Página de Login ---
# Inicializa o estado de autenticação se ainda não estiver definido
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None

# Se o usuário não estiver autenticado, exibe a página de login
if not st.session_state.authenticated:
    st.title("Login - AME Caraguatatuba")
    st.markdown("---") # Separador visual

    username = st.text_input("Usuário", key="login_username")
    password = st.text_input("Senha", type="password", key="login_password")

    if st.button("Entrar", key="login_button"):
        if authenticate(username, password):
            st.session_state.authenticated = True
            st.session_state.username = username  # Armazena o nome de usuário no estado da sessão
            st.success(f"Bem-vindo, {username}!")
            st.rerun()  # Recarrega a página para mostrar a aplicação principal
        else:
            st.error("Usuário ou senha inválidos.")
    st.markdown("---") # Separador visual
    st.info("Use 'ame_user' como usuário e 'ame_password' como senha para testar.")
    st.info("Ou 'admin' como usuário e 'admin_password' como senha.")

# Se o usuário estiver autenticado, exibe a aplicação principal
else:
    st.title("📊 AME Caraguatatuba")
    st.title("📊 Sistema de Produção Médica")

    # Navegação lateral
    pagina = st.sidebar.radio("Escolha a opção:", ["Performance", "Dados Gerais", "Uploads", "Absenteísmo", "Custos Médicos", "CDR"])
    
    # Botão de Sair na barra lateral
    st.sidebar.markdown("---")
    if st.sidebar.button("Sair", key="logout_button"):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.rerun() # Recarrega a página para voltar à tela de login

    # Conexão com o banco SQLite
    engine = create_engine('sqlite:///producao.db')

    # Página: UPLOADS
    if pagina == "Uploads":
        st.header("⬆️ Upload de Arquivos")
        
        st.subheader("Upload de Dados de Produção (SIRESP)")
        uploaded_file_producao = st.file_uploader("Selecione o arquivo de produção (Excel: .xlsx, .xls; CSV: .csv)", type=["xlsx", "xls", "csv"], key="upload_producao")

        if uploaded_file_producao:
            # Chama a função do uploads.py para processar o arquivo
            process_siresp_upload(uploaded_file_producao, engine)
        
        st.markdown("---") # Separador para os uploads

        st.subheader("Upload de Dados de Custos Médicos (Contratos)")
        uploaded_file_contratos = st.file_uploader("Selecione o arquivo Excel de contratos", type=["xlsx"], key="upload_contratos")

        if uploaded_file_contratos:
            # Chama a função do uploads.py para processar o arquivo
            process_contratos_upload(uploaded_file_contratos, engine)
        
        st.markdown("---") # Separador para os uploads

        st.subheader("Upload de Dados de CDR (CSV)")
        uploaded_file_cdr = st.file_uploader("Selecione o arquivo CSV de CDR", type=["csv"], key="upload_cdr")

        if uploaded_file_cdr:
            # Chama a função do uploads.py para processar o arquivo CDR
            process_cdr_upload(uploaded_file_cdr, engine)

    # Página: INSERIR DADOS (Agora vazia, pois o upload foi movido para 'Uploads')
    elif pagina == "Inserir Dados":
        st.header("ℹ️ Informações sobre Inserção de Dados")
        st.info("A funcionalidade de upload de dados foi movida para a página 'Uploads'.")


    # Página: PERFORMANCE
    elif pagina == "Performance":
        st.header("📈 Performance das Agendas Médicas por Especialidade")
        
        try:
            df = pd.read_sql_table('producao', con=engine)

            # Remover códigos numéricos iniciais da especialidade
            df['Especialidade'] = df['Especialidade'].astype(str).str.replace(r'^\d+\s*', '', regex=True).str.strip()

            # Normalizar nomes com agrupamento genérico
            df['Especialidade_Normalizada'] = df['Especialidade'].apply(normalizar_especialidade)
            df['Mes_Producao'] = df['Mes_Producao'].astype(str).str.lower() # Garante minúsculas para comparação
            df['Mes_Num'] = df['Mes_Producao'].apply(lambda x: meses_ordem.index(x) + 1 if x in meses_ordem else 0)

            # Filtros para a página de Performance
            anos = sorted(df['Ano_Producao'].unique())
            meses = sorted(df['Mes_Producao'].unique(), key=lambda x: meses_ordem.index(x.lower()))
            especialidades = sorted(df['Especialidade_Normalizada'].unique())

            st.sidebar.subheader("🔎 Filtros de Performance")
            ano_filtro = st.sidebar.multiselect("Ano", anos, default=anos, key="perf_ano")
            mes_filtro = st.sidebar.multiselect("Mês", meses, default=meses, key="perf_mes")
            especialidade_filtro = st.sidebar.multiselect("Especialidade", especialidades, default=especialidades, key="perf_especialidade")

            # Aplicar filtros
            df_filtro = df[
                (df['Ano_Producao'].isin(ano_filtro)) &
                (df['Mes_Producao'].isin(mes_filtro)) &
                (df['Especialidade_Normalizada'].isin(especialidade_filtro))
            ]

            if df_filtro.empty:
                st.warning("Nenhum dado encontrado para os filtros selecionados.")
            else:
                # Agrupar por especialidade normalizada e somar Oferta, Agendados e Realizados
                df_agrupado = df_filtro.groupby('Especialidade_Normalizada').agg({
                    'Oferta': 'sum',
                    'Agendados': 'sum',
                    'Realizados': 'sum'
                }).reset_index()

                # Criar o gráfico de barras
                fig = px.bar(
                    df_agrupado,
                    x='Especialidade_Normalizada',
                    y='Realizados',
                    title='Total de Atendimentos Realizados por Especialidade',
                    labels={'Especialidade_Normalizada': 'Especialidade', 'Realizados': 'Atendimentos Realizados'},
                    color='Realizados' # Opcional: colore as barras com base no valor de Realizados
                )
                fig.update_xaxes(tickangle=45) # Inclina os rótulos do eixo X para melhor legibilidade
                fig.update_yaxes(rangemode="tozero") # Começa o eixo Y em zero

                st.plotly_chart(fig, use_container_width=True)

                st.subheader("Dados Detalhados de Performance")
                st.dataframe(df_agrupado.rename(columns={'Especialidade_Normalizada': 'Especialidade'}), use_container_width=True)

        except Exception as e:
            st.error(f"Erro ao carregar dados de performance: {e}")

    elif pagina == "Dados Gerais":
        st.header("📋 Dados Gerais Consolidados")

        try:
            df = pd.read_sql_table('producao', con=engine)
            
            # Remover códigos numéricos iniciais da especialidade
            df['Especialidade'] = df['Especialidade'].astype(str).str.replace(r'^\d+\s*', '', regex=True).str.strip()

            # Normalizar nomes com agrupamento genérico
            df['Especialidade_Normalizada'] = df['Especialidade'].apply(normalizar_especialidade)
            df['Mes_Producao'] = df['Mes_Producao'].astype(str).str.lower() # Garante minúsculas para comparação

            # Filtros
            anos = sorted(df['Ano_Producao'].unique())
            meses = sorted(df['Mes_Producao'].unique(), key=lambda x: meses_ordem.index(x.lower()))

            st.sidebar.subheader("🔎 Filtros Gerais")
            ano_filtro = st.sidebar.multiselect("Ano", anos, default=anos, key="geral_ano")
            mes_filtro = st.sidebar.multiselect("Mês", meses, default=meses, key="geral_mes")

            # Aplicar filtros
            df_filtro = df[
                (df['Ano_Producao'].isin(ano_filtro)) &
                (df['Mes_Producao'].isin(mes_filtro))
            ]

            if df_filtro.empty:
                st.warning("Nenhum dado disponível para os filtros selecionados.")
            else:
                # Agrupar dados por Especialidade consolidada
                df_grouped = (
                    df_filtro
                    .groupby(['Especialidade_Normalizada', 'Ano_Producao', 'Mes_Producao'])
                    .agg({
                        'Oferta': 'sum',
                        'Agendados': 'sum',
                        'Realizados': 'sum'
                    })
                    .reset_index()
                    .rename(columns={
                        'Especialidade_Normalizada': 'Especialidade',
                        'Ano_Producao': 'Ano',
                        'Mes_Producao': 'Mês'
                    })
                )

                # Calcular Absenteísmo com tratamento de divisão por zero
                df_grouped['Absenteísmo'] = df_grouped.apply(
                    lambda row: 1 - (row['Realizados'] / row['Agendados']) if row['Agendados'] and row['Agendados'] > 0 else 0,
                    axis=1
                )

                df_grouped['Absenteísmo (%)'] = (df_grouped['Absenteísmo'] * 100).round(2).astype(str).str.replace('.', ',', regex=False) + '%'
                
                st.dataframe(df_grouped, use_container_width=True)
                
                # Exportar como Excel
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_grouped.to_excel(writer, index=False, sheet_name='Dados')
                processed_data = output.getvalue()

                st.download_button(
                    label="📥 Baixar como Excel",
                    data=processed_data,
                    file_name="dados_consolidados.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        except Exception as e:
            st.error(f"❌ Erro ao carregar os dados: {e}")

    # Página: ABSENTEÍSMO
    elif pagina == "Absenteísmo":
        st.header("📉 Taxa de Absenteísmo por Especialidade")

        try:
            df = pd.read_sql_table('producao', con=engine)

            # Remover códigos numéricos iniciais da especialidade
            df['Especialidade'] = df['Especialidade'].astype(str).str.replace(r'^\d+\s*', '', regex=True).str.strip()

            # Normalizar nomes com agrupamento genérico
            df['Especialidade_Normalizada'] = df['Especialidade'].apply(normalizar_especialidade)
            df['Mes_Producao'] = df['Mes_Producao'].astype(str).str.lower()
            df['Mes_Num'] = df['Mes_Producao'].apply(lambda x: meses_ordem.index(x) + 1 if x in meses_ordem else 0)

            # Filtros para a página de Absenteísmo
            anos = sorted(df['Ano_Producao'].unique())
            meses = sorted(df['Mes_Producao'].unique(), key=lambda x: meses_ordem.index(x.lower()))
            especialidades = sorted(df['Especialidade_Normalizada'].unique())

            st.sidebar.subheader("🔎 Filtros de Absenteísmo")
            ano_filtro_abs = st.sidebar.multiselect("Ano", anos, default=anos, key="abs_ano")
            mes_filtro_abs = st.sidebar.multiselect("Mês", meses, default=meses, key="abs_mes")
            especialidade_filtro_abs = st.sidebar.multiselect("Especialidade", especialidades, default=especialidades, key="abs_especialidade")

            # Aplicar filtros
            df_filtro = df[
                (df['Ano_Producao'].isin(ano_filtro_abs)) &
                (df['Mes_Producao'].isin(mes_filtro_abs)) &
                (df['Especialidade_Normalizada'].isin(especialidade_filtro_abs))
            ]

            if df_filtro.empty:
                st.warning("Nenhum dado encontrado para os filtros selecionados.")
            else:
                # Agrupar por período e especialidade normalizada
                df_grouped_abs = (
                    df_filtro
                    .groupby(['Ano_Producao', 'Mes_Producao', 'Mes_Num', 'Especialidade_Normalizada'])
                    .agg({
                        'Agendados': 'sum',
                        'Realizados': 'sum'
                    })
                    .reset_index()
                )

                # Calcular Absenteísmo
                df_grouped_abs['Absenteísmo'] = df_grouped_abs.apply(
                    lambda row: (1 - (row['Realizados'] / row['Agendados'])) * 100
                    if row['Agendados'] and row['Agendados'] > 0 else 0,
                    axis=1
                )
                df_grouped_abs['Absenteísmo'] = df_grouped_abs['Absenteísmo'].round(2)

                # Criar coluna de período para o eixo X e ordenar
                df_grouped_abs['Periodo'] = df_grouped_abs['Mes_Num'].astype(str).str.zfill(2) + '/' + df_grouped_abs['Ano_Producao'].astype(str)
                df_grouped_abs = df_grouped_abs.sort_values(by=['Ano_Producao', 'Mes_Num'])

                # Criar o gráfico de linha
                fig_abs = px.line(
                    df_grouped_abs,
                    x='Periodo',
                    y='Absenteísmo',
                    color='Especialidade_Normalizada',
                    title='Taxa de Absenteísmo por Especialidade',
                    markers=True,
                    labels={'Absenteísmo': 'Absenteísmo (%)', 'Periodo': 'Período (Mês/Ano)', 'Especialidade_Normalizada': 'Especialidade'},
                    hover_data={'Absenteísmo': ':.2f%', 'Periodo': True, 'Especialidade_Normalizada': True} # Formata tooltip
                )

                fig_abs.update_layout(
                    hovermode="x unified" # Melhora a interação do hover
                )
                fig_abs.update_yaxes(rangemode="tozero") # Começa o eixo Y em zero
                fig_abs.update_xaxes(tickangle=45) # Inclina os rótulos do eixo X para melhor legibilidade

                st.plotly_chart(fig_abs, use_container_width=True)

                st.subheader("Dados Detalhados de Absenteísmo")
                # Prepara os dados para exibição em tabela Streamlit (com formatação de vírgula)
                df_display_for_st = df_grouped_abs.copy()
                df_display_for_st['Absenteísmo (%)'] = df_display_for_st['Absenteísmo'].astype(str).str.replace('.', ',', regex=False) + '%'
                st.dataframe(df_display_for_st[['Ano_Producao', 'Mes_Producao', 'Especialidade_Normalizada', 'Agendados', 'Realizados', 'Absenteísmo (%)']], use_container_width=True)
                
                # Exportar como Excel
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    # Seleciona as colunas desejadas para exportação, usando o valor numérico de 'Absenteísmo'
                    df_to_export = df_grouped_abs[['Ano_Producao', 'Mes_Producao', 'Especialidade_Normalizada', 'Agendados', 'Realizados', 'Absenteísmo']].copy()
                    
                    # Garante que 'Ano_Producao' seja do tipo inteiro
                    df_to_export['Ano_Producao'] = df_to_export['Ano_Producao'].astype(int)

                    df_to_export.to_excel(writer, index=False, sheet_name='Dados')

                    # Acessa o workbook e o worksheet para aplicar a formatação numérica
                    workbook = writer.book
                    worksheet = writer.sheets['Dados']

                    # Cria um formato de porcentagem (Excel usará a localidade para ponto/vírgula)
                    percent_format = workbook.add_format({'num_format': '0.00%', 'align': 'center'})
                    
                    # Encontra o índice da coluna 'Absenteísmo' no DataFrame que será exportado
                    absenteismo_col_idx = df_to_export.columns.get_loc('Absenteísmo')
                    
                    # Aplica o formato à coluna de Absenteísmo no Excel
                    worksheet.set_column(absenteismo_col_idx, absenteismo_col_idx, None, percent_format)

                processed_data = output.getvalue()

                st.download_button(
                    label="📥 Baixar como Excel",
                    data=processed_data,
                    file_name="dados_consolidados_absenteismo.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )


        except Exception as e:
            st.error(f"❌ Erro ao carregar dados de absenteísmo: {e}")

    # Página: Custos Médicos (agora para visualização, não upload)
    elif pagina == "Custos Médicos":
        st.header("💸 Visualização e Análise de Custos Médicos - Contratos")
        
        try:
            # Tenta ler os dados da tabela de contratos
            df_contratos = pd.read_sql_table('contratos', con=engine)
            
            if df_contratos.empty:
                st.warning("Nenhum dado de contrato encontrado. Por favor, faça o upload dos dados na página 'Uploads'.")
            else:
                st.subheader("Dados dos Contratos Ativos")
                
                # Exibir um dataframe com os dados dos contratos
                st.dataframe(df_contratos, use_container_width=True)

                # Você pode adicionar filtros e gráficos para analisar os custos aqui
                st.subheader("Análise de Custos (Em Desenvolvimento)")
                st.info("Funcionalidades adicionais para análise de custos serão implementadas aqui.")

        except Exception as e:
            st.error(f"❌ Erro ao carregar os dados de contratos: {e}")
            st.info("Verifique se a tabela 'contratos' existe no banco de dados. Se não existir, faça o upload de um arquivo de contratos na página 'Uploads'.")
    
    # Nova Página: CDR
    elif pagina == "CDR":
        st.header("🗺️ Mapa de Dados de CDR por Município")

        try:
            df_cdr = pd.read_sql_table('cdr', con=engine)

            if df_cdr.empty:
                st.warning("Nenhum dado de CDR encontrado. Por favor, faça o upload dos dados na página 'Uploads'.")
            else:
                # Carregar dados GeoJSON para o mapa usando a função cacheada
                geojson_data = load_geojson("geojs-35-mun.json")

                if geojson_data:
                    # Assumindo que 'Valor' no df_cdr representa a quantidade de pacientes ou uma métrica similar
                    # Se 'Valor' não for a quantidade de pacientes, você precisará agrupar e contar aqui.
                    # Exemplo: df_cdr_grouped = df_cdr.groupby('Município').size().reset_index(name='Quantidade_Pacientes')
                    # E então usar 'Quantidade_Pacientes' no `color` do px.choropleth

                    # Obter lista de municípios para o filtro
                    municipios_disponiveis = sorted(df_cdr['Município'].unique())
                    
                    st.sidebar.subheader("🔎 Filtro de Município (CDR)")
                    # Adicionar um seletor para filtrar por município
                    selected_municipio = st.sidebar.selectbox(
                        "Selecione um Município para filtrar a tabela:",
                        ['Todos'] + municipios_disponiveis,
                        key="cdr_municipio_filter"
                    )

                    df_cdr_filtered = df_cdr.copy()
                    if selected_municipio != 'Todos':
                        df_cdr_filtered = df_cdr_filtered[df_cdr_filtered['Município'] == selected_municipio]
                        st.subheader(f"Dados de CDR para: {selected_municipio}")
                    else:
                        st.subheader("Dados de CDR por Município")

                    st.dataframe(df_cdr_filtered, use_container_width=True)

                    # Criar o mapa coroplético
                    fig_map = px.choropleth(
                        df_cdr, # Usar o DataFrame completo para o mapa, para mostrar todos os municípios
                        geojson=geojson_data,
                        locations='Município', # Coluna no df_cdr que contém os nomes dos municípios
                        featureidkey="properties.name", # Propriedade no GeoJSON que corresponde aos nomes dos municípios
                        color='Valor', # Coluna no df_cdr para colorir o mapa (assumindo quantidade de pacientes ou métrica)
                        color_continuous_scale="Viridis", # Escala de cores
                        scope="south america", # Define o escopo do mapa (pode ser "brazil" se tiver um GeoJSON do Brasil)
                        title="Distribuição de Valores por Município (CDR)",
                        hover_name="Município",
                        hover_data={"Valor": True}
                    )
                    
                    fig_map.update_geos(fitbounds="locations", visible=False) # Ajusta o zoom para os municípios presentes
                    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}) # Remove margens

                    st.plotly_chart(fig_map, use_container_width=True)
                else:
                    st.warning("Não foi possível carregar o GeoJSON, o mapa não será exibido.")

        except Exception as e:
            st.error(f"❌ Erro ao carregar ou exibir o mapa de CDR: {e}")
            st.info("Certifique-se de que o arquivo CSV de CDR contém a coluna 'Município' e que os nomes dos municípios correspondem aos dados do GeoJSON.")
            st.info("Para um mapa coroplético funcional, você precisará de um arquivo GeoJSON com as geometrias dos municípios brasileiros. Um exemplo pode ser encontrado buscando por 'geojson municípios Brasil'.")

