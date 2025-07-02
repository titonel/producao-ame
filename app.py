import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import openpyxl
import plotly.express as px
from io import BytesIO

# --- Gestão de Usuários (para demonstração, use um método seguro em produção) ---
USERS = {
    "ame_user": "ame_password",  # Substitua por uma forma segura de armazenar/recuperar credenciais
    "admin": "admin_password"
}

def authenticate(username, password):
    """
    Função para autenticar o usuário.
    Em uma aplicação real, você verificaria em um banco de dados com senhas hash.
    """
    if username in USERS and USERS[username] == password:
        return True
    return False

# --- Funções Auxiliares para Normalização de Especialidades ---
def normalizar_especialidade(nome):
    """Normaliza nomes de especialidades para agrupamento."""
    nome = str(nome).upper().strip()
    if nome.startswith("CIRURGIA PLÁSTICA"):
        return "Cirurgia Plástica"
    elif nome.startswith("OFTALMOLOGIA"):
        return "Oftalmologia"
    elif nome.startswith("CARDIOLOGIA"):
        return "Cardiologia"
    elif nome.startswith("DERMATOLOGIA"):
        return "Dermatologia"
    elif nome.startswith("ANESTESIOLOGIA"):
        return "Anestesiologia"
    elif nome.startswith("CIRURGIA VASCULAR"):
        return "Cirurgia Vascular"
    elif nome.startswith("COLOPROCTOLOGIA"):
        return "Coloproctologia"
    elif nome.startswith("GASTROCLÍNICA") or nome.startswith("GASTROENTEROLOGIA"):
        return "Gastroenterologia"
    elif nome.startswith("MASTOLOGIA"):
        return "Mastologia"
    elif nome.startswith("ORTOPEDIA"):
        return "Ortopedia"
    elif nome.startswith("OTORRINOLARINGOLOGIA"):
        return "Otorrinolaringologia"    
    elif nome.startswith("UROLOGIA"):
        return "Urologia"
    elif nome.startswith("ENDOCRINOLOGIA"):
        return "Endocrinologia"
    elif nome.startswith("CIRURGIA PEDIÁTRICA"):
        return "Cirurgia Pediátrica"
    elif nome.startswith("NEUROLOGIA PEDIÁTRICA"):
        return "Neurologia Pediátrica"
    elif nome.startswith("NEUROLOGIA"):
        return "Neurologia Adulto"
    elif nome.startswith("PNEUMOLOGIA PEDIÁTRICA"):
        return "Pneumologia Pediátrica"
    elif nome.startswith("PNEUMOLOGIA"):
        return "Pneumologia Adulto"    
    elif nome.startswith("NEFROLOGIA"):
        return "Nefrologia"
    elif nome.startswith("CIRURGIA GERAL"):
        return "Cirurgia Geral"
    # Adicione outras regras conforme necessário ou retorne o próprio nome se não houver correspondência
    return nome

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
    pagina = st.sidebar.radio("Escolha a opção:", ["Performance", "Dados Gerais", "Inserir Dados", "Absenteísmo"])
    
    # Botão de Sair na barra lateral
    st.sidebar.markdown("---")
    if st.sidebar.button("Sair", key="logout_button"):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.rerun() # Recarrega a página para voltar à tela de login

    # Conexão com o banco SQLite
    engine = create_engine('sqlite:///producao.db')

    # Página: INSERIR DADOS
    if pagina == "Inserir Dados":
        st.header("📥 Inserir Dados da Produção")
        uploaded_file = st.file_uploader("Selecione o arquivo .xlsx exportado do SIRESP", type=["xlsx"])

        if uploaded_file:
            try:
                # Carregar workbook
                wb = openpyxl.load_workbook(BytesIO(uploaded_file.read()), data_only=True)
                ws = wb.active

                # Extrair metadados
                tipo_consulta = ws['A3'].value
                data_producao = ws['F3'].value
                mes_producao, ano_producao = map(str.strip, data_producao.split('de'))

                # Reabrir para leitura com pandas
                uploaded_file.seek(0)
                df = pd.read_excel(uploaded_file, skiprows=6)

                # Manter apenas colunas A-D
                df = df.iloc[:, :4]
                df.columns = ['Especialidade', 'Oferta', 'Agendados', 'Realizados']

                # Remover linhas inválidas
                df = df[df['Oferta'].notna()]
                df = df[df['Oferta'].astype(str).str.lower() != 'total']

                # Adicionar colunas auxiliares
                df['Tipo_Consulta'] = tipo_consulta
                df['Mes_Producao'] = mes_producao.capitalize()
                df['Ano_Producao'] = ano_producao

                # Gravar no banco
                df.to_sql('producao', con=engine, if_exists='append', index=False)

                st.success("✅ Dados inseridos com sucesso!")
                st.subheader("📄 Visualização dos Dados Inseridos")
                st.dataframe(df)

            except Exception as e:
                st.error(f"❌ Erro ao processar o arquivo: {e}")

    # Página: PERFORMANCE
    elif pagina == "Performance":
        st.header("📈 Performance das Agendas Médicas")
        
        try:
            df = pd.read_sql_table('producao', con=engine)

            # Converter mês para número (para ordenar corretamente)
            df['Mes_Producao'] = df['Mes_Producao'].astype(str).str.lower()
            df['Mes_Num'] = df['Mes_Producao'].apply(lambda x: meses_ordem.index(x) + 1 if x in meses_ordem else 0)

            # Filtros
            anos = sorted(df['Ano_Producao'].unique())
            meses = sorted(df['Mes_Producao'].unique(), key=lambda x: meses_ordem.index(x))
            tipos = sorted(df['Tipo_Consulta'].dropna().unique())

            st.sidebar.subheader("🔎 Filtros de Performance")
            ano_filtro = st.sidebar.multiselect("Ano", anos, default=anos, key="perf_ano")
            mes_filtro = st.sidebar.multiselect("Mês", meses, default=meses, key="perf_mes")
            tipo_filtro = st.sidebar.multiselect("Tipo de Consulta", tipos, default=tipos, key="perf_tipo")


            # Aplicar filtros
            df_filtro = df[
                (df['Ano_Producao'].isin(ano_filtro)) &
                (df['Mes_Producao'].isin(mes_filtro)) &
                (df['Tipo_Consulta'].isin(tipo_filtro))
            ]

            if df_filtro.empty:
                st.warning("Nenhum dado encontrado para os filtros selecionados.")
            else:
                # Agrupar por mês/ano/especialidade e somar os realizados
                # Exibe período no formato "mm/yyyy"
                df_filtro['Periodo'] = df_filtro['Mes_Num'].astype(str).str.zfill(2) + '/' + df_filtro['Ano_Producao'].astype(str)
                # Ordenar o DataFrame agrupado pelo período para garantir que o gráfico de linha seja contínuo
                df_agrupado = df_filtro.groupby(['Periodo', 'Especialidade']).agg({'Realizados': 'sum'}).reset_index()
                df_agrupado['OrderPeriod'] = df_agrupado['Periodo'].apply(lambda x: int(x.split('/')[1] + x.split('/')[0]))
                df_agrupado = df_agrupado.sort_values(by='OrderPeriod').drop(columns='OrderPeriod')

                fig = px.line(df_agrupado, x='Periodo', y='Realizados', color='Especialidade',
                              title='Evolução dos Atendimentos por Especialidade',
                              markers=True,
                              labels={'Realizados': 'Atendimentos Realizados', 'Periodo': 'Período (Mês/Ano)'})
                fig.update_xaxes(tickangle=45)

                st.plotly_chart(fig, use_container_width=True)

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
                # Prepara os dados para exibição em tabela, formatando o percentual com vírgula
                df_display = df_grouped_abs.copy()
                df_display['Absenteísmo (%)'] = df_display['Absenteísmo'].astype(str).str.replace('.', ',', regex=False) + '%'
                st.dataframe(df_display[['Ano_Producao', 'Mes_Producao', 'Especialidade_Normalizada', 'Agendados', 'Realizados', 'Absenteísmo (%)']], use_container_width=True)


        except Exception as e:
            st.error(f"❌ Erro ao carregar dados de absenteísmo: {e}")