import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import openpyxl
import plotly.express as px
from io import BytesIO


# Configuração da página
st.set_page_config(page_title="Produção Médica AME", layout="wide")
st.title("📊 AME Caraguatatuba")
st.title("📊 Sistema de Produção Médica")

# Navegação lateral
pagina = st.sidebar.radio("Escolha a opção:", ["Performance", "Dados Gerais", "Inserir Dados"])

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
        meses_ordem = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho',
                       'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
        df['Mes_Producao'] = df['Mes_Producao'].str.lower()
        df['Mes_Num'] = df['Mes_Producao'].apply(lambda x: meses_ordem.index(x) + 1 if x in meses_ordem else 0)

        # Filtros
        anos = sorted(df['Ano_Producao'].unique())
        meses = sorted(df['Mes_Producao'].unique(), key=lambda x: meses_ordem.index(x))
        tipos = sorted(df['Tipo_Consulta'].dropna().unique())

        ano_filtro = st.sidebar.multiselect("Ano", anos, default=anos)
        mes_filtro = st.sidebar.multiselect("Mês", meses, default=meses)
        tipo_filtro = st.sidebar.multiselect("Tipo de Consulta", tipos, default=tipos)

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
            df_agrupado = df_filtro.groupby(['Periodo', 'Especialidade']).agg({'Realizados': 'sum'}).reset_index()

            fig = px.line(df_agrupado, x='Periodo', y='Realizados', color='Especialidade',
                          title='Evolução dos Atendimentos por Especialidade',
                          markers=True)

            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao carregar dados de performance: {e}")

elif pagina == "Dados Gerais":
    st.header("📋 Dados Gerais Consolidados")

    try:
        df = pd.read_sql_table('producao', con=engine)
        # Lista de meses para ordenação correta
        meses_ordem = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
                    'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

        # Remover códigos numéricos iniciais da especialidade
        df['Especialidade'] = df['Especialidade'].astype(str).str.replace(r'^\d+\s*', '', regex=True).str.strip()

        # Normalizar nomes com agrupamento genérico
        def normalizar_especialidade(nome):
            nome = nome.upper().strip()
            if nome.startswith("CIRURGIA PLÁSTICA"):
                return "CIRURGIA PLÁSTICA"
            elif nome.startswith("OFTALMOLOGIA"):
                return "OFTALMOLOGIA"
            elif nome.startswith("CARDIOLOGIA"):
                return "CARDIOLOGIA"
            elif nome.startswith("DERMATOLOGIA"):
                return "DERMATOLOGIA"
            elif nome.startswith("ANESTESIOLOGIA"):
                return "ANESTESIOLOGIA"
            elif nome.startswith("CIRURGIA VASCULAR"):
                return "CIRURGIA VASCULAR"
            elif nome.startswith("COLOPROCTOLOGIA"):
                return "COLOPROCTOLOGIA"
            elif nome.startswith("GASTROCLÍNICA"):
                return "GASTROENTEROLOGIA"
            elif nome.startswith("MASTOLOGIA"):
                return "MASTOLOGIA"
            elif nome.startswith("ORTOPEDIA"):
                return "ORTOPEDIA"
            elif nome.startswith("OTORRINOLARINGOLOGIA"):
                return "OTORRINOLARINGOLOGIA"    
            elif nome.startswith("UROLOGIA"):
                return "UROLOGIA"                                                       
            # adicione outras regras conforme necessário...
            return nome

        df['Especialidade_Normalizada'] = df['Especialidade'].apply(normalizar_especialidade)

        # Filtros
        anos = sorted(df['Ano_Producao'].unique())
        meses = sorted(df['Mes_Producao'].unique(), key=lambda x: meses_ordem.index(x.lower()))

        st.sidebar.subheader("🔎 Filtros")
        ano_filtro = st.sidebar.multiselect("Ano", anos, default=anos)
        mes_filtro = st.sidebar.multiselect("Mês", meses, default=meses)

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
                lambda row: 1 - (row['Realizados'] / row['Agendados']) if row['Agendados'] else 0,
                axis=1
            )

            # Arredondar para 4 casas decimais
            #df_grouped['Absenteísmo'] = df_grouped['Absenteísmo'].round(4)
            df_grouped['Absenteísmo (%)'] = (df_grouped['Absenteísmo'] * 100).round(2).astype(str) + '%'
            
            st.dataframe(df_grouped, use_container_width=True)
            
            # Exportar como Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_grouped.to_excel(writer, index=False, sheet_name='Dados')
                #writer.save()
            processed_data = output.getvalue()

            st.download_button(
                label="📥 Baixar como Excel",
                data=processed_data,
                file_name="dados_consolidados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"❌ Erro ao carregar os dados: {e}")
