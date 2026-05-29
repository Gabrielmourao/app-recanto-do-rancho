import streamlit as st
import sqlite3
import datetime
import os

# Configuração da página - Agora a aba lateral inicia recolhida por padrão!
st.set_page_config(page_title="Recanto do Rancho", layout="wide", initial_sidebar_state="collapsed")

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
    
    # NOVAS TABELAS: Multas e Mensagens
    executar_sql('''CREATE TABLE IF NOT EXISTS multas (id INTEGER PRIMARY KEY AUTOINCREMENT, casa TEXT NOT NULL, motivo TEXT NOT NULL, data_aplicacao TEXT NOT NULL, nome_arquivo TEXT NOT NULL)''')
    executar_sql('''CREATE TABLE IF NOT EXISTS mensagens (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, casa TEXT NOT NULL, assunto TEXT NOT NULL, texto TEXT NOT NULL, data_envio TEXT NOT NULL)''')
    
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

# Controle de navegação inteligente
if 'pagina_atual' not in st.session_state:
    st.session_state['pagina_atual'] = "Página Inicial"

def navegar_para(pagina):
    st.session_state['pagina_atual'] = pagina

# ==========================================
# 2. SISTEMA DE LOGIN REAL
# ==========================================
if 'usuario_logado' not in st.session_state:
    st.session_state['usuario_logado'] = None

if 'tela_acesso' not in st.session_state:
    st.session_state['tela_acesso'] = "Login"

if st.session_state['usuario_logado'] is None:
    st.title("🔐 Portal Recanto do Rancho")
    
    escolha_tela = st.radio("Selecione uma opção:", ["Login", "Cadastrar Novo Morador"], horizontal=True)
    
    if escolha_tela != st.session_state['tela_acesso']:
        st.session_state['tela_acesso'] = escolha_tela
        st.rerun()
    
    if st.session_state['tela_acesso'] == "Login":
        st.subheader("Acesse sua conta")
        email_login = st.text_input("E-mail")
        senha_login = st.text_input("Senha", type="password")
        
        if st.button("Entrar"):
            usuario = buscar_dados("SELECT * FROM usuarios WHERE email=? AND senha=?", (email_login, senha_login))
            if usuario:
                st.session_state['usuario_logado'] = usuario[0]
                st.session_state['pagina_atual'] = "Página Inicial" 
                st.rerun()
            else:
                st.error("E-mail ou senha incorretos.")
                
    else: 
        st.subheader("Crie seu acesso")
        nome_cad = st.text_input("Nome Completo")
        email_cad = st.text_input("E-mail Pessoal")
        casa_cad = st.text_input("Número da Casa/Apt")
        senha_cad = st.text_input("Crie uma Senha", type="password")
        
        if st.button("Criar Conta"):
            if nome_cad and email_cad and casa_cad and senha_cad:
                existe = buscar_dados("SELECT * FROM usuarios WHERE email=?", (email_cad,))
                if existe:
                    st.warning("Este e-mail já está cadastrado. Tente fazer login.")
                else:
                    executar_sql("INSERT INTO usuarios (nome, email, casa, senha, perfil) VALUES (?, ?, ?, ?, ?)",
                                 (nome_cad, email_cad, casa_cad, senha_cad, "Morador"))
                    st.success("Conta criada! Redirecionando para o login...")
                    st.session_state['tela_acesso'] = "Login"
                    st.rerun()
            else:
                st.warning("Por favor, preencha todos os campos.")

