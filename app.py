import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import datetime
# NOVOS IMPORTS PARA E-MAIL
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading 

# Configuração da página - Inicia com layout expandido e barra lateral escondida/removida
st.set_page_config(page_title="Recanto do Rancho", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# --- FUNÇÕES DE E-MAIL (NOVO) ---
# ==========================================
def disparar_email_background(destinatarios, assunto, corpo_texto):
    """Função que roda em segundo plano para enviar o e-mail"""
    try:
        # Puxa as credenciais dos Secrets
        remetente = st.secrets["email"]["endereco"]
        senha = st.secrets["email"]["senha"]
        
        # Configura a mensagem
        msg = MIMEMultipart()
        msg['From'] = remetente
        msg['Subject'] = assunto
        
        # Corpo do e-mail em HTML simples
        corpo_html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="background-color: #f4f4f4; padding: 20px; border-radius: 10px;">
                <h2 style="color: #0b5394;">Portal Recanto do Rancho</h2>
                <p>{corpo_texto.replace(chr(10), '<br>')}</p>
                <hr style="border: none; border-top: 1px solid #ccc;">
                <p style="font-size: 12px; color: gray;">Esta é uma mensagem automática gerada pelo Portal. Por favor, não responda.</p>
            </div>
          </body>
        </html>
        """
        msg.attach(MIMEText(corpo_html, 'html'))
        
        # Configura o servidor SMTP (Gmail)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls() # Segurança
        server.login(remetente, senha)
        
        # Envia
        if isinstance(destinatarios, list):
            # Se for lista (Aviso Geral), usa Cópia Oculta (BCC)
            msg['To'] = remetente # Manda 'para' o próprio admin
            msg['Bcc'] = ", ".join(destinatarios) # Cópia oculta para todos
            server.sendmail(remetente, destinatarios + [remetente], msg.as_string())
        else:
            # Se for único (Aprovação de reserva)
            msg['To'] = destinatarios
            server.sendmail(remetente, destinatarios, msg.as_string())
            
        server.quit()
    except Exception as e:
        # Se der erro, printa no console do Streamlit (não quebra o app pro usuário)
        print(f"🔺 ERRO AO ENVIAR E-MAIL: {e}")

def enviar_notificacao(destinatarios, assunto, corpo_texto):
    """Chama o envio de e-mail em uma Thread separada para não travar o app"""
    # Cria uma cópia da lista de destinatários para evitar problemas de memória
    lista_destinatarios = list(destinatarios) if isinstance(destinatarios, list) else destinatarios
    
    thread = threading.Thread(target=disparar_email_background, args=(lista_destinatarios, assunto, corpo_texto))
    thread.start()

# ==========================================
# Estilo para deixar com aparência de Aplicativo
# ==========================================
def aplicar_estilo_app():
    st.markdown("""
    <style>
        /* Esconde elementos nativos do Streamlit que não queremos ver */
        [data-testid="collapsedControl"] {display: none;}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }
        
        /* Esconde a caixa extra do st.link_button para evitar "botão dentro de botão" */
        div[data-testid="stLinkButton"] {
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            background-color: transparent !important;
        }
        
        /* Estilo das caixas (Botões normais e Link do WhatsApp) */
        div.stButton > button, div[data-testid="stLinkButton"] > a {
            border-radius: 12px !important;
            border: 1px solid rgba(200, 200, 200, 0.2) !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
            transition: all 0.2s ease-in-out !important;
            height: auto !important;
            padding: 12px 0 !important;
            font-weight: 600 !important;
            display: flex !important;
            justify-content: center !important;
            text-decoration: none !important;
            width: 100% !important;
        }
        div.stButton > button:hover, div[data-testid="stLinkButton"] > a:hover {
            transform: translateY(-3px) !important;
            box-shadow: 0 8px 12px rgba(0,0,0,0.1) !important;
            border-color: #0b5394 !important;
            color: #0b5394 !important;
        }
        
        div[data-testid="stExpander"] {
            border-radius: 12px !important;
            border: 1px solid rgba(200, 200, 200, 0.2);
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            margin-bottom: 10px;
        }
        div[data-testid="stAlert"] {
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        }
    </style>
    """, unsafe_allow_html=True)

aplicar_estilo_app()

# ==========================================
# 1. CONEXÃO COM BANCO DE DADOS EM NUVEM (SUPABASE)
# ==========================================
def get_conexao():
    try:
        return psycopg2.connect(
            host=st.secrets["supabase"]["host"],
            port=st.secrets["supabase"]["port"],
            database=st.secrets["supabase"]["database"],
            user=st.secrets["supabase"]["user"],
            password=st.secrets["supabase"]["password"],
            sslmode="require",
            connect_timeout=10
        )
    except Exception as e:
        st.error(f"🔺 ERRO DO SUPABASE: {e}")
        st.stop()

def executar_sql(query, parametros=()):
    query = query.replace('?', '%s')
    conn = get_conexao()
    cursor = conn.cursor()
    cursor.execute(query, parametros)
    conn.commit()
    cursor.close()
    conn.close()

def buscar_dados(query, parametros=()):
    query = query.replace('?', '%s')
    conn = get_conexao()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(query, parametros)
    resultado = cursor.fetchall()
    resultado_normalizado = [dict(linha) for linha in resultado]
    cursor.close()
    conn.close()
    return resultado_normalizado

@st.cache_resource
def inicializar_banco():
    try:
        conn = get_conexao()
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
        
        cursor.execute("SELECT id FROM usuarios WHERE perfil='Síndico' LIMIT 1")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO usuarios (nome, email, casa, senha, perfil) VALUES (%s, %s, %s, %s, %s)",
                         ("Administrador", "sindico@recanto.com", "Sede", "admin123", "Síndico"))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro na criação inicial do banco de dados: {e}")
        return False

inicializar_banco()

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

if 'pagina_atual' not in st.session_state:
    st.session_state['pagina_atual'] = "Página Inicial"

def navegar_para(pagina):
    st.session_state['pagina_atual'] = pagina

# ==========================================
# 2. SISTEMA DE LOGIN
# ==========================================
if 'usuario_logado' not in st.session_state:
    st.session_state['usuario_logado'] = None

if 'tela_acesso' not in st.session_state:
    st.session_state['tela_acesso'] = "Login"

if st.session_state['usuario_logado'] is None:
    st.title("🔐 Portal Recanto do Rancho")
    
    opcoes_acesso = ["Login", "Cadastrar Novo Morador"]
    idx_acesso = opcoes_acesso.index(st.session_state['tela_acesso'])
    
    escolha_tela = st.radio("Selecione uma opção:", opcoes_acesso, horizontal=True, index=idx_acesso)
    st.session_state['tela_acesso'] = escolha_tela
    
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
        casa_cad = st.text_input("Número da Casa ou Apartamento")
        senha_cad = st.text_input("Crie uma Senha", type="password")
        
        if st.button("Criar Conta"):
            if nome_cad and email_cad and casa_cad and senha_cad:
                existe = buscar_dados("SELECT * FROM usuarios WHERE email=?", (email_cad,))
                if existe:
                    st.warning("Este e-mail já está cadastrado. Tente fazer login.")
                else:
                    executar_sql("INSERT INTO usuarios (nome, email, casa, senha, perfil) VALUES (?, ?, ?, ?, ?)",
                                 (nome_cad, email_cad, casa_cad, senha_cad, "Morador"))
                    st.success("Conta criada com sucesso! Redirecionando para o login...")
                    st.session_state['tela_acesso'] = "Login"
                    st.rerun()
            else:
                st.warning("Por favor, preencha todos os campos corretamente.")

# ==========================================
# 3. O APLICATIVO LOGADO
# ==========================================
else:
    user = st.session_state['usuario_logado'] 
    pagina = st.session_state['pagina_atual']
    primeiro_nome = user['nome'].split()[0].upper()

    # --- CABEÇALHO SUPERIOR (ALINHADO) ---
    col_nome, col_vazio, col_sair = st.columns([6, 2, 2])
    with col_nome:
        # A margem superior (margin-top: 15px) alinha o texto perfeitamente com o botão de Sair
        st.markdown(f"<div style='margin-top: 15px;'><span style='color: gray; font-size: 15px;'>🏠 Casa {user['casa']} | Logado como: <b>{user['nome']}</b></span></div>", unsafe_allow_html=True)
    with col_sair:
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state['usuario_logado'] = None
            st.rerun()
    st.divider()

    # --- BOTÃO DE VOLTAR ---
    if pagina != "Página Inicial":
        st.button("🏠 Voltar para a Página Inicial", use_container_width=True, on_click=navegar_para, args=("Página Inicial",))
        st.divider()

    # --- PÁGINA INICIAL ---
    if pagina == "Página Inicial":
        st.markdown(f"<h4 style='text-align: center; color: gray; font-weight: normal; margin-bottom: 0;'>Bem-vindo, {primeiro_nome}</h4>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; margin-top: 0;'>Recanto do Rancho</h1>", unsafe_allow_html=True)
        st.write("")
        
        # Caixas organizadas perfeitamente em 3 colunas (Lado a lado)
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
        ultimos_avisos = buscar_dados("SELECT * FROM comunicados ORDER BY id DESC LIMIT 3")
        assembleias_agendadas = buscar_dados("SELECT * FROM assembleias WHERE status='Agendada' ORDER BY id DESC LIMIT 2")
        
        if assembleias_agendadas or ultimos_avisos:
            st.subheader("📌 Destaques")
            for ass in assembleias_agendadas:
                st.warning(f"🚨 **ASSEMBLEIA:** {ass['data_completa']} | Local: {ass['local']}")
            for aviso in ultimos_avisos:
                st.info(f"**{aviso['titulo']}** ({aviso['data_publicacao']})\n\n{aviso['mensagem']}")

    # --- COMUNICADOS ---
    elif pagina == "Comunicados":
        st.title("📢 Mural de Comunicados")
        if user['perfil'] == "Síndico":
            with st.expander("➕ Publicar Novo Comunicado"):
                with st.form("form_aviso", clear_on_submit=True):
                    tit_aviso = st.text_input("Título do Comunicado")
                    msg_aviso = st.text_area("Assunto ou Mensagem")
                    if st.form_submit_button("Publicar no Mural"):
                        if tit_aviso and msg_aviso:
                            data_hoje = datetime.datetime.now().strftime("%d/%m/%Y")
                            executar_sql("INSERT INTO comunicados (titulo, mensagem, data_publicacao) VALUES (?, ?, ?)", (tit_aviso, msg_aviso, data_hoje))
                            
                            # --- GATILHO DE E-MAIL (NOVO) ---
                            # Busca todos os e-mails dos usuários cadastrados
                            todos_usuarios = buscar_dados("SELECT email FROM usuarios")
                            lista_emails = [u['email'] for u in todos_usuarios]
                            
                            if lista_emails:
                                corpo_email = f"""Olá Morador(a)!

