"""
Módulo de Autenticação para Dashboard BI
Sistema de login seguro com bcrypt e session management
"""
import bcrypt
import streamlit as st
from typing import Optional, Dict
import json
from pathlib import Path
import base64
import os


class AuthManager:
    """Gerenciador de autenticação com bcrypt"""
    
    def __init__(self, credentials_file: str = "credentials.json"):
        self.credentials_file = Path(credentials_file)
        self.users = self._load_credentials()
    
    def _load_credentials(self) -> Dict:
        """Carrega credenciais do arquivo JSON ou Streamlit Secrets"""
        try:
            if hasattr(st, 'secrets') and 'credentials' in st.secrets:
                credentials_section = st.secrets['credentials']
                
                creds = {}
                for username in credentials_section:
                    user_data = credentials_section[username]
                    creds[username] = {
                        'password': str(user_data['password']),
                        'name': str(user_data['name']),
                        'role': str(user_data['role'])
                    }
                
                if creds:
                    return creds
        except Exception:
            pass
        
        if self.credentials_file.exists():
            try:
                with open(self.credentials_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return {}
        
        if self.credentials_file.exists():
            st.info("📂 Carregando do arquivo local...")
            try:
                with open(self.credentials_file, 'r', encoding='utf-8') as f:
                    creds = json.load(f)
                    st.success(f"✅ {len(creds)} usuário(s) carregado(s) do arquivo!")
                    return creds
            except Exception as e:
                st.error(f"❌ Erro ao ler arquivo: {e}")
        
        st.error("❌ Nenhuma credencial carregada!")
        return {}
    
    def _save_credentials(self):
        """Salva credenciais no arquivo JSON"""
        with open(self.credentials_file, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, indent=4, ensure_ascii=False)
    
    def hash_password(self, password: str) -> str:
        """Gera hash bcrypt da senha"""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verifica se a senha corresponde ao hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False
    
    def authenticate(self, username: str, password: str) -> bool:
        """Autentica usuário"""
        if username not in self.users:
            return False
        
        stored_hash = self.users[username]['password']
        return self.verify_password(password, stored_hash)
    
    def add_user(self, username: str, password: str, name: str, role: str = "user"):
        """Adiciona novo usuário ao sistema"""
        if username in self.users:
            return False
        
        self.users[username] = {
            "password": self.hash_password(password),
            "name": name,
            "role": role
        }
        self._save_credentials()
        return True
    
    def get_user_info(self, username: str) -> Optional[Dict]:
        """Retorna informações do usuário (sem a senha)"""
        if username not in self.users:
            return None
        
        user_info = self.users[username].copy()
        user_info.pop('password', None)
        return user_info


def init_session_state():
    """Inicializa variáveis de sessão"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None


def logout():
    """Realiza logout do usuário"""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.user_info = None
    st.rerun()


def get_image_base64(image_path: Path) -> str:
    """Converte imagem para base64 para embedding no HTML"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return ""


def login_form(auth_manager: AuthManager, logo_path: str = "data/Vector.png"):
    """Renderiza formulário de login minimalista com logo"""
    
    # Tenta carregar a logo
    logo_file = Path(logo_path)
    if not logo_file.exists():
        # Tenta outros formatos comuns
        for ext in ['.jpg', '.jpeg', '.png']:
            test_path = Path(str(logo_file).rsplit('.', 1)[0] + ext)
            if test_path.exists():
                logo_file = test_path
                break
    
    logo_b64 = ""
    if logo_file.exists():
        logo_b64 = get_image_base64(logo_file)
    
    # CSS customizado - Design minimalista e clean
    st.markdown("""
    <style>
    /* Remove padding padrão */
    .block-container {
        padding-top: 2rem;
        max-width: 600px;
    }
    
    /* Container principal */
    .login-wrapper {
        max-width: 480px;
        margin: 3rem auto;
        padding: 0;
    }
    
    /* Logo e título integrados */
    .logo-section {
        text-align: center;
        margin-bottom: 2.5rem;
    }
    
    .logo-section img {
        max-width: 400px;
        width: 100%;
        height: auto;
        margin-bottom: 1.5rem;
    }
    
    .login-divider {
        height: 1px;
        background: linear-gradient(to right, transparent, #e0e0e0, transparent);
        margin: 2rem 0;
    }
    
    /* Card do formulário - neutro e clean */
    .login-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 2.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    .login-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .login-header h2 {
        color: #1f2937;
        font-size: 1.5rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    
    .login-header p {
        color: #6b7280;
        font-size: 0.95rem;
        margin: 0;
    }
    
    /* Inputs estilizados */
    .stTextInput > div > div > input {
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 0.95rem;
        border: 1.5px solid #d1d5db;
        background: #fafafa;
        transition: all 0.2s;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #3b82f6;
        background: white;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    .stTextInput > label {
        color: #374151;
        font-weight: 500;
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
    }
    
    /* Botão de login */
    .stButton > button {
        width: 100%;
        background: #3b82f6 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px;
        padding: 12px;
        font-size: 1rem;
        font-weight: 600;
        margin-top: 1.5rem;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        background: #2563eb !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        color: #6b7280;
        font-size: 0.9rem;
    }
    
    /* Alertas */
    .stAlert {
        border-radius: 8px;
        border-left: 4px solid;
    }
    
    /* Footer */
    .login-footer {
        text-align: center;
        margin-top: 2rem;
        color: #9ca3af;
        font-size: 0.85rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Layout centralizado
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col2:
        st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)
        
        # Logo centralizada
        if logo_b64:
            st.markdown(f'''
            <div class="logo-section">
                <img src="data:image/png;base64,{logo_b64}" alt="Logo" />
            </div>
            ''', unsafe_allow_html=True)
        
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Formulário de login
        with st.form("login_form"):
            username = st.text_input(
                "Usuário", 
                placeholder="Digite seu usuário",
                key="login_username"
            )
            password = st.text_input(
                "Senha", 
                type="password", 
                placeholder="Digite sua senha",
                key="login_password"
            )
            
            submit = st.form_submit_button("Entrar", use_container_width=True)
            
            if submit:
                if not username or not password:
                    st.error("❌ Por favor, preencha todos os campos")
                    return False
                
                if auth_manager.authenticate(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.user_info = auth_manager.get_user_info(username)
                    st.success("✅ Login realizado com sucesso!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos")
                    return False
        
        # Ajuda
        with st.expander("Precisa de ajuda?"):
            st.markdown("""
            **Primeiro acesso:**  
            Entre em contato com o administrador do sistema.
            
            **Esqueceu a senha:**  
            Contate o suporte técnico da Secretaria.
            
            **Suporte:**  
            📧 suporte@saude.pe.gov.br  
            📞 (81) 3181-XXXX
            """)
        
        # Rodapé
        st.markdown('''
        <div class="login-footer">
            <p>🔒 Conexão segura • © 2025 Secretaria da Saúde - Governo de Pernambuco</p>
        </div>
        ''', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    return False


def require_authentication(auth_manager: AuthManager, logo_path: str = "data/Vector.png"):
    """Decorator/wrapper para proteger páginas"""
    init_session_state()
    
    if not st.session_state.authenticated:
        login_form(auth_manager, logo_path)
        st.stop()
    
    return True
