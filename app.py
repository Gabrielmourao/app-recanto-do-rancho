import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import datetime

# Configuração da página - Inicia com a aba lateral fechada
st.set_page_config(page_title="Recanto do Rancho", layout="wide", initial_sidebar_state="collapsed")

# Estilo para deixar com cara de App
def aplicar_estilo_app():
    st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        div.stButton > button {
            border-radius: 15px;
            border: 1px solid #e0e0e0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            transition: all 0.2s ease-in-out;
            height: auto;
            padding: 15px 0;
            font-weight: 600;
        }
        div.stButton > button:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 12px rgba(0,0,0,0.1);
            border-color: #0b5394;
            color: #0b5394;
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

# 🚀 OTIMIZAÇÃO DE VELOCIDADE MAXIMA: 
# O cache memoriza a operação para que ela NUNCA se repita enquanto o app estiver no ar
@st.cache_resource
def inicializar_banco():
    try:
        conn = get_conexao()
        cursor = conn.cursor()
        
        # Agrupamos todas as tabelas em um único pacote gigante de dados (1 única viagem ao banco!)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, email TEXT UNIQUE NOT NULL, casa TEXT NOT NULL, senha TEXT NOT NULL, perfil TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS comunicados (id SERIAL PRIMARY KEY, titulo TEXT NOT NULL, mensagem TEXT NOT NULL, data_publicacao TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS assembleias (id SERIAL PRIMARY KEY, data_completa TEXT NOT NULL, mes_ano TEXT NOT NULL, local TEXT NOT NULL, pauta TEXT NOT NULL, status TEXT DEFAULT 'Agendada');
            CREATE TABLE IF NOT EXISTS atas (id SERIAL PRIMARY KEY, mes_ano TEXT NOT NULL, data_completa TEXT NOT NULL, pauta TEXT NOT NULL, nome_arquivo TEXT NOT NULL, arquivo_dados BYTEA);
            CREATE TABLE IF NOT EXISTS reservas (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, casa TEXT NOT NULL, data_reserva TEXT NOT NULL, status TEXT NOT NULL, boleto_nome TEXT, boleto_dados BYTEA, comprovante_nome TEXT, comprovante_dados BYTEA);
            CREATE TABLE IF NOT EXISTS balancetes (id SERIAL PRIMARY KEY, titulo TEXT NOT NULL, nome_arquivo TEXT NOT NULL, arquivo_dados BYTEA);
            CREATE TABLE IF NOT EXISTS multas (id SERIAL PRIMARY KEY, casa TEXT NOT NULL, motivo TEXT NOT NULL, data_aplicacao TEXT NOT NULL, nome_arquivo TEXT NOT NULL, arquivo_dados BYTEA);
            CREATE TABLE IF NOT EXISTS chamados (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, casa TEXT NOT NULL, assunto TEXT NOT NULL, status TEXT DEFAULT 'Aberto', data_criacao TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS respostas (id SERIAL PRIMARY KEY, chamado_id INTEGER NOT NULL, remetente TEXT NOT NULL, texto TEXT NOT NULL, data_envio TEXT NOT NULL);
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
        print(f"Erro na criação inicial do banco: {e}")
        return False

# Chama a função super-rápida (só executa de verdade 1x quando o servidor acorda)
inicializar_banco()

def criar_novo_chamado(nome, casa, assunto, texto, data_envio):
    conn = get_conexao()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chamados (nome, casa, assunto, data_criacao) VALUES (%s, %s, %s, %s) RETURNING id", (nome, casa, assunto, data_envio))
    novo_id = cursor.fetchone()[0]
    cursor.execute("INSERT INTO respostas (chamado_id, remetente, texto, data_envio) VALUES (%s, %s, %s, %s)", (novo_id, nome, texto, data_envio))
    conn.commit()
    cursor.close()
    conn.close()

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
# 3. O APLICATIVO LOGADO
# ==========================================
else:
    user = st.session_state['usuario_logado'] 
    partes_nome = user['nome'].split()
    iniciais = "".join([n[0] for n in partes_nome[:2]]).upper()
    primeiro_nome = partes_nome[0].upper()
    
    if user['perfil'] == "Síndico":
        opcoes_menu = ["Página Inicial", "Comunicados", "Reservas", "Assembleias", "Prestação de Contas", "Moradores", "Multas", "Mensagens"]
    else:
        opcoes_menu = ["Página Inicial", "Comunicados", "Reservas", "Assembleias", "Prestação de Contas", "Falar com o Síndico", "Minhas Multas"]

    st.sidebar.markdown(f"""
    <div style="text-align: center; padding: 10px 0;">
        <div style="background-color: #0b5394; color: white; border-radius: 50%; width: 60px; height: 60px; line-height: 60px; font-size: 22px; font-weight: bold; margin: 0 auto;">
            {iniciais}
        </div>
        <h4 style="margin: 10px 0 0 0; color: #333;">{user['nome'].upper()}</h4>
        <p style="margin: 0; color: gray; font-size: 14px;">Casa: {user['casa']} • Perfil: {user['perfil']}</p>
    </div>
    """, unsafe_allow_html=True)
    st.sidebar.divider()
    
    menu = st.sidebar.radio("Navegação:", opcoes_menu, index=opcoes_menu.index(st.session_state['pagina_atual']), label_visibility="collapsed")
    
    if menu != st.session_state['pagina_atual']:
        st.session_state['pagina_atual'] = menu
        st.rerun()
        
    st.sidebar.divider()
    if st.sidebar.button("Sair (Logout)", use_container_width=True):
        st.session_state['usuario_logado'] = None
        st.rerun()

    pagina = st.session_state['pagina_atual']

    if pagina != "Página Inicial":
        st.button("🏠 Voltar para a Página Inicial", use_container_width=True, on_click=navegar_para, args=("Página Inicial",))
        st.divider()

    # --- PÁGINA INICIAL ---
    if pagina == "Página Inicial":
        st.markdown(f"<h3 style='text-align: center; color: gray; font-weight: normal; margin-bottom: 0;'>Bem-vindo, {primeiro_nome}</h3>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; margin-top: 0;'>Recanto do Rancho</h1>", unsafe_allow_html=True)
        st.write("")
        
        # 🚀 OTIMIZAÇÃO: Botões com on_click navegam instantaneamente sem duplo-carregamento
        col1, col2, col3 = st.columns(3)
        with col1:
            st.button("📢\nComunicados", use_container_width=True, on_click=navegar_para, args=("Comunicados",))
            st.button("📊\nContas", use_container_width=True, on_click=navegar_para, args=("Prestação de Contas",))
            if user['perfil'] == "Síndico":
                st.button("📥\nMensagens", use_container_width=True, on_click=navegar_para, args=("Mensagens",))
        with col2:
            st.button("📅\nReservas", use_container_width=True, on_click=navegar_para, args=("Reservas",))
            st.button("🤝\nAssembleias", use_container_width=True, on_click=navegar_para, args=("Assembleias",))
            if user['perfil'] == "Síndico":
                st.button("👥\nMoradores", use_container_width=True, on_click=navegar_para, args=("Moradores",))
        with col3:
            if user['perfil'] == "Síndico":
                st.button("🛑\nMultas", use_container_width=True, on_click=navegar_para, args=("Multas",))
            else:
                st.button("💬\nFalar c/ Síndico", use_container_width=True, on_click=navegar_para, args=("Falar com o Síndico",))
                st.button("🛑\nMinhas Multas", use_container_width=True, on_click=navegar_para, args=("Minhas Multas",))

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
                    msg_aviso = st.text_area("Assunto / Mensagem")
                    if st.form_submit_button("Publicar no Mural"):
                        if tit_aviso and msg_aviso:
                            data_hoje = datetime.datetime.now().strftime("%d/%m/%Y")
                            executar_sql("INSERT INTO comunicados (titulo, mensagem, data_publicacao) VALUES (?, ?, ?)", (tit_aviso, msg_aviso, data_hoje))
                            st.success("Publicado!")
                            st.rerun()
            st.divider()

        for ass in buscar_dados("SELECT * FROM assembleias WHERE status='Agendada'"):
            st.warning(f"🚨 **CONVOCAÇÃO:** {ass['data_completa']}\n\n**Local:** {ass['local']} | **Pauta:** {ass['pauta']}")

        avisos = buscar_dados("SELECT * FROM comunicados ORDER BY id DESC")
        if not avisos: st.write("Nenhum comunicado.")
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
            st.subheader("Painel de Solicitações e Pagamentos")
            pendentes = [r for r in reservas_gerais if r['status'] in ["Aguardando Taxa", "Em Análise", "Aguardando Pagamento"]]
            
            if not pendentes: st.write("Nenhuma ação pendente no momento.")
            for r in pendentes:
                with st.expander(f"📌 {r['data_reserva']} - {r['nome']} (Casa {r['casa']}) | Status: {r['status']}", expanded=True):
                    if r['status'] == "Aguardando Taxa":
                        st.info("O morador solicitou esta data. Envie o boleto/chave Pix para ele pagar.")
                        arq_boleto = st.file_uploader("Upload do Boleto/Pix (PDF ou Imagem)", key=f"up_bol_{r['id']}")
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
                            executar_sql("UPDATE reservas SET status='Aprovada' WHERE id=?", (r['id'],)); st.rerun()
                        if col2.button("❌ Reprovar / Cancelar", key=f"rep_{r['id']}"):
                            executar_sql("UPDATE reservas SET status='Reprovada' WHERE id=?", (r['id'],)); st.rerun()
            st.divider()
            st.subheader("Histórico Completo")
            for r in reservas_gerais:
                st.write(f"**{r['data_reserva']}** | {r['nome']} (Casa {r['casa']}) | Status: {r['status']}")

        else: # Morador
            st.subheader("Minhas Solicitações")
            minhas_reservas = buscar_dados("SELECT * FROM reservas WHERE casa=? ORDER BY id DESC", (user['casa'],))
            if not minhas_reservas: st.write("Você não tem solicitações.")
            
            for r in minhas_reservas:
                with st.container():
                    if r['status'] == "Aprovada": st.success(f"📅 {r['data_reserva']} | APROVADA - Churrasqueira liberada!")
                    elif r['status'] == "Reprovada": st.error(f"📅 {r['data_reserva']} | REPROVADA - Cancelada pela administração.")
                    elif r['status'] == "Aguardando Taxa": st.warning(f"📅 {r['data_reserva']} | Aguardando síndico gerar a cobrança.")
                    elif r['status'] == "Em Análise": st.info(f"📅 {r['data_reserva']} | Comprovante enviado! Em análise pela administração.")
                    elif r['status'] == "Aguardando Pagamento":
                        st.error(f"📅 {r['data_reserva']} | PENDENTE DE PAGAMENTO")
                        if r.get('boleto_dados'):
                            st.download_button("📥 1. Baixar Boleto / Chave Pix", data=bytes(r['boleto_dados']), file_name=r['boleto_nome'], key=f"dl_bol_{r['id']}")
                        
                        st.write("Após pagar, envie o comprovante abaixo:")
                        arq_comp = st.file_uploader("2. Enviar Comprovante", key=f"up_comp_{r['id']}")
                        if st.button("Confirmar Pagamento", key=f"btn_comp_{r['id']}"):
                            if arq_comp:
                                executar_sql("UPDATE reservas SET status='Em Análise', comprovante_nome=?, comprovante_dados=? WHERE id=?", (arq_comp.name, arq_comp.getvalue(), r['id']))
                                st.success("Comprovante enviado!"); st.rerun()
                            else: st.error("Anexe o comprovante antes de confirmar.")
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
                        st.success("Enviado! Aguarde a liberação da cobrança."); st.rerun()

    # --- ASSEMBLEIAS ---
    elif pagina == "Assembleias":
        st.title("🤝 Assembleias")
        assembleias = buscar_dados("SELECT * FROM assembleias WHERE status='Agendada'")
        atas = buscar_dados("SELECT * FROM atas ORDER BY id DESC")
        
        if user['perfil'] == "Síndico":
            with st.expander("➕ Agendar Nova"):
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
                            st.rerun()
            
            with st.expander("📂 Publicar Ata"):
                if assembleias:
                    with st.form("form_ata", clear_on_submit=True):
                        opcoes = {f"{a['data_completa']} - {a['pauta']}": a for a in assembleias}
                        escolha = st.selectbox("Assembleia:", list(opcoes.keys()))
                        arq_ata = st.file_uploader("PDF", type=["pdf"])
                        if st.form_submit_button("Publicar") and arq_ata:
                            ass = opcoes[escolha]
                            executar_sql("INSERT INTO atas (mes_ano, data_completa, pauta, nome_arquivo, arquivo_dados) VALUES (?, ?, ?, ?, ?)", (ass['mes_ano'], ass['data_completa'], ass['pauta'], arq_ata.name, arq_ata.getvalue()))
                            executar_sql("UPDATE assembleias SET status='Concluida' WHERE id=?", (ass['id'],))
                            st.rerun()
            st.divider()

        st.subheader("Histórico de Atas")
        for ata in atas:
            with st.expander(f"📌 {ata['mes_ano']}"):
                st.write(f"**Data:** {ata['data_completa']} | **Pauta:** {ata['pauta']}")
                col1, col2 = st.columns(2)
                if ata.get('arquivo_dados'):
                    col1.download_button("📄 Baixar", data=bytes(ata['arquivo_dados']), file_name=ata['nome_arquivo'], mime="application/pdf", key=f"d_ata_{ata['id']}")
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
                    arq_bal = st.file_uploader("PDF", type=["pdf"])
                    if st.form_submit_button("Salvar") and arq_bal:
                        titulo = f"Balancete {mes_sel}/{ano_sel}"
                        executar_sql("INSERT INTO balancetes (titulo, nome_arquivo, arquivo_dados) VALUES (?, ?, ?)", (titulo, arq_bal.name, arq_bal.getvalue())); st.rerun()
            st.divider()
            
        for bal in balancetes:
            st.write(f"**{bal['titulo']}**")
            col1, col2 = st.columns(2)
            if bal.get('arquivo_dados'):
                col1.download_button("📄 Baixar", data=bytes(bal['arquivo_dados']), file_name=bal['nome_arquivo'], mime="application/pdf", key=f"d_bal_{bal['id']}")
            if user['perfil'] == "Síndico" and col2.button("🗑️ Excluir", key=f"x_bal_{bal['id']}"):
                executar_sql("DELETE FROM balancetes WHERE id=?", (bal['id'],)); st.rerun()
            st.divider()

    # --- COMUNICAÇÃO (BATE-PAPO) ---
    elif pagina == "Falar com o Síndico" or pagina == "Mensagens":
        st.title("💬 Central de Atendimento")
        if st.button("🔄 Atualizar Chat"): st.rerun()
        st.divider()
        
        if user['perfil'] == "Síndico":
            chamados = buscar_dados("SELECT * FROM chamados ORDER BY id DESC")
        else:
            chamados = buscar_dados("SELECT * FROM chamados WHERE casa=? ORDER BY id DESC", (user['casa'],))
            with st.expander("➕ Iniciar Nova Conversa"):
                with st.form("form_novo_chamado", clear_on_submit=True):
                    assunto = st.text_input("Assunto")
                    texto = st.text_area("Primeira Mensagem")
                    if st.form_submit_button("Enviar"):
                        if assunto and texto:
                            hoje = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")
                            criar_novo_chamado(user['nome'], user['casa'], assunto, texto, hoje)
                            st.success("Enviado!"); st.rerun()

        for ch in chamados:
            respostas = buscar_dados("SELECT * FROM respostas WHERE chamado_id=? ORDER BY id ASC", (ch['id'],))
            alerta_nova = ""
            if respostas and ch['status'] == "Aberto":
                ultima_msg = respostas[-1]
                if user['perfil'] == "Síndico" and ultima_msg['remetente'] not in ["Administrador", "Síndico"]: alerta_nova = "🔴 [NOVA] "
                elif user['perfil'] == "Morador" and ultima_msg['remetente'] in ["Administrador", "Síndico"]: alerta_nova = "🔴 [NOVA] "
                    
            status_icone = "🟢" if ch['status'] == "Aberto" else "⚪"
            with st.expander(f"{alerta_nova}{status_icone} {ch['assunto']} - Casa {ch['casa']}"):
                for r in respostas:
                    if r['remetente'] in ["Síndico", "Administrador"]: st.info(f"👔 **Administração** ({r['data_envio']}):\n\n{r['texto']}")
                    else: st.success(f"👤 **{r['remetente']}** ({r['data_envio']}):\n\n{r['texto']}")
                
                if ch['status'] == "Aberto":
                    st.divider()
                    with st.form(key=f"form_resp_{ch['id']}", clear_on_submit=True):
                        texto_resposta = st.text_input("Escreva sua resposta...")
                        col_btn1, col_btn2 = st.columns(2)
                        if col_btn1.form_submit_button("Enviar Resposta") and texto_resposta:
                            hoje = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")
                            executar_sql("INSERT INTO respostas (chamado_id, remetente, texto, data_envio) VALUES (?, ?, ?, ?)", (ch['id'], user['nome'], texto_resposta, hoje))
                            st.rerun()
                            
                    if user['perfil'] == "Síndico" and st.button("🚫 Encerrar Conversa", key=f"btn_encer_{ch['id']}"):
                        executar_sql("UPDATE chamados SET status='Encerrado' WHERE id=?", (ch['id'],)); st.rerun()
                else: st.error("Esta conversa foi encerrada pelo Síndico.")

    # --- MORADORES ---
    elif pagina == "Moradores":
        st.title("👥 Moradores")
        moradores = buscar_dados("SELECT * FROM usuarios WHERE perfil='Morador' ORDER BY casa ASC")
        for m in moradores:
            col1, col2 = st.columns([3, 1])
            col1.write(f"🏠 **Casa {m['casa']}** - {m['nome']}")
            if col2.button("🗑️ Excluir", key=f"x_user_{m['id']}"):
                executar_sql("DELETE FROM usuarios WHERE id=?", (m['id'],)); st.rerun()
            st.divider()

    # --- MULTAS ---
    elif pagina == "Multas" or pagina == "Minhas Multas":
        st.title("🛑 Multas")
        if user['perfil'] == "Síndico":
            with st.expander("➕ Aplicar Multa"):
                moradores = buscar_dados("SELECT * FROM usuarios WHERE perfil='Morador'")
                with st.form("form_multa", clear_on_submit=True):
                    infrator = st.selectbox("Infrator:", [f"Casa {m['casa']} - {m['nome']}" for m in moradores]) if moradores else None
                    motivo = st.text_input("Motivo:")
                    arq_multa = st.file_uploader("PDF", type=["pdf"])
                    if st.form_submit_button("Aplicar") and infrator and motivo and arq_multa:
                        num_casa = infrator.split(" - ")[0].replace("Casa ", "")
                        hoje = datetime.datetime.now().strftime("%d/%m/%Y")
                        executar_sql("INSERT INTO multas (casa, motivo, data_aplicacao, nome_arquivo, arquivo_dados) VALUES (?, ?, ?, ?, ?)", (num_casa, motivo, hoje, arq_multa.name, arq_multa.getvalue())); st.rerun()
            
            st.subheader("Histórico")
            for m in buscar_dados("SELECT * FROM multas ORDER BY id DESC"):
                st.write(f"🏠 **Casa {m['casa']}** | {m['data_aplicacao']} - {m['motivo']}")
                col1, col2 = st.columns(2)
                if m.get('arquivo_dados'):
                    col1.download_button("📄 Baixar", data=bytes(m['arquivo_dados']), file_name=m['nome_arquivo'], mime="application/pdf", key=f"d_multa_{m['id']}")
                if col2.button("🗑️ Cancelar", key=f"x_multa_{m['id']}"):
                    executar_sql("DELETE FROM multas WHERE id=?", (m['id'],)); st.rerun()
                st.divider()
        else:
            minhas_multas = buscar_dados("SELECT * FROM multas WHERE casa=? ORDER BY id DESC", (user['casa'],))
            if not minhas_multas: st.success("🎉 Nenhuma multa para a sua casa.")
            for m in minhas_multas:
                st.error(f"⚠️ {m['motivo']}")
                if m.get('arquivo_dados'):
                    st.download_button("📄 Baixar Boleto", data=bytes(m['arquivo_dados']), file_name=m['nome_arquivo'], mime="application/pdf", key=f"d_minha_{m['id']}")
                st.divider()