Há um novo comunicado importante no Mural do Recanto do Rancho:

Título: {tit_aviso}

Mensagem:
{msg_aviso}

Acesse o Portal para mais detalhes."""
                                enviar_notificacao(lista_emails, f"📢 Novo Comunicado: {tit_aviso}", corpo_email)
                            # --------------------------------
                            
                            st.success("Comunicado publicado e e-mails enviados com sucesso!")
                            st.rerun()
            st.divider()

        for ass in buscar_dados("SELECT * FROM assembleias WHERE status='Agendada'"):
            st.warning(f"🚨 **CONVOCAÇÃO:** {ass['data_completa']}\n\n**Local:** {ass['local']} | **Pauta:** {ass['pauta']}")

        avisos = buscar_dados("SELECT * FROM comunicados ORDER BY id DESC")
        if not avisos: st.write("Nenhum comunicado publicado ainda.")
        
        for aviso in avisos:
            st.markdown(f"### 📌 {aviso['titulo']}")
            st.caption(f"Publicado em: {aviso['data_publicacao']}")
            st.write(aviso['mensagem'])
            
            if user['perfil'] == "Síndico":
                if st.button("🗑️ Apagar Comunicado", key=f"del_aviso_{aviso['id']}"):
                    executar_sql("DELETE FROM comunicados WHERE id=?", (aviso['id'],))
                    st.rerun()
                    
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
                        st.info("O morador solicitou esta data. Envie o boleto ou a chave Pix para pagamento.")
                        arq_boleto = st.file_uploader("Anexar Boleto ou chave Pix (PDF ou Imagem)", key=f"up_bol_{r['id']}")
                        if st.button("Enviar Cobrança", key=f"btn_bol_{r['id']}"):
                            if arq_boleto:
                                executar_sql("UPDATE reservas SET status='Aguardando Pagamento', boleto_nome=?, boleto_dados=? WHERE id=?", (arq_boleto.name, arq_boleto.getvalue(), r['id']))
                                st.rerun()
                            else: st.error("Por favor, anexe o arquivo da cobrança.")
                                
                    elif r['status'] == "Aguardando Pagamento":
                        st.warning("Cobrança enviada. Aguardando o morador anexar o comprovante.")
                        
                    elif r['status'] == "Em Análise":
                        st.success("O morador enviou o comprovante de pagamento!")
                        if r.get('comprovante_dados'):
                            st.download_button("📄 Baixar Comprovante", data=bytes(r['comprovante_dados']), file_name=r['comprovante_nome'], key=f"dl_comp_{r['id']}")
                        
                        col1, col2 = st.columns(2)
                        if col1.button("✅ Aprovar Reserva", key=f"apr_{r['id']}"):
                            executar_sql("UPDATE reservas SET status='Aprovada' WHERE id=?", (r['id'],))
                            
                            # --- GATILHO DE E-MAIL (NOVO) ---
                            # Busca o e-mail do morador que fez a reserva
                            dono_reserva = buscar_dados("SELECT email FROM usuarios WHERE casa=? LIMIT 1", (r['casa'],))
                            
                            if dono_reserva:
                                email_morador = dono_reserva[0]['email']
                                corpo_email = f"""Olá {r['nome']}, Casa {r['casa']}!

