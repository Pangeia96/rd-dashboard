"""
inspect_supabase.py — Inspeciona a estrutura do Supabase
---------------------------------------------------------
Este script conecta ao Supabase e lista:
1. Todas as tabelas existentes no schema public
2. As colunas da tabela pedidos_consolidados
3. Uma amostra de 3 registros para entender os dados
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client
from config import get_settings

settings = get_settings()

def inspect():
    print("🔌 Conectando ao Supabase...")
    client = create_client(settings.supabase_url, settings.supabase_service_key)
    print(f"✅ Conectado em: {settings.supabase_url}\n")

    # 1. Lista todas as tabelas
    print("=" * 60)
    print("📋 TABELAS EXISTENTES NO SUPABASE:")
    print("=" * 60)
    try:
        result = client.rpc("get_tables_list", {}).execute()
        if result.data:
            for t in result.data:
                print(f"  → {t}")
        else:
            print("  (Nenhuma tabela encontrada via RPC)")
    except Exception as e:
        print(f"  ⚠️  RPC não disponível: {e}")

    # 2. Inspeciona pedidos_consolidados via query direta
    print("\n" + "=" * 60)
    print("📦 ESTRUTURA DE pedidos_consolidados:")
    print("=" * 60)
    try:
        # Busca 1 registro para ver as colunas
        result = client.table("pedidos_consolidado").select("*").limit(1).execute()
        if result.data:
            sample = result.data[0]
            print(f"\n  Total de colunas: {len(sample.keys())}\n")
            for col, val in sample.items():
                tipo = type(val).__name__
                val_preview = str(val)[:60] if val is not None else "NULL"
                print(f"  {col:<35} | {tipo:<10} | {val_preview}")
        else:
            print("  ⚠️  Tabela vazia ou não encontrada")
    except Exception as e:
        print(f"  ❌ Erro: {e}")

    # 3. Conta registros
    print("\n" + "=" * 60)
    print("📊 CONTAGEM DE REGISTROS:")
    print("=" * 60)
    try:
        result = client.table("pedidos_consolidado").select("*", count="exact").limit(1).execute()
        print(f"  Total de pedidos: {result.count:,}")
    except Exception as e:
        print(f"  ❌ Erro ao contar: {e}")

    # 4. Amostra de 3 registros completos
    print("\n" + "=" * 60)
    print("🔍 AMOSTRA DE 3 REGISTROS:")
    print("=" * 60)
    try:
        result = client.table("pedidos_consolidado").select("*").limit(3).execute()
        for i, row in enumerate(result.data, 1):
            print(f"\n  --- Registro {i} ---")
            for col, val in row.items():
                print(f"  {col}: {val}")
    except Exception as e:
        print(f"  ❌ Erro: {e}")

if __name__ == "__main__":
    inspect()
