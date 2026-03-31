"""
run_migration.py — Executa a migração SQL no Supabase
------------------------------------------------------
Este script lê o arquivo create_rd_tables.sql e executa
cada comando no banco de dados Supabase via conexão direta
com PostgreSQL (usando psycopg2).

Uso:
  cd backend && python3 scripts/run_migration.py
"""

import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_settings

settings = get_settings()

def run_migration():
    try:
        import psycopg2
    except ImportError:
        print("❌ psycopg2 não instalado. Execute: pip install psycopg2-binary")
        sys.exit(1)

    # Monta a connection string do Supabase
    # Formato: postgresql://postgres:[SERVICE_KEY]@db.[PROJECT_REF].supabase.co:5432/postgres
    # Extrai o project ref da URL
    supabase_url = settings.supabase_url
    project_ref = supabase_url.replace("https://", "").replace(".supabase.co", "")

    # Usa a service_role key como senha do PostgreSQL
    # No Supabase, a senha do banco é configurada separadamente
    # Vamos usar a API REST para executar o SQL via rpc
    print("🔌 Conectando ao Supabase via API REST...")

    from supabase import create_client
    client = create_client(settings.supabase_url, settings.supabase_service_key)

    # Lê o arquivo SQL
    sql_file = os.path.join(os.path.dirname(__file__), "create_rd_tables.sql")
    with open(sql_file, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Remove comentários de linha e blocos vazios
    # Divide por ; para executar comando por comando
    statements = []
    current = []

    for line in sql_content.split("\n"):
        stripped = line.strip()
        # Ignora linhas de comentário puro
        if stripped.startswith("--"):
            continue
        current.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(current).strip()
            if stmt and stmt != ";":
                statements.append(stmt)
            current = []

    print(f"📋 {len(statements)} comandos SQL encontrados\n")

    # Executa via Supabase RPC (função exec_sql)
    # Como o Supabase não tem exec_sql por padrão, vamos usar
    # a conexão direta via psycopg2 com a URL de conexão do Supabase
    print("⚙️  Tentando conexão direta via PostgreSQL...")

    # URL de conexão direta do Supabase
    # Disponível em: Settings → Database → Connection string
    db_host = f"db.{project_ref}.supabase.co"
    db_port = 5432
    db_name = "postgres"
    db_user = "postgres"

    # A senha do banco é diferente das API keys
    # Precisa ser configurada no .env como SUPABASE_DB_PASSWORD
    db_password = os.environ.get("SUPABASE_DB_PASSWORD", "")

    if not db_password:
        print("\n⚠️  SUPABASE_DB_PASSWORD não configurada no .env")
        print("   Para executar a migração diretamente, adicione ao .env:")
        print("   SUPABASE_DB_PASSWORD=sua_senha_do_banco")
        print("\n   Alternativa: execute o SQL manualmente no Supabase:")
        print("   1. Acesse supabase.com → seu projeto → SQL Editor")
        print("   2. Cole o conteúdo do arquivo: backend/scripts/create_rd_tables.sql")
        print("   3. Clique em 'Run'\n")

        # Salva o SQL para facilitar execução manual
        print("📄 Conteúdo do SQL para copiar:")
        print("=" * 60)
        with open(sql_file, "r") as f:
            content = f.read()
            # Remove comentários para ficar mais limpo
            lines = [l for l in content.split("\n") if not l.strip().startswith("--")]
            clean = "\n".join(lines)
            # Remove linhas em branco duplas
            while "\n\n\n" in clean:
                clean = clean.replace("\n\n\n", "\n\n")
            print(clean[:3000] + "..." if len(clean) > 3000 else clean)
        return False

    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password,
            sslmode="require",
        )
        conn.autocommit = True
        cursor = conn.cursor()

        success = 0
        errors = 0

        for i, stmt in enumerate(statements, 1):
            # Pega primeira linha para identificar o comando
            first_line = stmt.split("\n")[0][:80]
            try:
                cursor.execute(stmt)
                print(f"  ✅ [{i:02d}] {first_line}")
                success += 1
            except Exception as e:
                err_msg = str(e).split("\n")[0]
                if "already exists" in err_msg.lower():
                    print(f"  ⏭️  [{i:02d}] Já existe: {first_line}")
                    success += 1
                else:
                    print(f"  ❌ [{i:02d}] Erro: {err_msg}")
                    errors += 1

        cursor.close()
        conn.close()

        print(f"\n{'='*60}")
        print(f"✅ Migração concluída: {success} sucesso, {errors} erros")
        return errors == 0

    except Exception as e:
        print(f"\n❌ Erro de conexão: {e}")
        print("\n   Verifique a senha do banco em: supabase.com → Settings → Database")
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
