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
            for ass in assembleias_agendadas: st.warning(f"🚨 **ASSEMBLEIA