import bcrypt
import json
from pathlib import Path

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def create_user(username: str, password: str, name: str, role: str = "user"):
    
    credentials_file = Path("credentials.json")

    if credentials_file.exists():
        with open(credentials_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
    else:
        users = {}

    if username in users:
        print(f"❌ Usuário '{username}' já existe!")
        return False
    
    users[username] = {
        "password": hash_password(password),
        "name": name,
        "role": role
    }

    with open(credentials_file, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Usuário '{username}' criado com sucesso!")
    return True

def list_users():
    credentials_file = Path("credentials.json")

    if not credentials_file.exists():
        print("Nenhum usuário encontrado.")
        return

    with open(credentials_file, 'r', encoding='utf-8') as f:
        users = json.load(f)

    print("\n" + "="*60)
    print("USUÁRIOS CADASTRADOS:")
    print("="*60)
    
    for username, info in users.items():
        print(f"\n👤 Usuário: {username}")
        print(f"   Nome: {info['name']}")
        print(f"   Perfil: {info['role']}")
    
    print("\n" + "="*60)

def delete_user(username: str):
    credentials_file = Path("credentials.json")

    if not credentials_file.exists():
        print("Nenhum usuário encontrado.")
        return False

    with open(credentials_file, 'r', encoding='utf-8') as f:
        users = json.load(f)

    if username not in users:
        print(f"❌ Usuário '{username}' não encontrado!")
        return False

    del users[username]

    with open(credentials_file, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Usuário '{username}' deletado com sucesso!")
    return True

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔐 GERENCIADOR DE USUÁRIOS - BI DASHBOARD")
    print("Secretaria da Saúde - Governo de Pernambuco")
    print("="*60)
    
    while True:
        print("\n📋 MENU:")
        print("1 - Criar novo usuário")
        print("2 - Listar usuários")
        print("3 - Remover usuário")
        print("4 - Criar usuários padrão (exemplo)")
        print("0 - Sair")
        
        opcao = input("\nEscolha uma opção: ").strip()
        
        if opcao == "1":
            print("\n📝 CRIAR NOVO USUÁRIO")
            username = input("Usuário (login): ").strip()
            password = input("Senha: ").strip()
            name = input("Nome completo: ").strip()
            role = input("Perfil (admin/user) [user]: ").strip() or "user"
            
            if username and password and name:
                create_user(username, password, name, role)
            else:
                print("❌ Todos os campos são obrigatórios!")
        
        elif opcao == "2":
            list_users()
        
        elif opcao == "3":
            print("\n🗑️ REMOVER USUÁRIO")
            username = input("Usuário para remover: ").strip()
            if username:
                confirma = input(f"Confirma remoção de '{username}'? (s/n): ").strip().lower()
                if confirma == 's':
                    delete_user(username)
        
        elif opcao == "4":
            print("\n🚀 CRIANDO USUÁRIOS PADRÃO...")
            create_user("admin", "Admin@2025!", "Administrador do Sistema", "admin")
            create_user("gestor", "Gestor@2025!", "Gestor de Saúde", "user")
            create_user("analista", "Analista@2025!", "Analista BI", "user")
            print("\n✅ Usuários padrão criados!")
            print("⚠️ IMPORTANTE: Altere as senhas após o primeiro login!")
        
        elif opcao == "0":
            print("\n👋 Até logo!")
            break
        
        else:
            print("❌ Opção inválida!")