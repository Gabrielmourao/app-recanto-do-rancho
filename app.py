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

# Inicia a tabela de usuários e cria a conta do Síndico se não existir
def inicializar_banco():
    executar_sql('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        casa TEXT NOT NULL,
        senha TEXT NOT NULL,
        perfil TEXT NOT NULL
    )
    ''')
    
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

if st.session_state['usuario_logado'] is None:
    st.title("🔐 Portal Recanto do Rancho")
    
    # Cria abas para separar o Login do Cadastro
    aba_login, aba_cadastro = st.tabs(["Entrar", "Cadastrar Novo Morador"])
    
    with aba_login:
        st.subheader("Acesse sua conta")
        email_login = st.text_input("E-mail")
        senha_login = st.text_input("Senha", type="password")
        
        if st.button("Entrar", key="btn_login"):
            usuario = buscar_dados("SELECT * FROM usuarios WHERE email=? AND senha=?", (email_login, senha_login))
            if usuario:
                st.session_state['usuario_logado'] = usuario[0] # Guarda todos os dados da pessoa na memória
                st.rerun()
            else:
                st.error("E-mail ou senha incorretos.")
                
    with aba_cadastro:
        st.subheader("Crie seu acesso")
        nome_cad = st.text_input("Nome Completo")
        email_cad = st.text_input("E-mail Pessoal")
        casa_cad = st.text_input("Número da Casa/Apt")
        senha_cad = st.text_input("Crie uma Senha", type="password")
        
        if st.button("Criar Conta", key="btn_cad"):
            if nome_cad and email_cad and casa_cad and senha_cad:
                # Verifica se o e-mail já existe no banco
                existe = buscar_dados("SELECT * FROM usuarios WHERE email=?", (email_cad,))
                if existe:
                    st.warning("Este e-mail já está cadastrado. Tente fazer login.")
                else:
                    executar_sql("INSERT INTO usuarios (nome, email, casa, senha, perfil) VALUES (?, ?, ?, ?, ?)",
                                 (nome_cad, email_cad, casa_cad, senha_cad, "Morador"))
                    st.success("Conta criada com sucesso! Agora você pode fazer o login ao lado.")
            else:
                st.warning("Por favor, preencha todos os campos para se cadastrar.")

# ==========================================
# 3. O APLICATIVO (Área Logada)
# ==========================================
else:
    user = st.session_state['usuario_logado'] # Atalho para saber quem está navegando
    
    st.sidebar.success(f"👤 Olá, **{user['nome']}**\n\n🏠 Casa: {user['casa']}")
    if st.sidebar.button("Sair (Logout)"):
        st.session_state['usuario_logado'] = None
        st.rerun()
        
    st.sidebar.divider()

    # Menu Lateral
    st.sidebar.title("Navegação")
    menu = st.sidebar.selectbox(
        "Escolha uma página:", 
        ["Página Inicial", "Comunicados", "Reservas", "Assembleias", "Prestação de Contas"]
    )

    # --- PÁGINA INICIAL ---
    if menu == "Página Inicial":
        st.title("🏢 Condomínio Recanto do Rancho")
        st.write("Bem-vindo ao sistema integrado de gestão.")

    # --- COMUNICADOS ---
    elif menu == "Comunicados":
        st.title("📢 Mural de Comunicados")
        
        if user['perfil'] == "Síndico":
            with st.expander("➕ Publicar Novo Comunicado"):
                tit_aviso = st.text_input("Título do Comunicado")
                msg_aviso = st.text_area("Assunto / Mensagem")
                if st.button("Publicar no Mural"):
                    if tit_aviso:
                        data_hoje = datetime.datetime.now().strftime("%d/%m/%Y")
                        executar_sql("INSERT INTO comunicados (titulo, mensagem, data_publicacao) VALUES (?, ?, ?)", 
                                     (tit_aviso, msg_aviso, data_hoje))
                        st.success("Comunicado publicado!")
                        st.rerun()
            st.divider()

        avisos = buscar_dados("SELECT * FROM comunicados ORDER BY id DESC")
        for aviso in avisos:
            st.subheader(f"📌 {aviso['titulo']}")
            st.caption(f"Publicado em: {aviso['data_publicacao']}")
            st.write(aviso['mensagem'])
            st.divider()

        assembleias = buscar_dados("SELECT * FROM assembleias WHERE status='Agendada'")
        for assembleia in assembleias:
            st.subheader("🚨 CONVOCAÇÃO DE ASSEMBLEIA")
            st.info(f"📅 Data: {assembleia['data_completa']} | 📍 Local: {assembleia['local']}")
            st.write(f"**Pauta:** {assembleia['pauta']}")
            st.divider()

    # --- RESERVAS ---
    elif menu == "Reservas":
        st.title("📅 Reservas da Churrasqueira 🥩")
        
        # Puxa todas as reservas gerais do banco para fazer a verificação do calendário
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
            
            # FILTRO MÁGICO: Busca no banco apenas as reservas da casa do usuário logado!
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
            
            data_escolhida = st.date_input("Selecione a data para verificar disponibilidade:")
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
                    # Agora o sistema puxa o nome e casa direto do perfil logado, sem precisar digitar
                    executar_sql("INSERT INTO reservas (nome, casa, data_reserva, status) VALUES (?, ?, ?, ?)", 
                                 (user['nome'], user['casa'], data_str, "Aguardando Aprovação"))
                    st.success("Solicitação enviada!")
                    st.rerun()

    # --- ASSEMBLEIAS ---
    elif menu == "Assembleias":
        st.title("🤝 Assembleias")
        
        assembleias = buscar_dados("SELECT * FROM assembleias WHERE status='Agendada'")
        atas = buscar_dados("SELECT * FROM atas ORDER BY id DESC")
        
        if user['perfil'] == "Síndico":
            with st.expander("➕ Agendar Nova Assembleia"):
                col1, col2 = st.columns(2)
                with col1: data_reuniao = st.date_input("Data da Assembleia")
                with col2: hora_reuniao = st.time_input("Horário da Assembleia")
                novo_local = st.text_input("Local")
                nova_pauta = st.text_area("Pauta Principal")
                
                if st.button("Agendar e Avisar Moradores"):
                    data_str = data_reuniao.strftime("%d/%m/%Y")
                    hora_str = hora_reuniao.strftime("%H:%M")
                    mes_ano_formatado = f"{MESES_PT[data_reuniao.month]}/{data_reuniao.year}"
                    data_completa = f"{data_str} às {hora_str}"
                    
                    executar_sql("INSERT INTO assembleias (data_completa, mes_ano, local, pauta) VALUES (?, ?, ?, ?)",
                                 (data_completa, mes_ano_formatado, novo_local, nova_pauta))
                    st.success("Assembleia agendada!")
                    st.rerun()
            
            with st.expander("📂 Publicar Ata Finalizada"):
                if not assembleias:
                    st.warning("Não há assembleias aguardando ata.")
                else:
                    opcoes = {f"{a['data_completa']} - {a['pauta']}": a for a in assembleias}
                    escolha = st.selectbox("Selecione a assembleia:", list(opcoes.keys()))
                    arquivo_ata = st.file_uploader("Selecione o PDF", type=["pdf"], key="up_ata")
                    
                    if st.button("Publicar Ata"):
                        if arquivo_ata:
                            ass = opcoes[escolha]
                            with open(os.path.join("uploads", arquivo_ata.name), "wb") as f:
                                f.write(arquivo_ata.getbuffer())
                            executar_sql("INSERT INTO atas (mes_ano, data_completa, pauta, nome_arquivo) VALUES (?, ?, ?, ?)",
                                         (ass['mes_ano'], ass['data_completa'], ass['pauta'], arquivo_ata.name))
                            executar_sql("UPDATE assembleias SET status='Concluida' WHERE id=?", (ass['id'],))
                            st.rerun()
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
                        col_btn1.download_button(
                            label=f"📄 Baixar {ata['nome_arquivo']}", data=file,
                            file_name=ata['nome_arquivo'], mime="application/pdf", key=f"dl_ata_{ata['id']}"
                        )
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
                data_balancete = st.date_input("Mês referente:")
                mes_ano_bal = f"Balancete {MESES_PT[data_balancete.month]}/{data_balancete.year}"
                
                arq_bal = st.file_uploader("Selecione o PDF do Balancete", type=["pdf"], key="up_bal")
                if st.button("Salvar Balancete"):
                    if arq_bal:
                        with open(os.path.join("uploads", arq_bal.name), "wb") as f:
                            f.write(arq_bal.getbuffer())
                        executar_sql("INSERT INTO balancetes (titulo, nome_arquivo) VALUES (?, ?)", (mes_ano_bal, arq_bal.name))
                        st.success("Balancete liberado!")
                        st.rerun()
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
                    col1.download_button(
                        label=f"📄 Baixar {bal['nome_arquivo']}", data=file,
                        file_name=bal['nome_arquivo'], mime="application/pdf", key=f"dl_bal_{bal['id']}"
                    )
            else:
                col1.button("📄 Arquivo perdido", disabled=True, key=f"err_bal_{bal['id']}")
            
            if user['perfil'] == "Síndico":
                if col2.button("🗑️ Excluir para Substituir", key=f"del_bal_{bal['id']}"):
                    executar_sql("DELETE FROM balancetes WHERE id=?", (bal['id'],))
                    st.rerun()
            st.divider()