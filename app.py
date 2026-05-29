import streamlit as st
import sqlite3
import datetime
import os

# Configuração da página
st.set_page_config(page_title="Recanto do Rancho", layout="wide")

# ==========================================
# 1. BANCO DE DADOS E CONFIGURAÇÕES
# ==========================================
if not os.path.exists("uploads"):
    os.makedirs("uploads")

def get_conexao():
    return sqlite3.connect('condominio.db', check_same_thread=False)

def executar_sql(query, parametros=()):
    conn = get_conexao()
    cursor = conn.cursor()
    cursor.execute(query, parametros)
    conn.commit()
    conn.close()

def buscar_dados(query, parametros=()):
    conn = get_conexao()
    cursor = conn.cursor()
    cursor.execute(query, parametros)
    colunas = [desc[0] for desc in cursor.description]
    resultado = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]
    conn.close()
    return resultado

def inicializar_banco():
    executar_sql('''CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, email TEXT UNIQUE NOT NULL, casa TEXT NOT NULL, senha TEXT NOT NULL, perfil TEXT NOT NULL)''')
    executar_sql('''CREATE TABLE IF NOT EXISTS comunicados (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL, mensagem TEXT NOT NULL, data_publicacao TEXT NOT NULL)''')
    executar_sql('''CREATE TABLE IF NOT EXISTS assembleias (id INTEGER PRIMARY KEY AUTOINCREMENT, data_completa TEXT NOT NULL, mes_ano TEXT NOT NULL, local TEXT NOT NULL, pauta TEXT NOT NULL, status TEXT DEFAULT 'Agendada')''')
    executar_sql('''CREATE TABLE IF NOT EXISTS atas (id INTEGER PRIMARY KEY AUTOINCREMENT, mes_ano TEXT NOT NULL, data_completa TEXT NOT NULL, pauta TEXT NOT NULL, nome_arquivo TEXT NOT NULL)''')
    executar_sql('''CREATE TABLE IF NOT EXISTS reservas (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, casa TEXT NOT NULL, data_reserva TEXT NOT NULL, status TEXT NOT NULL)''')
    executar_sql('''CREATE TABLE IF NOT EXISTS balancetes (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL, nome_arquivo TEXT NOT NULL)''')
    
    sindico_existe = buscar_dados("SELECT * FROM usuarios WHERE perfil='Síndico'")
    if not sindico_existe:
        executar_sql("INSERT INTO usuarios (nome, email, casa, senha, perfil) VALUES (?, ?, ?, ?, ?)",
                     ("Administrador", "sindico@recanto.com", "Sede", "admin123", "Síndico"))

inicializar_banco()

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

# ==========================================
# 2. SISTEMA DE LOGIN REAL
# ==========================================
if 'usuario_logado' not in st.session_state:
    st.session_state['usuario_logado'] = None

# Controle de tela para mudar do Cadastro pro Login automaticamente
if 'tela_acesso' not in st.session_state:
    st.session_state['tela_acesso'] = "Login"

if st.session_state['usuario_logado'] is None:
    st.title("🔐 Portal Recanto do Rancho")
    
    escolha_tela = st.radio("Selecione uma opção:", ["Login", "Cadastrar Novo Morador"], horizontal=True, key="modo_tela")
    
    # Sincroniza a escolha do radio com o session_state
    if escolha_tela != st.session_state['tela_acesso']:
        st.session_state['tela_acesso'] = escolha_tela
        st.rerun()
    
    if st.session_state['tela_acesso'] == "Login":
        st.subheader("Acesse sua conta")
        email_login = st.text_input("E-mail")
        senha_login = st.text_input("Senha", type="password")
        
        if st.button("Entrar", key="btn_login"):
            usuario = buscar_dados("SELECT * FROM usuarios WHERE email=? AND senha=?", (email_login, senha_login))
            if usuario:
                st.session_state['usuario_logado'] = usuario[0] 
                st.rerun()
            else:
                st.error("E-mail ou senha incorretos.")
                
    else: # Cadastro
        st.subheader("Crie seu acesso")
        nome_cad = st.text_input("Nome Completo")
        email_cad = st.text_input("E-mail")
        casa_cad = st.text_input("Número da Casa")
        senha_cad = st.text_input("Crie uma Senha", type="password")
        
        if st.button("Criar Conta", key="btn_cad"):
            if nome_cad and email_cad and casa_cad and senha_cad:
                existe = buscar_dados("SELECT * FROM usuarios WHERE email=?", (email_cad,))
                if existe:
                    st.warning("Este e-mail já está cadastrado. Tente fazer login.")
                else:
                    executar_sql("INSERT INTO usuarios (nome, email, casa, senha, perfil) VALUES (?, ?, ?, ?, ?)",
                                 (nome_cad, email_cad, casa_cad, senha_cad, "Morador"))
                    st.success("Conta criada! Redirecionando para o login...")
                    st.session_state['tela_acesso'] = "Login" # Muda a tela de volta pro login
                    st.rerun()
            else:
                st.warning("Por favor, preencha todos os campos.")