# ==========================================
# 3. O APLICATIVO (Área Logada)
# ==========================================
else:
    user = st.session_state['usuario_logado'] 
    primeiro_nome = user['nome'].split()[0] 
    
    # Opções do menu baseadas no perfil
    if user['perfil'] == "Síndico":
        opcoes_menu = ["Página Inicial", "Comunicados", "Reservas", "Assembleias", "Prestação de Contas", "Moradores", "Multas", "Mensagens"]
    else:
        opcoes_menu = ["Página Inicial", "Comunicados", "Reservas", "Assembleias", "Prestação de Contas", "Falar com o Síndico", "Minhas Multas"]

    st.sidebar.success(f"👤 Olá, **{primeiro_nome}**\n\n🏠 Casa: {user['casa']}")
    
    # Menu Lateral sincronizado com a navegação
    menu = st.sidebar.radio("Navegação Lateral:", opcoes_menu, index=opcoes_menu.index(st.session_state['pagina_atual']))
    
    if menu != st.session_state['pagina_atual']:
        st.session_state['pagina_atual'] = menu
        st.rerun()
        
    st.sidebar.divider()
    if st.sidebar.button("Sair (Logout)"):
        st.session_state['usuario_logado'] = None
        st.rerun()

    pagina = st.session_state['pagina_atual']

    # --- PÁGINA INICIAL ---
    if pagina == "Página Inicial":
        st.title(f"🏢 Olá, {primeiro_nome}! Bem-vindo(a).")
        st.write("Acesse rapidamente os serviços do condomínio:")
        
        # ÍCONES DE NAVEGAÇÃO NA TELA INICIAL
        col1, col2, col3, col4 = st.columns(4)
        if col1.button("📢 Comunicados", use_container_width=True): navegar_para("Comunicados"); st.rerun()
        if col2.button("📅 Reservas", use_container_width=True): navegar_para("Reservas"); st.rerun()
        if col3.button("🤝 Assembleias", use_container_width=True): navegar_para("Assembleias"); st.rerun()
        if col4.button("📊 Contas", use_container_width=True): navegar_para("Prestação de Contas"); st.rerun()

        st.divider()
        st.subheader("📢 Últimos Avisos e Eventos")
        
        # Junta Avisos e Assembleias na página inicial
        ultimos_avisos = buscar_dados("SELECT * FROM comunicados ORDER BY id DESC LIMIT 3")
        assembleias_agendadas = buscar_dados("SELECT * FROM assembleias WHERE status='Agendada' ORDER BY id DESC LIMIT 2")
        
        if not ultimos_avisos and not assembleias_agendadas:
            st.info("Nenhuma novidade no momento.")
        
        for ass in assembleias_agendadas:
            st.warning(f"🚨 **CONVOCAÇÃO DE ASSEMBLEIA** - {ass['data_completa']}\n\n**Local:** {ass['local']} | **Pauta:** {ass['pauta']}")
            
        for aviso in ultimos_avisos:
            st.markdown(f"**📌 {aviso['titulo']}** *(Publicado em: {aviso['data_publicacao']})*")
            st.write(aviso['mensagem'])
            st.divider()

    # --- COMUNICADOS ---
    elif pagina == "Comunicados":
        st.title("📢 Mural de Comunicados")
        
        if user['perfil'] == "Síndico":
            with st.expander("➕ Publicar Novo Comunicado"):
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
                            st.rerun()
                        else:
                            st.warning("Preencha título e mensagem.")
            st.divider()

        assembleias_agendadas = buscar_dados("SELECT * FROM assembleias WHERE status='Agendada'")
        for ass in assembleias_agendadas:
            st.warning(f"🚨 **CONVOCAÇÃO DE ASSEMBLEIA** - {ass['data_completa']}\n\n**Local:** {ass['local']} | **Pauta:** {ass['pauta']}")

        avisos = buscar_dados("SELECT * FROM comunicados ORDER BY id DESC")
        if not avisos:
            st.write("Nenhum comunicado no mural.")
        for aviso in avisos:
            st.markdown(f"### 📌 {aviso['titulo']}")
            st.caption(f"Publicado em: {aviso['data_publicacao']}")
            st.write(aviso['mensagem'])
            st.divider()

    # --- RESERVAS ---
    elif pagina == "Reservas":
        st.title("📅 Reservas da Churrasqueira")
        reservas_gerais = buscar_dados("SELECT * FROM reservas ORDER BY id DESC")
        
        if user['perfil'] == "Síndico":
            st.subheader("Painel de Solicitações")
            pendentes = [r for r in reservas_gerais if r['status'] == "Aguardando Aprovação"]
            if not pendentes:
                st.write("Nenhuma solicitação aguardando análise.")
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
            
            st.subheader("Histórico de Reservas")
            for r in reservas_gerais:
                st.write(f"**{r['data_reserva']}** | {r['nome']} (Casa {r['casa']}) | Status: {r['status']}")

        else: # Morador
            st.subheader("Minhas Solicitações")
            minhas_reservas = buscar_dados("SELECT * FROM reservas WHERE casa=? ORDER BY id DESC", (user['casa'],))
            
            if not minhas_reservas:
                st.write("Você não tem solicitações.")
            for r in minhas_reservas:
                if r['status'] == "Aprovada":
                    st.success(f"📅 {r['data_reserva']} | APROVADA - Boa festa!")
                elif r['status'] == "Reprovada":
                    st.error(f"📅 {r['data_reserva']} | REPROVADA - Fale com o síndico.")
                else:
                    st.warning(f"📅 {r['data_reserva']} | AGUARDANDO APROVAÇÃO")
            
            st.divider()
            st.subheader("Nova Solicitação")
            data_escolhida = st.date_input("Selecione a data no calendário:", value=None)
            
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
                    st.info("✅ Data disponível!")
                    if st.button("Confirmar Reserva"):
                        executar_sql("INSERT INTO reservas (nome, casa, data_reserva, status) VALUES (?, ?, ?, ?)", 
                                     (user['nome'], user['casa'], data_str, "Aguardando Aprovação"))
                        st.success("Enviado!")
                        st.rerun()

    # --- ASSEMBLEIAS ---
    elif pagina == "Assembleias":
        st.title("🤝 Assembleias")
        assembleias = buscar_dados("SELECT * FROM assembleias WHERE status='Agendada'")
        atas = buscar_dados("SELECT * FROM atas ORDER BY id DESC")
        
        if user['perfil'] == "Síndico":
            with st.expander("➕ Agendar Nova Assembleia"):
                with st.form("form_assembleia", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    data_reuniao = col1.date_input("Data", value=None)
                    hora_reuniao = col2.time_input("Horário", value=None)
                    novo_local = st.text_input("Local")
                    nova_pauta = st.text_area("Pauta Principal")
                    
                    if st.form_submit_button("Agendar Assembleia"):
                        if data_reuniao and hora_reuniao and novo_local and nova_pauta:
                            data_str = data_reuniao.strftime("%d/%m/%Y")
                            hora_str = hora_reuniao.strftime("%H:%M")
                            mes_ano_formatado = f"{MESES_PT[data_reuniao.month]}/{data_reuniao.year}"
                            data_completa = f"{data_str} às {hora_str}"
                            executar_sql("INSERT INTO assembleias (data_completa, mes_ano, local, pauta) VALUES (?, ?, ?, ?)",
                                         (data_completa, mes_ano_formatado, novo_local, nova_pauta))
                            st.success("Agendada!")
                            st.rerun()
                        else:
                            st.warning("Preencha todos os campos.")
            
            with st.expander("📂 Publicar Ata"):
                if not assembleias:
                    st.warning("Nenhuma assembleia aguardando ata.")
                else:
                    with st.form("form_ata", clear_on_submit=True):
                        opcoes = {f"{a['data_completa']} - {a['pauta']}": a for a in assembleias}
                        escolha = st.selectbox("Selecione a assembleia:", list(opcoes.keys()))
                        arquivo_ata = st.file_uploader("PDF da Ata", type=["pdf"])
                        
                        if st.form_submit_button("Publicar Ata"):
                            if arquivo_ata:
                                ass = opcoes[escolha]
                                with open(os.path.join("uploads", arquivo_ata.name), "wb") as f:
                                    f.write(arquivo_ata.getbuffer())
                                executar_sql("INSERT INTO atas (mes_ano, data_completa, pauta, nome_arquivo) VALUES (?, ?, ?, ?)",
                                             (ass['mes_ano'], ass['data_completa'], ass['pauta'], arquivo_ata.name))
                                executar_sql("UPDATE assembleias SET status='Concluida' WHERE id=?", (ass['id'],))
                                st.rerun()
                            else:
                                st.error("Anexe o PDF.")
            st.divider()

        st.subheader("Histórico de Atas")
        for ata in atas:
            with st.expander(f"📌 {ata['mes_ano']} - {ata['pauta'][:30]}..."):
                st.write(f"**Data:** {ata['data_completa']} | **Pauta:** {ata['pauta']}")
                col1, col2 = st.columns(2)
                caminho = os.path.join("uploads", ata['nome_arquivo'])
                if os.path.exists(caminho):
                    with open(caminho, "rb") as f:
                        col1.download_button("📄 Baixar Ata", data=f, file_name=ata['nome_arquivo'], mime="application/pdf", key=f"d_ata_{ata['id']}")
                if user['perfil'] == "Síndico" and col2.button("🗑️ Excluir", key=f"x_ata_{ata['id']}"):
                    executar_sql("DELETE FROM atas WHERE id=?", (ata['id'],))
                    st.rerun()

    # --- PRESTAÇÃO DE CONTAS ---
    elif pagina == "Prestação de Contas":
        st.title("📊 Balancetes Mensais")
        balancetes = buscar_dados("SELECT * FROM balancetes ORDER BY id DESC")
        
        if user['perfil'] == "Síndico":
            with st.expander("📂 Novo Balancete"):
                with st.form("form_balancete", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    mes_sel = col1.selectbox("Mês:", list(MESES_PT.values()))
                    ano_sel = col2.selectbox("Ano:", [2024, 2025, 2026, 2027])
                    arq_bal = st.file_uploader("PDF do Balancete", type=["pdf"])
                    
                    if st.form_submit_button("Salvar Balancete") and arq_bal:
                        titulo = f"Balancete {mes_sel}/{ano_sel}"
                        with open(os.path.join("uploads", arq_bal.name), "wb") as f:
                            f.write(arq_bal.getbuffer())
                        executar_sql("INSERT INTO balancetes (titulo, nome_arquivo) VALUES (?, ?)", (titulo, arq_bal.name))
                        st.rerun()
            st.divider()
            
        for bal in balancetes:
            st.write(f"**{bal['titulo']}**")
            col1, col2 = st.columns(2)
            caminho = os.path.join("uploads", bal['nome_arquivo'])
            if os.path.exists(caminho):
                with open(caminho, "rb") as f:
                    col1.download_button("📄 Baixar", data=f, file_name=bal['nome_arquivo'], mime="application/pdf", key=f"d_bal_{bal['id']}")
            if user['perfil'] == "Síndico" and col2.button("🗑️ Excluir", key=f"x_bal_{bal['id']}"):
                executar_sql("DELETE FROM balancetes WHERE id=?", (bal['id'],))
                st.rerun()
            st.divider()

    # --- MORADORES E MENSAGENS (MÓDULOS NOVOS) ---

    elif pagina == "Falar com o Síndico":
        st.title("✉️ Fale com a Administração")
        st.write("Envie dúvidas, sugestões ou reclamações diretas para o síndico.")
        with st.form("form_msg", clear_on_submit=True):
            assunto = st.text_input("Assunto")
            texto = st.text_area("Sua mensagem")
            if st.form_submit_button("Enviar Mensagem"):
                if assunto and texto:
                    hoje = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")
                    executar_sql("INSERT INTO mensagens (nome, casa, assunto, texto, data_envio) VALUES (?, ?, ?, ?, ?)",
                                 (user['nome'], user['casa'], assunto, texto, hoje))
                    st.success("Mensagem enviada com sucesso! O síndico entrará em contato em breve.")
                else:
                    st.warning("Preencha o assunto e a mensagem.")

    elif pagina == "Mensagens":
        st.title("📥 Caixa de Mensagens")
        mensagens = buscar_dados("SELECT * FROM mensagens ORDER BY id DESC")
        if not mensagens:
            st.info("Sua caixa de entrada está vazia.")
        for msg in mensagens:
            with st.expander(f"✉️ {msg['assunto']} - Casa {msg['casa']}"):
                st.caption(f"Enviado por {msg['nome']} em {msg['data_envio']}")
                st.write(msg['texto'])
                if st.button("🗑️ Arquivar / Apagar Mensagem", key=f"x_msg_{msg['id']}"):
                    executar_sql("DELETE FROM mensagens WHERE id=?", (msg['id'],))
                    st.rerun()

    elif pagina == "Moradores":
        st.title("👥 Gestão de Moradores")
        st.write("Controle os acessos ao aplicativo.")
        moradores = buscar_dados("SELECT * FROM usuarios WHERE perfil='Morador' ORDER BY casa ASC")
        
        if not moradores:
            st.write("Nenhum morador cadastrado.")
        for m in moradores:
            with st.container():
                col1, col2 = st.columns([3, 1])
                col1.write(f"🏠 **Casa {m['casa']}** - {m['nome']} ({m['email']})")
                if col2.button("🗑️ Excluir Acesso", key=f"x_user_{m['id']}"):
                    executar_sql("DELETE FROM usuarios WHERE id=?", (m['id'],))
                    st.rerun()
                st.divider()

    elif pagina == "Multas" or pagina == "Minhas Multas":
        st.title("🛑 Infrações e Multas")
        
        if user['perfil'] == "Síndico":
            moradores = buscar_dados("SELECT * FROM usuarios WHERE perfil='Morador'")
            with st.expander("➕ Aplicar Nova Multa"):
                if not moradores:
                    st.warning("Cadastre moradores primeiro.")
                else:
                    with st.form("form_multa", clear_on_submit=True):
                        opcoes_casas = [f"Casa {m['casa']} - {m['nome']}" for m in moradores]
                        infrator = st.selectbox("Selecione o Infrator:", opcoes_casas)
                        motivo = st.text_input("Motivo da Multa (Resumo):")
                        arq_multa = st.file_uploader("Anexar Documento/Boleto da Multa (PDF)", type=["pdf"])
                        
                        if st.form_submit_button("Aplicar Multa e Notificar"):
                            if infrator and motivo and arq_multa:
                                # Extrai apenas o número da casa da string selecionada (Ex: "Casa 12 - João" -> "12")
                                num_casa = infrator.split(" - ")[0].replace("Casa ", "")
                                hoje = datetime.datetime.now().strftime("%d/%m/%Y")
                                
                                with open(os.path.join("uploads", arq_multa.name), "wb") as f:
                                    f.write(arq_multa.getbuffer())
                                    
                                executar_sql("INSERT INTO multas (casa, motivo, data_aplicacao, nome_arquivo) VALUES (?, ?, ?, ?)",
                                             (num_casa, motivo, hoje, arq_multa.name))
                                st.success(f"Multa aplicada para a Casa {num_casa}!")
                                st.rerun()
                            else:
                                st.warning("Preencha todos os campos e anexe o PDF.")
            
            st.subheader("Histórico Geral de Multas")
            todas_multas = buscar_dados("SELECT * FROM multas ORDER BY id DESC")
            if not todas_multas:
                st.write("Nenhuma multa registrada.")
            for m in todas_multas:
                st.write(f"🏠 **Casa {m['casa']}** | {m['data_aplicacao']} - {m['motivo']}")
                col1, col2 = st.columns(2)
                caminho = os.path.join("uploads", m['nome_arquivo'])
                if os.path.exists(caminho):
                    with open(caminho, "rb") as f:
                        col1.download_button("📄 Baixar Documento", data=f, file_name=m['nome_arquivo'], mime="application/pdf", key=f"d_multa_{m['id']}")
                if col2.button("🗑️ Cancelar Multa", key=f"x_multa_{m['id']}"):
                    executar_sql("DELETE FROM multas WHERE id=?", (m['id'],))
                    st.rerun()
                st.divider()

        else: # Morador visualiza apenas suas multas
            st.write("Consulte abaixo se há pendências ou infrações vinculadas à sua unidade.")
            minhas_multas = buscar_dados("SELECT * FROM multas WHERE casa=? ORDER BY id DESC", (user['casa'],))
            
            if not minhas_multas:
                st.success("🎉 Parabéns! Nenhuma multa registrada para a sua casa.")
            else:
                for m in minhas_multas:
                    st.error(f"⚠️ **Notificação de Multa:** {m['motivo']}")
                    st.caption(f"Aplicada em: {m['data_aplicacao']}")
                    caminho = os.path.join("uploads", m['nome_arquivo'])
                    if os.path.exists(caminho):
                        with open(caminho, "rb") as f:
                            st.download_button("📄 Baixar Documento / Boleto", data=f, file_name=m['nome_arquivo'], mime="application/pdf", key=f"d_minhamulta_{m['id']}")
                    st.divider()