Boas notícias! Sua solicitação de reserva para a Churrasqueira foi APROVADA.

Data: {r['data_reserva']}

Divirta-se! 🎉"""
                                enviar_notificacao(email_morador, "📅 Sua Reserva da Churrasqueira foi APROVADA!", corpo_email)
                            # --------------------------------
                            st.rerun()

                        if col2.button("❌ Reprovar ou Cancelar", key=f"rep_{r['id']}"):
                            executar_sql("UPDATE reservas SET status='Reprovada' WHERE id=?", (r['id'],)); st.rerun()
            st.divider()
            st.subheader("Histórico Completo")
            for r in reservas_gerais:
                st.write(f"**{r['data_reserva']}** | {r['nome']} (Casa {r['casa']}) | Status: {r['status']}")

        else: # Morador
            st.subheader("Minhas Solicitações")
            minhas_reservas = buscar_dados("SELECT * FROM reservas WHERE casa=? ORDER BY id DESC", (user['casa'],))
            if not minhas_reservas: st.write("Você não possui solicitações de reserva.")
            
            for r in minhas_reservas:
                with st.container():
                    if r['status'] == "Aprovada": st.success(f"📅 {r['data_reserva']} | APROVADA - Churrasqueira liberada!")
                    elif r['status'] == "Reprovada": st.error(f"📅 {r['data_reserva']} | REPROVADA - Cancelada pela administração.")
                    elif r['status'] == "Aguardando Taxa": st.warning(f"📅 {r['data_reserva']} | Aguardando o síndico gerar a cobrança.")
                    elif r['status'] == "Em Análise": st.info(f"📅 {r['data_reserva']} | Comprovante enviado! Em análise pela administração.")
                    elif r['status'] == "Aguardando Pagamento":
                        st.error(f"📅 {r['data_reserva']} | PENDENTE DE PAGAMENTO")
                        if r.get('boleto_dados'):
                            st.download_button("📥 1. Baixar Boleto ou Chave Pix", data=bytes(r['boleto_dados']), file_name=r['boleto_nome'], key=f"dl_bol_{r['id']}")
                        
                        st.write("Após realizar o pagamento, envie o comprovante abaixo:")
                        arq_comp = st.file_uploader("2. Enviar Comprovante", key=f"up_comp_{r['id']}")
                        if st.button("Confirmar Pagamento", key=f"btn_comp_{r['id']}"):
                            if arq_comp:
                                executar_sql("UPDATE reservas SET status='Em Análise', comprovante_nome=?, comprovante_dados=? WHERE id=?", (arq_comp.name, arq_comp.getvalue(), r['id']))
                                st.success("Comprovante enviado com sucesso!"); st.rerun()
                            else: st.error("Por favor, anexe o comprovante antes de confirmar o pagamento.")
                st.divider()

            st.subheader("Nova Solicitação")
            data_escolhida = st.date_input("Selecione a data no calendário:", value=None)
            if data_escolhida:
                data_str = data_escolhida.strftime("%d/%m/%Y")
                status_data = None
                for r in reservas_gerais:
                    if r['data_reserva'] == data_str and r['status'] in ["Aguardando Taxa", "Aguardando Pagamento", "Em Análise", "Aprovada"]:
                        status_data = r['status']
                        break 
                
                if status_data == "Aprovada": st.error("⚠️ Data já reservada.")
                elif status_data: st.warning("⏳ Data já está em processo de locação por outro morador.")
                else:
                    st.info("✅ Data disponível!")
                    if st.button("Solicitar Data"):
                        executar_sql("INSERT INTO reservas (nome, casa, data_reserva, status) VALUES (?, ?, ?, ?)", (user['nome'], user['casa'], data_str, "Aguardando Taxa"))
                        st.success("Solicitação enviada com sucesso! Aguarde a liberação da cobrança."); st.rerun()

    # --- ASSEMBLEIAS ---
    elif pagina == "Assembleias":
        st.title("🤝 Assembleias")
        assembleias = buscar_dados("SELECT * FROM assembleias WHERE status='Agendada'")
        atas = buscar_dados("SELECT * FROM atas ORDER BY id DESC")
        
        if user['perfil'] == "Síndico":
            with st.expander("➕ Agendar Nova Assembleia"):
                with st.form("form_ass", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    data_reuniao = col1.date_input("Data", value=None)
                    hora_reuniao = col2.time_input("Horário", value=None)
                    novo_local = st.text_input("Local")
                    nova_pauta = st.text_area("Pauta Principal")
                    
                    if st.form_submit_button("Agendar"):
                        if data_reuniao and hora_reuniao and novo_local and nova_pauta:
                            data_str = data_reuniao.strftime("%d/%m/%Y")
                            hora_str = hora_reuniao.strftime("%H:%M")
                            mes_ano = f"{MESES_PT[data_reuniao.month]}/{data_reuniao.year}"
                            executar_sql("INSERT INTO assembleias (data_completa, mes_ano, local, pauta) VALUES (?, ?, ?, ?)", (f"{data_str} às {hora_str}", mes_ano, novo_local, nova_pauta))
                            
                            # --- GATILHO DE E-MAIL (NOVO) ---
                            todos_usuarios = buscar_dados("SELECT email FROM usuarios")
                            lista_emails = [u['email'] for u in todos_usuarios]
                            
                            if lista_emails:
                                corpo_email = f"""Olá Morador(a)!