# ==========================================
# 3. O APLICATIVO (Área Logada)
# ==========================================
else:
    user = st.session_state['usuario_logado'] 
    primeiro_nome = user['nome'].split()[0] # Pega apenas o primeiro nome
    
    st.sidebar.success(f"👤 Olá, **{primeiro_nome}**\n\n🏠 Casa: {user['casa']}")
    if st.sidebar.button("Sair (Logout)"):
        st.session_state['usuario_logado'] = None
        st.rerun()
        
    st.sidebar.divider()

    menu = st.sidebar.selectbox(
        "Navegação:", 
        ["Página Inicial", "Comunicados", "Reservas", "Assembleias", "Prestação de Contas"]
    )

    # --- PÁGINA INICIAL ---
    if menu == "Página Inicial":
        st.title("🏢 Condomínio Recanto do Rancho")
        st.write("Bem-vindo ao painel central do seu condomínio.")
        st.divider()
        
        st.subheader("📢 Últimos Avisos")
        # Puxa apenas os 3 mais recentes
        ultimos_avisos = buscar_dados("SELECT * FROM comunicados ORDER BY id DESC LIMIT 3")
        
        if not ultimos_avisos:
            st.info("Nenhum aviso publicado recentemente.")
        else:
            for aviso in ultimos_avisos:
                with st.container():
                    st.markdown(f"**📌 {aviso['titulo']}** *(Publicado em: {aviso['data_publicacao']})*")
                    st.write(aviso['mensagem'])
                    st.divider()

    # --- COMUNICADOS ---
    elif menu == "Comunicados":
        st.title("📢 Mural de Comunicados")
        
        if user['perfil'] == "Síndico":
            with st.expander("➕ Publicar Novo Comunicado"):
                # st.form limpa os campos automaticamente após o envio
                with st.form("form_aviso", clear_on_submit=True):
                    tit_aviso = st.text_input("Título do Comunicado")
                    msg_aviso = st.text_area("Assunto / Mensagem")
                    submit_aviso = st.form_submit_button("Publicar no Mural")
                    
                    if submit_aviso:
                        if tit_aviso and msg_aviso:
                            data_hoje = datetime.datetime.now().strftime("%d/%m/%Y")
                            executar_sql("INSERT INTO comunicados (titulo, mensagem, data_publicacao) VALUES (?, ?, ?)", 
                                         (tit_aviso, msg_aviso, data_hoje))
                            st.success("Comunicado publicado!")
                            st.rerun() # O rerun fecha o expander
                        else:
                            st.warning("Preencha título e mensagem.")
            st.divider()

        st.subheader("Todos os Comunicados")
        avisos = buscar_dados("SELECT * FROM comunicados ORDER BY id DESC")
        if not avisos:
            st.write("Nenhum comunicado no mural.")
        for aviso in avisos:
            st.markdown(f"### 📌 {aviso['titulo']}")
            st.caption(f"Publicado em: {aviso['data_publicacao']}")
            st.write(aviso['mensagem'])
            st.divider()

    # --- RESERVAS ---
    elif menu == "Reservas":
        st.title("📅 Reservas da Churrasqueira 🥩")
        
        reservas_gerais = buscar_dados("SELECT * FROM reservas ORDER BY id DESC")
        
        if user['perfil'] == "Síndico":
            st.subheader("Painel de Solicitações")
            pendentes = [r for r in reservas_gerais if r['status'] == "Aguardando Aprovação"]
            if not pendentes:
                st.write("Nenhuma solicitação aguardando análise.")
            else:
                for r in pendentes:
                    with st.expander(f"Solicitação: {r['data_reserva']} - {r['nome']} (Casa {r['casa']})", expanded=True):
                        col1, col2 = st.columns(2)
                        if col1.button("✅ Aprovar", key=f"apr_{r['id']}"):
                            executar_sql("UPDATE reservas SET status='Aprovada' WHERE id=?", (r['id'],))
                            st.rerun()
                        if col2.button("❌ Reprovar", key=f"rep_{r['id']}"):
                            executar_sql("UPDATE reservas SET status='Reprovada' WHERE id=?", (r['id'],))
                            st.rerun()
            st.divider()
            
            st.subheader("Histórico de Reservas (Geral)")
            if not reservas_gerais:
                st.write("Nenhuma reserva registrada.")
            for r in reservas_gerais:
                st.write(f"**{r['data_reserva']}** | {r['nome']} (Casa {r['casa']}) | Status: {r['status']}")

        else: # VISÃO DO MORADOR
            st.subheader("Minhas Solicitações")
            minhas_reservas = buscar_dados("SELECT * FROM reservas WHERE casa=? ORDER BY id DESC", (user['casa'],))
            
            if not minhas_reservas:
                st.write("Você ainda não fez nenhuma solicitação.")
            else:
                for r in minhas_reservas:
                    if r['status'] == "Aprovada":
                        st.success(f"📅 {r['data_reserva']} | APROVADA - Boa festa!")
                    elif r['status'] == "Reprovada":
                        st.error(f"📅 {r['data_reserva']} | REPROVADA - Fale com o síndico.")
                    else:
                        st.warning(f"📅 {r['data_reserva']} | AGUARDANDO APROVAÇÃO")
            
            st.divider()
            st.subheader("Nova Solicitação")
            
            # value=None deixa o campo em branco por padrão para não mostrar erro antes de clicar
            data_escolhida = st.date_input("Selecione a data para verificar disponibilidade:", value=None)
            
            if data_escolhida:
                data_str = data_escolhida.strftime("%d/%m/%Y")
                
                status_data = None
                for r in reservas_gerais:
                    if r['data_reserva'] == data_str and r['status'] in ["Aguardando Aprovação", "Aprovada"]:
                        status_data = r['status']
                        break 
                
                if status_data == "Aprovada":
                    st.error("⚠️ Já existe uma reserva confirmada para este dia.")
                elif status_data == "Aguardando Aprovação":
                    st.warning("⏳ Esta data já possui uma solicitação aguardando aprovação.")
                else:
                    st.info("✅ Data disponível! Clique abaixo para confirmar.")
                    if st.button("Confirmar Solicitação de Reserva"):
                        executar_sql("INSERT INTO reservas (nome, casa, data_reserva, status) VALUES (?, ?, ?, ?)", 
                                     (user['nome'], user['casa'], data_str, "Aguardando Aprovação"))
                        st.success("Solicitação enviada!")
                        st.rerun()
            else:
                st.caption("👆 Clique no calendário acima para escolher um dia.")

    # --- ASSEMBLEIAS ---
    elif menu == "Assembleias":
        st.title("🤝 Assembleias")
        
        assembleias = buscar_dados("SELECT * FROM assembleias WHERE status='Agendada'")
        atas = buscar_dados("SELECT * FROM atas ORDER BY id DESC")
        
        if user['perfil'] == "Síndico":
            with st.expander("➕ Agendar Nova Assembleia"):
                with st.form("form_assembleia", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    # value=None deixa em branco
                    data_reuniao = col1.date_input("Data da Assembleia", value=None)
                    hora_reuniao = col2.time_input("Horário da Assembleia", value=None)
                    
                    novo_local = st.text_input("Local")
                    nova_pauta = st.text_area("Pauta Principal")
                    submit_ass = st.form_submit_button("Agendar e Avisar Moradores")
                    
                    if submit_ass:
                        if data_reuniao and hora_reuniao and novo_local and nova_pauta:
                            data_str = data_reuniao.strftime("%d/%m/%Y")
                            hora_str = hora_reuniao.strftime("%H:%M")
                            mes_ano_formatado = f"{MESES_PT[data_reuniao.month]}/{data_reuniao.year}"
                            data_completa = f"{data_str} às {hora_str}"
                            
                            executar_sql("INSERT INTO assembleias (data_completa, mes_ano, local, pauta) VALUES (?, ?, ?, ?)",
                                         (data_completa, mes_ano_formatado, novo_local, nova_pauta))
                            st.success("Assembleia agendada!")
                            st.rerun()
                        else:
                            st.warning("Preencha todos os campos, incluindo data e hora.")
            
            with st.expander("📂 Publicar Ata Finalizada"):
                if not assembleias:
                    st.warning("Não há assembleias aguardando ata.")
                else:
                    with st.form("form_ata", clear_on_submit=True):
                        opcoes = {f"{a['data_completa']} - {a['pauta']}": a for a in assembleias}
                        escolha = st.selectbox("Selecione a assembleia:", list(opcoes.keys()))
                        arquivo_ata = st.file_uploader("Selecione o PDF", type=["pdf"])
                        submit_ata = st.form_submit_button("Publicar Ata")
                        
                        if submit_ata:
                            if arquivo_ata:
                                ass = opcoes[escolha]
                                with open(os.path.join("uploads", arquivo_ata.name), "wb") as f:
                                    f.write(arquivo_ata.getbuffer())
                                executar_sql("INSERT INTO atas (mes_ano, data_completa, pauta, nome_arquivo) VALUES (?, ?, ?, ?)",
                                             (ass['mes_ano'], ass['data_completa'], ass['pauta'], arquivo_ata.name))
                                executar_sql("UPDATE assembleias SET status='Concluida' WHERE id=?", (ass['id'],))
                                st.rerun()
                            else:
                                st.error("Anexe o PDF da ata.")
            st.divider()

        st.subheader("Histórico de Assembleias")
        for ata in atas:
            with st.expander(f"📌 Assembleia de {ata['mes_ano']}"):
                st.write(f"**Realizada em:** {ata['data_completa']}")
                st.write(f"**Pauta:** {ata['pauta']}")
                col_btn1, col_btn2 = st.columns(2)
                
                caminho_arquivo = os.path.join("uploads", ata['nome_arquivo'])
                if os.path.exists(caminho_arquivo):
                    with open(caminho_arquivo, "rb") as file:
                        col_btn1.download_button(label=f"📄 Baixar {ata['nome_arquivo']}", data=file, file_name=ata['nome_arquivo'], mime="application/pdf", key=f"dl_ata_{ata['id']}")
                else:
                    col_btn1.button("📄 Arquivo perdido", disabled=True, key=f"err_{ata['id']}")
                
                if user['perfil'] == "Síndico":
                    if col_btn2.button("🗑️ Excluir Ata", key=f"del_ata_{ata['id']}"):
                        executar_sql("DELETE FROM atas WHERE id=?", (ata['id'],))
                        st.rerun()

    # --- PRESTAÇÃO DE CONTAS ---
    elif menu == "Prestação de Contas":
        st.title("📊 Balancetes e Finanças")
        
        balancetes = buscar_dados("SELECT * FROM balancetes ORDER BY id DESC")
        
        if user['perfil'] == "Síndico":
            with st.expander("📂 Enviar Novo Balancete"):
                with st.form("form_balancete", clear_on_submit=True):
                    # Trocado calendário por seletores simples de Mês e Ano
                    col1, col2 = st.columns(2)
                    mes_selecionado = col1.selectbox("Mês Referente:", list(MESES_PT.values()))
                    ano_selecionado = col2.selectbox("Ano Referente:", [2024, 2025, 2026, 2027])
                    
                    arq_bal = st.file_uploader("Selecione o PDF do Balancete", type=["pdf"])
                    submit_bal = st.form_submit_button("Salvar Balancete")
                    
                    if submit_bal:
                        if arq_bal:
                            mes_ano_bal = f"Balancete {mes_selecionado}/{ano_selecionado}"
                            with open(os.path.join("uploads", arq_bal.name), "wb") as f:
                                f.write(arq_bal.getbuffer())
                            executar_sql("INSERT INTO balancetes (titulo, nome_arquivo) VALUES (?, ?)", (mes_ano_bal, arq_bal.name))
                            st.success("Balancete liberado!")
                            st.rerun()
                        else:
                            st.error("Anexe o PDF do balancete.")
            st.divider()
            
        st.subheader("Relatórios Mensais")
        if not balancetes:
            st.write("Nenhum balancete publicado ainda.")
            
        for bal in balancetes:
            st.write(f"**{bal['titulo']}**")
            col1, col2 = st.columns(2)
            
            caminho_arquivo = os.path.join("uploads", bal['nome_arquivo'])
            if os.path.exists(caminho_arquivo):
                with open(caminho_arquivo, "rb") as file:
                    col1.download_button(label=f"📄 Baixar {bal['nome_arquivo']}", data=file, file_name=bal['nome_arquivo'], mime="application/pdf", key=f"dl_bal_{bal['id']}")
            else:
                col1.button("📄 Arquivo perdido", disabled=True, key=f"err_bal_{bal['id']}")
            
            if user['perfil'] == "Síndico":
                if col2.button("🗑️ Excluir", key=f"del_bal_{bal['id']}"):
                    executar_sql("DELETE FROM balancetes WHERE id=?", (bal['id'],))
                    st.rerun()
            st.divider()