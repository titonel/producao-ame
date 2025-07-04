import bcrypt
from sqlalchemy import create_engine, text, inspect

# --- Configuração do Banco de Dados SQLite ---
DATABASE_URL = 'sqlite:///producao.db'
engine = create_engine(DATABASE_URL)

def setup_database_and_users():
    """
    Configura a tabela de usuários e cadastra usuários específicos.
    """
    inspector = inspect(engine)
    
    # Verifica se a tabela 'usuarios' existe, e cria se não existir
    if not inspector.has_table('usuarios'):
        print("Tabela 'usuarios' não encontrada. Criando a tabela...")
        with engine.connect() as connection:
            connection.execute(text("""
                CREATE TABLE usuarios (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL
                )
            """))
            connection.commit()
        print("Tabela 'usuarios' criada com sucesso.")
    else:
        print("Tabela 'usuarios' já existe.")

    users_to_add = {
        "admin": "Catarina@2016",
        "jessica.muniz": "Muniz"
    }

    for username, password in users_to_add.items():
        # Verifica se o usuário já existe antes de tentar adicionar
        with engine.connect() as connection:
            result = connection.execute(text("SELECT username FROM usuarios WHERE username = :username"), {"username": username}).fetchone()
            if result:
                print(f"Usuário '{username}' já existe. Ignorando cadastro.")
            else:
                # Gera o hash da senha
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

                # Insere o novo usuário no banco de dados
                with engine.connect() as connection:
                    connection.execute(text("INSERT INTO usuarios (username, password_hash) VALUES (:username, :password_hash)"),
                                       {"username": username, "password_hash": hashed_password})
                    connection.commit()
                print(f"Usuário '{username}' cadastrado com sucesso.")

if __name__ == "__main__":
    setup_database_and_users()
    print("\nProcesso de configuração de usuários concluído.")