Uma nova Assembleia foi agendada no Recanto do Rancho.

Data: {data_str} às {hora_str}
Local: {novo_local}
Pauta: {nova_pauta}

Sua presença é muito importante. Acesse o portal para conferir o edital oficial."""
                                enviar_notificacao(lista_emails, f"🤝 Convocação de Assembleia: {data_str}", corpo_email)
                            # --------------------------------
                            
                            st.rerun()
            
            with st.expander("📂 Publicar Ata"):
                if assembleias:
                    with st.form("form_ata", clear_on_submit=True):
                        opcoes = {f"{a['data_completa']} - {a['pauta']}": a for a in assembleias}
                        escolha = st.selectbox("Assembleia:", list(opcoes.keys()))
                        arq_ata = st.file_uploader("Documento em PDF", type=["pdf"])
                        if st.form_submit_button("Publicar") and arq_ata:
                            ass = opcoes[escolha]
                            executar_sql("INSERT INTO atas (mes_ano, data_completa, pauta, nome_arquivo, arquivo_dados) VALUES (?, ?, ?, ?, ?)", (ass['mes_ano'], ass['data_completa'], ass['pauta'], arq_ata.name, arq_ata.getvalue()))
                            executar_sql("UPDATE assembleias SET status='Concluída' WHERE id=?", (ass['id'],))
                            st.rerun()
            st.divider()

        st.subheader("Histórico de Atas")
        for ata in atas:
            with st.expander(f"📌 {ata['mes_ano']}"):
                st.write(f"**Data:** {ata['data_completa']} | **Pauta:** {ata['pauta']}")
                col1, col2 = st.columns(2)
                if ata.get('arquivo_dados'):
                    col1.download_button("📄 Baixar Ata", data=bytes(ata['arquivo_dados']), file_name=ata['nome_arquivo'], mime="application/pdf", key=f"d_ata_{ata['id']}")
                if user['perfil'] == "Síndico" and col2.button("🗑️ Excluir", key=f"x_ata_{ata['id']}"):
                    executar_sql("DELETE FROM atas WHERE id=?", (ata['id'],)); st.rerun()

    # --- PRESTAÇÃO DE CONTAS ---
    elif pagina == "Prestação de Contas":
        st.title("📊 Balancetes")
        balancetes = buscar_dados("SELECT * FROM balancetes ORDER BY id DESC")
        
        if user['perfil'] == "Síndico":
            with st.expander("📂 Novo Balancete"):
                with st.form("form_bal", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    mes_sel = col1.selectbox("Mês:", list(MESES_PT.values()))
                    ano_sel = col2.selectbox("Ano:", [2024, 2025, 2026, 2027])
                    arq_bal = st.file_uploader("Documento em PDF", type=["pdf"])
                    if st.form_submit_button("Salvar") and arq_bal:
                        titulo = f"Balancete {mes_sel}/{ano_sel}"
                        executar_sql("INSERT INTO balancetes (titulo, nome_arquivo, arquivo_dados) VALUES (?, ?, ?)", (titulo, arq_bal.name, arq_bal.getvalue())); st.rerun()
            st.divider()
            
        for bal in balancetes:
            st.write(f"**{bal['titulo']}**")
            col1, col2 = st.columns(2)
            if bal.get('arquivo_dados'):
                col1.download_button("📄 Baixar Balancete", data=bytes(bal['arquivo_dados']), file_name=bal['nome_arquivo'], mime="application/pdf", key=f"d_bal_{bal['id']}")
            if user['perfil'] == "Síndico" and col2.button("🗑️ Excluir", key=f"x_bal_{bal['id']}"):
                executar_sql("DELETE FROM balancetes WHERE id=?", (bal['id'],)); st.rerun()
            st.divider()

    # --- MORADORES ---
    elif pagina == "Moradores":
        st.title("👥 Moradores")
        moradores = buscar_dados("SELECT * FROM usuarios WHERE perfil='Morador' ORDER BY casa ASC")
        for m in moradores:
            col1, col2 = st.columns([3, 1])
            col1.write(f"🏠 **Casa {m['casa']}** - {m['nome']}")
            if col2.button("🗑️ Excluir Morador", key=f"x_user_{m['id']}"):
                executar_sql("DELETE FROM usuarios WHERE id=?", (m['id'],)); st.rerun()
            st.divider()

    # --- MULTAS ---
    elif pagina == "Multas" or pagina == "Minhas Multas":
        st.title("🛑 Multas")
        if user['perfil'] == "Síndico":
            with st.expander("➕ Aplicar Multa"):
                moradores = buscar_dados("SELECT * FROM usuarios WHERE perfil='Morador'")
                with st.form("form_multa", clear_on_submit=True):
                    infrator = st.selectbox("Morador Infrator:", [f"Casa {m['casa']} - {m['nome']}" for m in moradores]) if moradores else None
                    motivo = st.text_input("Motivo da Multa:")
                    arq_multa = st.file_uploader("Documento em PDF", type=["pdf"])
                    if st.form_submit_button("Aplicar") and infrator and motivo and arq_multa:
                        num_casa = infrator.split(" - ")[0].replace("Casa ", "")
                        hoje = datetime.datetime.now().strftime("%d/%m/%Y")
                        executar_sql("INSERT INTO multas (casa, motivo, data_aplicacao, nome_arquivo, arquivo_dados) VALUES (?, ?, ?, ?, ?)", (num_casa, motivo, hoje, arq_multa.name, arq_multa.getvalue())); st.rerun()
            
            st.subheader("Histórico")
            for m in buscar_dados("SELECT * FROM multas ORDER BY id DESC"):
                st.write(f"🏠 **Casa {m['casa']}** | {m['data_aplicacao']} - {m['motivo']}")
                col1, col2 = st.columns(2)
                if m.get('arquivo_dados'):
                    col1.download_button("📄 Baixar Documento", data=bytes(m['arquivo_dados']), file_name=m['nome_arquivo'], mime="application/pdf", key=f"d_multa_{m['id']}")
                if col2.button("🗑️ Cancelar Multa", key=f"x_multa_{m['id']}"):
                    executar_sql("DELETE FROM multas WHERE id=?", (m['id'],)); st.rerun()
                st.divider()
        else:
            minhas_multas = buscar_dados("SELECT * FROM multas WHERE casa=? ORDER BY id DESC", (user['casa'],))
            if not minhas_multas: st.success("🎉 Parabéns! Nenhuma multa registrada para a sua casa.")
            for m in minhas_multas:
                st.error(f"⚠️ {m['motivo']}")
                if m.get('arquivo_dados'):
                    st.download_button("📄 Baixar Boleto da Multa", data=bytes(m['arquivo_dados']), file_name=m['nome_arquivo'], mime="application/pdf", key=f"d_minha_{m['id']}")
                st.divider()