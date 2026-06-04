import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading

# Configuração da página
st.set_page_config(page_title="Recanto do Rancho", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# --- FUNÇÕES DE E-MAIL ---
# ==========================================
def disparar_email_background(destinatarios, assunto, corpo_texto, remetente, senha):
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remetente, senha)
        
        lista_dests = destinatarios if isinstance(destinatarios, list) else [destinatarios]
        
        for dest in lista_dests:
            if dest == "sindico@recanto.com" or "@" not in dest:
                continue
                
            msg = MIMEMultipart()
            msg['From'] = remetente
            msg['To'] = dest 
            msg['Subject'] = assunto
            
            corpo_html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="background-color: #f4f4f4; padding: 20px; border-radius: 10px;">
                    <h2 style="color: #0b5394;">Portal Recanto do Rancho</h2>
                    <p>{corpo_texto.replace(chr(10), '<br>')}</p>
                    <hr style="border: none; border-top: 1px solid #ccc;">
                    <p style="font-size: 12px; color: gray;">Mensagem automática gerada pelo Portal. Por favor, não responda.</p>
                </div>
              </body>
            </html>
            """
            msg.attach(MIMEText(corpo_html, 'html'))
            server.sendmail(remetente, dest, msg.as_string())
            
        server.quit()
    except Exception as e:
        print(f"🔺 ERRO AO ENVIAR E-MAIL: {e}")

def enviar_notificacao(destinatarios, assunto, corpo_texto):
    remetente = st.secrets["email"]["endereco"]
    senha = st.secrets["email"]["senha"]
    lista_destinatarios = list(destinatarios) if isinstance(destinatarios, list) else destinatarios
    thread = threading.Thread(target=disparar_email_background, args=(lista_destinatarios, assunto, corpo_texto, remetente, senha))
    thread.start()

# ==========================================
# --- ESTILO VISUAL ---
# ==========================================
def aplicar_estilo_app():
    st.markdown("""
    <style>
        [data-testid="collapsedControl"] {display: none;}
        #MainMenu, footer, header {visibility: hidden;}
        .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
        div[data-testid="stLinkButton"] {border: none !important; box-shadow: none !important; padding: 0 !important; background-color: transparent !important;}
        div.stButton > button, div[data-testid="stLinkButton"] > a {
            border-radius: 12px !important; border: 1px solid rgba(200, 200, 200, 0.2) !important; box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
            transition: all 0.2s ease-in-out !important; height: auto !important; padding: 12px 0 !important; font-weight: 600 !important;
            display: flex !important; justify-content: center !important; text-decoration: none !important; width: 100% !important;
        }
        div.stButton > button:hover, div[data-testid="stLinkButton"] > a:hover {
            transform: translateY(-3px) !important; box-shadow: 0 8px 12px rgba(0,0,0,0.1) !important; border-color: #0b5394 !important; color: #0b5394 !important;
        }
        div[data-testid="stExpander"] {border-radius: 12px !important; border: 1px solid rgba(200, 200, 200, 0.2); box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 10px;}
        div[data-testid="stAlert"] {border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.03);}
    </style>
    """, unsafe_allow_html=True)

aplicar_estilo_app()

# ==========================================
# --- BANCO DE DADOS ---
# ==========================================
def get_conexao():
    return psycopg2.connect(
        host=st.secrets["supabase"]["host"], port=st.secrets["supabase"]["port"],
        database=st.secrets["supabase"]["database"], user=st.secrets["supabase"]["user"],
        password=st.secrets["supabase"]["password"], sslmode="require", connect_timeout=10
    )

def executar_sql(query, parametros=()):
    conn = get_conexao(); cursor = conn.cursor(); cursor.execute(query.replace('?', '%s'), parametros)
    conn.commit(); cursor.close(); conn.close()

def buscar_dados(query, parametros=()):
    conn = get_conexao(); cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(query.replace('?', '%s'), parametros); resultado = [dict(linha) for linha in cursor.fetchall()]
    cursor.close(); conn.close(); return resultado

@st.cache_resource
def inicializar_banco():
    try:
        conn = get_conexao()
        conn.autocommit = True  # Autocommit ligado para evitar erro nas adições de coluna
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, email TEXT UNIQUE NOT NULL, casa TEXT NOT NULL, senha TEXT NOT NULL, perfil TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS comunicados (id SERIAL PRIMARY KEY, titulo TEXT NOT NULL, mensagem TEXT NOT NULL, data_publicacao TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS assembleias (id SERIAL PRIMARY KEY, data_completa TEXT NOT NULL, mes_ano TEXT NOT NULL, local TEXT NOT NULL, pauta TEXT NOT NULL, status TEXT DEFAULT 'Agendada');
            CREATE TABLE IF NOT EXISTS atas (id SERIAL PRIMARY KEY, mes_ano TEXT NOT NULL, data_completa TEXT NOT NULL, pauta TEXT NOT NULL, nome_arquivo TEXT NOT NULL, arquivo_dados BYTEA);
            CREATE TABLE IF NOT EXISTS reservas (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, casa TEXT NOT NULL, data_reserva TEXT NOT NULL, status TEXT NOT NULL, boleto_nome TEXT, boleto_dados BYTEA, comprovante_nome TEXT, comprovante_dados BYTEA);
            CREATE TABLE IF NOT EXISTS balancetes (id SERIAL PRIMARY KEY, titulo TEXT NOT NULL, nome_arquivo TEXT NOT NULL, arquivo_dados BYTEA);
            CREATE TABLE IF NOT EXISTS multas (id SERIAL PRIMARY KEY, casa TEXT NOT NULL, motivo TEXT NOT NULL, data_aplicacao TEXT NOT NULL, nome_arquivo TEXT NOT NULL, arquivo_dados BYTEA);
        ''')
        
        # Atualiza a tabela de multas silenciosamente para o novo sistema de baixa
        try: cursor.execute("ALTER TABLE multas ADD COLUMN status TEXT DEFAULT 'Pendente'")
        except: pass
        try: cursor.execute("ALTER TABLE multas ADD COLUMN comprovante_nome TEXT")
        except: pass
        try: cursor.execute("ALTER TABLE multas ADD COLUMN comprovante_dados BYTEA")
        except: pass
        
        cursor.execute("SELECT id FROM usuarios WHERE perfil='Síndico' LIMIT 1")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO usuarios (nome, email, casa, senha, perfil) VALUES (%s, %s, %s, %s, %s)", ("Administrador", "sindico@recanto.com", "Sede", "admin123", "Síndico"))
        
        cursor.close(); conn.close()
        return True
    except Exception as e:
        print(f"Erro no banco: {e}")
        return False

inicializar_banco()

MESES_PT = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}

if 'pagina_atual' not in st.session_state: st.session_state['pagina_atual'] = "Página Inicial"
def navegar_para(pagina): st.session_state['pagina_atual'] = pagina

# ==========================================
# --- LOGIN / CADASTRO ---
# ==========================================
if 'usuario_logado' not in st.session_state: st.session_state['usuario_logado'] = None
if 'tela_acesso' not in st.session_state: st.session_state['tela_acesso'] = "Login"

if st.session_state['usuario_logado'] is None:
    st.title("🔐 Portal Recanto do Rancho")
    escolha_tela = st.radio("Selecione uma opção:", ["Login", "Cadastrar Novo Morador"], horizontal=True, index=["Login", "Cadastrar Novo Morador"].index(st.session_state['tela_acesso']))
    st.session_state['tela_acesso'] = escolha_tela
    
    if escolha_tela == "Login":
        st.subheader("Acesse sua conta")
        email_login = st.text_input("E-mail"); senha_login = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            usuario = buscar_dados("SELECT * FROM usuarios WHERE email=? AND senha=?", (email_login, senha_login))
            if usuario:
                st.session_state['usuario_logado'] = usuario[0]; st.session_state['pagina_atual'] = "Página Inicial"; st.rerun()
            else: st.error("E-mail ou senha incorretos.")
    else: 
        st.subheader("Crie seu acesso")
        nome_cad = st.text_input("Nome Completo"); email_cad = st.text_input("E-mail Pessoal"); casa_cad = st.text_input("Número da Casa"); senha_cad = st.text_input("Crie uma Senha", type="password")
        if st.button("Criar Conta"):
            if nome_cad and email_cad and casa_cad and senha_cad:
                if buscar_dados("SELECT * FROM usuarios WHERE email=?", (email_cad,)): st.warning("Este e-mail já está cadastrado. Tente fazer login.")
                else:
                    executar_sql("INSERT INTO usuarios (nome, email, casa, senha, perfil) VALUES (?, ?, ?, ?, ?)", (nome_cad, email_cad, casa_cad, senha_cad, "Morador"))
                    st.success("Conta criada! Redirecionando..."); st.session_state['tela_acesso'] = "Login"; st.rerun()
            else: st.warning("Preencha todos os campos corretamente.")

# ==========================================
# --- APP LOGADO ---
# ==========================================
else:
    user = st.session_state['usuario_logado']; pagina = st.session_state['pagina_atual']

    col_nome, col_sair = st.columns([8, 2])
    with col_nome: st.markdown(f"<div style='margin-top: 15px;'><span style='color: gray; font-size: 15px;'>🏠 Casa {user['casa']} | Logado como: <b>{user['nome']}</b></span></div>", unsafe_allow_html=True)
    with col_sair:
        if st.button("🚪 Sair", use_container_width=True): st.session_state['usuario_logado'] = None; st.rerun()
    st.divider()

    if pagina != "Página Inicial":
        st.button("🏠 Voltar para a Página Inicial", use_container_width=True, on_click=navegar_para, args=("Página Inicial",)); st.divider()

    # --- PÁGINA INICIAL ---
    if pagina == "Página Inicial":
        st.markdown(f"<h4 style='text-align: center; color: gray; font-weight: normal; margin-bottom: 0;'>Bem-vindo, {user['nome'].split()[0].upper()}</h4>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; margin-top: 0;'>Recanto do Rancho</h1>", unsafe_allow_html=True); st.write("")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.button("📢 Comunicados", use_container_width=True, on_click=navegar_para, args=("Comunicados",))
            st.button("📊 Contas", use_container_width=True, on_click=navegar_para, args=("Prestação de Contas",))
        with col2:
            st.button("📅 Reservas", use_container_width=True, on_click=navegar_para, args=("Reservas",))
            st.button("🤝 Assembleias", use_container_width=True, on_click=navegar_para, args=("Assembleias",))
        with col3:
            if user['perfil'] == "Síndico":
                st.button("👥 Moradores", use_container_width=True, on_click=navegar_para, args=("Moradores",))
                st.button("🛑 Multas", use_container_width=True, on_click=navegar_para, args=("Multas",))
            else:
                st.link_button("💬 Falar com o Síndico", "https://wa.me/5521990353882", use_container_width=True)
                st.button("🛑 Minhas Multas", use_container_width=True, on_click=navegar_para, args=("Minhas Multas",))

        st.divider()
        assembleias_agendadas = buscar_dados("SELECT * FROM assembleias WHERE status='Agendada' ORDER BY id DESC LIMIT 2")
        ultimos_avisos = buscar_dados("SELECT * FROM comunicados ORDER BY id DESC LIMIT 3")
        
        if assembleias_agendadas or ultimos_avisos:
            st.subheader("📌 Destaques")
            for ass in assembleias_agendadas: st.warning(f"🚨 **ASSEMBLEIA:** {ass['data_completa']} | Local: {ass['local']}")
            for aviso in ultimos_avisos: st.info(f"**{aviso['titulo']}** ({aviso['data_publicacao']})\n\n{aviso['mensagem']}")

    # --- COMUNICADOS ---
    elif pagina == "Comunicados":
        st.title("📢 Mural de Comunicados")
        if user['perfil'] == "Síndico":
            with st.expander("➕ Publicar Novo Comunicado"):
                with st.form("form_aviso", clear_on_submit=True):
                    tit = st.text_input("Título do Comunicado"); msg = st.text_area("Mensagem")
                    if st.form_submit_button("Publicar no Mural") and tit and msg:
                        executar_sql("INSERT INTO comunicados (titulo, mensagem, data_publicacao) VALUES (?, ?, ?)", (tit, msg, datetime.datetime.now().strftime("%d/%m/%Y")))
                        emails = [u['email'] for u in buscar_dados("SELECT email FROM usuarios")]
                        enviar_notificacao(emails, f"📢 Novo Comunicado: {tit}", f"Olá!\n\nHá um novo aviso no Portal:\n\nTítulo: {tit}\nMensagem: {msg}")
                        st.success("Publicado!"); st.rerun()
            st.divider()

        for ass in buscar_dados("SELECT * FROM assembleias WHERE status='Agendada'"):
            st.warning(f"🚨 **CONVOCAÇÃO:** {ass['data_completa']}\n\n**Local:** {ass['local']} | **Pauta:** {ass['pauta']}")

        avisos = buscar_dados("SELECT * FROM comunicados ORDER BY id DESC")
        if not avisos: st.write("Nenhum comunicado publicado.")
        for aviso in avisos:
            st.markdown(f"### 📌 {aviso['titulo']}"); st.caption(aviso['data_publicacao']); st.write(aviso['mensagem'])
            if user['perfil'] == "Síndico" and st.button("🗑️ Apagar Comunicado", key=f"del_{aviso['id']}"):
                executar_sql("DELETE FROM comunicados WHERE id=?", (aviso['id'],)); st.rerun()
            st.divider()

    # --- RESERVAS ---
    elif pagina == "Reservas":
        st.title("📅 Reservas da Churrasqueira")
        reservas_gerais = buscar_dados("SELECT * FROM reservas ORDER BY id DESC")
        
        if user['perfil'] == "Síndico":
            st.subheader("Painel de Solicitações e Pagamentos")
            pendentes = [r for r in reservas_gerais if r['status'] in ["Aguardando Taxa", "Em Análise", "Aguardando Pagamento"]]
            if not pendentes: st.write("Nenhuma ação pendente no momento.")
            
            for r in pendentes:
                with st.expander(f"📌 {r['data_reserva']} - {r['nome']} (Casa {r['casa']}) | Status: {r['status']}", expanded=True):
                    if r['status'] == "Aguardando Taxa":
                        st.info("O morador solicitou esta data. Envie a cobrança.")
                        arq_bol = st.file_uploader("Anexar Boleto/Pix", key=f"ub_{r['id']}")
                        if st.button("Enviar Cobrança", key=f"bb_{r['id']}") and arq_bol:
                            executar_sql("UPDATE reservas SET status='Aguardando Pagamento', boleto_nome=?, boleto_dados=? WHERE id=?", (arq_bol.name, arq_bol.getvalue(), r['id'])); st.rerun()
                    elif r['status'] == "Aguardando Pagamento": st.warning("Cobrança enviada. Aguardando comprovante do morador.")
                    elif r['status'] == "Em Análise":
                        st.success("O morador enviou o comprovante!")
                        if r.get('comprovante_dados'): st.download_button("📄 Baixar Comprovante", data=bytes(r['comprovante_dados']), file_name=r['comprovante_nome'], key=f"dc_{r['id']}")
                        c1, c2 = st.columns(2)
                        if c1.button("✅ Aprovar", key=f"apr_{r['id']}"):
                            executar_sql("UPDATE reservas SET status='Aprovada' WHERE id=?", (r['id'],))
                            dono = buscar_dados("SELECT email FROM usuarios WHERE casa=? LIMIT 1", (r['casa'],))
                            if dono: enviar_notificacao(dono[0]['email'], "📅 Reserva Aprovada!", f"Sua reserva para {r['data_reserva']} foi APROVADA.")
                            st.rerun()
                        if c2.button("❌ Reprovar", key=f"rep_{r['id']}"): executar_sql("UPDATE reservas SET status='Reprovada' WHERE id=?", (r['id'],)); st.rerun()
            st.divider(); st.subheader("Histórico Completo")
            for r in reservas_gerais: st.write(f"**{r['data_reserva']}** | Casa {r['casa']} | Status: {r['status']}")

        else: # MORADOR
            minhas_reservas = buscar_dados("SELECT * FROM reservas WHERE casa=? ORDER BY id DESC", (user['casa'],))
            if minhas_reservas:
                st.subheader("Minhas Solicitações")
                for r in minhas_reservas:
                    with st.container():
                        if r['status'] == "Aprovada": st.success(f"📅 {r['data_reserva']} | APROVADA")
                        elif r['status'] == "Reprovada": st.error(f"📅 {r['data_reserva']} | REPROVADA")
                        elif r['status'] == "Aguardando Taxa": st.warning(f"📅 {r['data_reserva']} | Aguardando o síndico gerar a cobrança.")
                        elif r['status'] == "Em Análise": st.info(f"📅 {r['data_reserva']} | Comprovante em análise.")
                        elif r['status'] == "Aguardando Pagamento":
                            st.error(f"📅 {r['data_reserva']} | PENDENTE DE PAGAMENTO")
                            if r.get('boleto_dados'): st.download_button("📥 1. Baixar Cobrança", data=bytes(r['boleto_dados']), file_name=r['boleto_nome'], key=f"db_{r['id']}")
                            arq_comp = st.file_uploader("2. Enviar Comprovante", key=f"uc_{r['id']}")
                            if st.button("Confirmar Pagamento", key=f"bc_{r['id']}") and arq_comp:
                                executar_sql("UPDATE reservas SET status='Em Análise', comprovante_nome=?, comprovante_dados=? WHERE id=?", (arq_comp.name, arq_comp.getvalue(), r['id'])); st.rerun()
                    st.divider()

            st.subheader("Nova Solicitação")
            # --- LÓGICA DE RESET DO CALENDÁRIO ---
            if 'chave_calendario' not in st.session_state: st.session_state['chave_calendario'] = 0
            
            data_escolhida = st.date_input("Selecione a data:", value=None, key=f"calendario_{st.session_state['chave_calendario']}")
            
            if data_escolhida:
                data_str = data_escolhida.strftime("%d/%m/%Y")
                status_data = None
                for r in reservas_gerais:
                    if r['data_reserva'] == data_str and r['status'] in ["Aguardando Taxa", "Aguardando Pagamento", "Em Análise", "Aprovada"]:
                        status_data = r['status']; break 
                
                if status_data == "Aprovada": st.error("⚠️ Data já reservada.")
                elif status_data: st.warning("⏳ Data já está em processo de locação por outro morador.")
                else:
                    st.info("✅ Data disponível!")
                    if st.button("Solicitar Data"):
                        executar_sql("INSERT INTO reservas (nome, casa, data_reserva, status) VALUES (?, ?, ?, ?)", (user['nome'], user['casa'], data_str, "Aguardando Taxa"))
                        
                        # --- NOTIFICA SÍNDICO ---
                        sindico = buscar_dados("SELECT email FROM usuarios WHERE perfil='Síndico' LIMIT 1")
                        if sindico: enviar_notificacao(sindico[0]['email'], f"📅 Nova Reserva: Casa {user['casa']}", f"O morador da Casa {user['casa']} solicitou a reserva para {data_str}.\nAcesse o painel para anexar a cobrança.")
                        
                        st.session_state['chave_calendario'] += 1 # Reseta o calendário
                        st.success("Enviado! Aguarde a liberação da cobrança."); st.rerun()

    # --- ASSEMBLEIAS ---
    elif pagina == "Assembleias":
        st.title("🤝 Assembleias")
        assembleias = buscar_dados("SELECT * FROM assembleias WHERE status='Agendada'")
        atas = buscar_dados("SELECT * FROM atas ORDER BY id DESC")
        
        if user['perfil'] == "Síndico":
            with st.expander("➕ Agendar Nova Assembleia"):
                with st.form("f_ass", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    d_reuniao = c1.date_input("Data", value=None); h_reuniao = c2.time_input("Horário", value=None)
                    loc = st.text_input("Local"); pauta = st.text_area("Pauta Principal")
                    if st.form_submit_button("Agendar") and d_reuniao and h_reuniao and loc and pauta:
                        d_str = d_reuniao.strftime("%d/%m/%Y"); h_str = h_reuniao.strftime("%H:%M")
                        executar_sql("INSERT INTO assembleias (data_completa, mes_ano, local, pauta) VALUES (?, ?, ?, ?)", (f"{d_str} às {h_str}", f"{MESES_PT[d_reuniao.month]}/{d_reuniao.year}", loc, pauta))
                        emails = [u['email'] for u in buscar_dados("SELECT email FROM usuarios")]
                        if emails: enviar_notificacao(emails, f"🤝 Assembleia: {d_str}", f"Nova Assembleia!\nData: {d_str}\nLocal: {loc}\nPauta: {pauta}")
                        st.rerun()
            
            with st.expander("📂 Publicar Ata"):
                if assembleias:
                    with st.form("f_ata", clear_on_submit=True):
                        opcoes = {f"{a['data_completa']} - {a['pauta']}": a for a in assembleias}
                        escolha = st.selectbox("Assembleia:", list(opcoes.keys()))
                        arq = st.file_uploader("Ata em PDF", type=["pdf"])
                        if st.form_submit_button("Publicar") and arq:
                            ass = opcoes[escolha]
                            executar_sql("INSERT INTO atas (mes_ano, data_completa, pauta, nome_arquivo, arquivo_dados) VALUES (?, ?, ?, ?, ?)", (ass['mes_ano'], ass['data_completa'], ass['pauta'], arq.name, arq.getvalue()))
                            executar_sql("UPDATE assembleias SET status='Concluída' WHERE id=?", (ass['id'],)); st.rerun()
            st.divider()

        for ata in atas:
            with st.expander(f"📌 {ata['mes_ano']}"):
                st.write(f"**Data:** {ata['data_completa']} | **Pauta:** {ata['pauta']}")
                c1, c2 = st.columns(2)
                if ata.get('arquivo_dados'): c1.download_button("📄 Baixar Ata", data=bytes(ata['arquivo_dados']), file_name=ata['nome_arquivo'], key=f"da_{ata['id']}")
                if user['perfil'] == "Síndico" and c2.button("🗑️ Excluir", key=f"xa_{ata['id']}"): executar_sql("DELETE FROM atas WHERE id=?", (ata['id'],)); st.rerun()

    # --- PRESTAÇÃO DE CONTAS ---
    elif pagina == "Prestação de Contas":
        st.title("📊 Balancetes")
        if user['perfil'] == "Síndico":
            with st.expander("📂 Novo Balancete"):
                with st.form("f_bal", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    mes_sel = c1.selectbox("Mês:", list(MESES_PT.values())); ano_sel = c2.selectbox("Ano:", [2024, 2025, 2026, 2027])
                    arq_bal = st.file_uploader("Documento PDF", type=["pdf"])
                    if st.form_submit_button("Salvar") and arq_bal:
                        executar_sql("INSERT INTO balancetes (titulo, nome_arquivo, arquivo_dados) VALUES (?, ?, ?)", (f"Balancete {mes_sel}/{ano_sel}", arq_bal.name, arq_bal.getvalue())); st.rerun()
            st.divider()
        for b in buscar_dados("SELECT * FROM balancetes ORDER BY id DESC"):
            st.write(f"**{b['titulo']}**")
            c1, c2 = st.columns(2)
            if b.get('arquivo_dados'): c1.download_button("📄 Baixar", data=bytes(b['arquivo_dados']), file_name=b['nome_arquivo'], key=f"db_{b['id']}")
            if user['perfil'] == "Síndico" and c2.button("🗑️ Excluir", key=f"xb_{b['id']}"): executar_sql("DELETE FROM balancetes WHERE id=?", (b['id'],)); st.rerun()
            st.divider()

    # --- MORADORES ---
    elif pagina == "Moradores":
        st.title("👥 Moradores")
        for m in buscar_dados("SELECT * FROM usuarios WHERE perfil='Morador' ORDER BY casa ASC"):
            c1, c2 = st.columns([3, 1])
            c1.write(f"🏠 **Casa {m['casa']}** - {m['nome']}")
            if c2.button("🗑️ Excluir", key=f"xm_{m['id']}"): executar_sql("DELETE FROM usuarios WHERE id=?", (m['id'],)); st.rerun()
            st.divider()

    # --- MULTAS ---
    elif pagina == "Multas" or pagina == "Minhas Multas":
        st.title("🛑 Multas")
        
        # --- VISAO DO SÍNDICO ---
        if user['perfil'] == "Síndico":
            with st.expander("➕ Aplicar Multa"):
                moradores = buscar_dados("SELECT * FROM usuarios WHERE perfil='Morador'")
                with st.form("f_multa", clear_on_submit=True):
                    infrator = st.selectbox("Morador Infrator:", [f"Casa {m['casa']} - {m['nome']}" for m in moradores]) if moradores else None
                    mot = st.text_input("Motivo da Multa:")
                    arq_m = st.file_uploader("Notificação em PDF", type=["pdf"])
                    if st.form_submit_button("Aplicar") and infrator and mot and arq_m:
                        n_casa = infrator.split(" - ")[0].replace("Casa ", "")
                        executar_sql("INSERT INTO multas (casa, motivo, data_aplicacao, nome_arquivo, arquivo_dados) VALUES (?, ?, ?, ?, ?)", (n_casa, mot, datetime.datetime.now().strftime("%d/%m/%Y"), arq_m.name, arq_m.getvalue()))
                        
                        # --- NOTIFICA MORADOR ---
                        email_infrator = buscar_dados("SELECT email FROM usuarios WHERE casa=? LIMIT 1", (n_casa,))
                        if email_infrator: enviar_notificacao(email_infrator[0]['email'], "🛑 Nova Notificação", f"Uma nova notificação/multa foi registrada para a sua casa.\nMotivo: {mot}\n\nAcesse o portal para baixar o documento e enviar o comprovante de pagamento.")
                        st.rerun()
            
            st.subheader("Controle de Multas e Baixas")
            for m in buscar_dados("SELECT * FROM multas ORDER BY id DESC"):
                status_multa = m.get('status', 'Pendente')
                st.write(f"🏠 **Casa {m['casa']}** | {m['motivo']} ({m['data_aplicacao']}) | Status: **{status_multa}**")
                
                c1, c2, c3, c4 = st.columns(4)
                if m.get('arquivo_dados'): c1.download_button("📄 Notificação", data=bytes(m['arquivo_dados']), file_name=m['nome_arquivo'], key=f"dm_{m['id']}")
                
                if status_multa == 'Em Análise':
                    if m.get('comprovante_dados'): c2.download_button("📥 Comprovante", data=bytes(m['comprovante_dados']), file_name=m['comprovante_nome'], key=f"dcm_{m['id']}")
                    if c3.button("✅ Dar Baixa", key=f"dbm_{m['id']}"): executar_sql("UPDATE multas SET status='Paga' WHERE id=?", (m['id'],)); st.rerun()
                
                if c4.button("🗑️ Excluir", key=f"xxm_{m['id']}"): executar_sql("DELETE FROM multas WHERE id=?", (m['id'],)); st.rerun()
                st.divider()
                
        # --- VISAO DO MORADOR ---
        else:
            minhas_multas = buscar_dados("SELECT * FROM multas WHERE casa=? ORDER BY id DESC", (user['casa'],))
            if not minhas_multas: st.success("🎉 Nenhuma multa registrada para a sua casa.")
            for m in minhas_multas:
                status_m = m.get('status', 'Pendente')
                if status_m == 'Pendente':
                    st.error(f"⚠️ PENDENTE: {m['motivo']} ({m['data_aplicacao']})")
                    if m.get('arquivo_dados'): st.download_button("📄 Baixar Notificação/Boleto", data=bytes(m['arquivo_dados']), file_name=m['nome_arquivo'], key=f"dmm_{m['id']}")
                    
                    arq_comp = st.file_uploader("Enviar Comprovante de Pagamento", key=f"ucm_{m['id']}")
                    if st.button("Confirmar Pagamento", key=f"bcm_{m['id']}") and arq_comp:
                        executar_sql("UPDATE multas SET status='Em Análise', comprovante_nome=?, comprovante_dados=? WHERE id=?", (arq_comp.name, arq_comp.getvalue(), m['id'])); st.rerun()
                
                elif status_m == 'Em Análise':
                    st.info(f"⏳ EM ANÁLISE: {m['motivo']}")
                    st.write("Comprovante enviado! Aguardando o síndico dar baixa.")
                
                elif status_m == 'Paga':
                    st.success(f"✅ PAGA: {m['motivo']} ({m['data_aplicacao']})")
                
                st.divider()