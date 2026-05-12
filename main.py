#!/usr/bin/env python3
"""
Entry point - Azure DevOps User Story to Specs Converter
Pode ser executado manualmente ou por agendador
"""

import sys
import logging
from datetime import datetime

# Importar configuração e sync
try:
    from config import LOG_FILE
    from azure_sync import main as run_sync
except ImportError as e:
    print(f"❌ Erro ao importar módulos: {e}")
    print("Execute: pip install -r requirements.txt")
    sys.exit(1)

# Configurar logging
logger = logging.getLogger(__name__)


def main():
    """Executa a sincronização"""
    print("\n" + "=" * 60)
    print("🤖 Azure DevOps Auto Sync - User Stories to Specs")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60 + "\n")

    try:
        result = run_sync()
        
        print("\n" + "=" * 60)
        print("📊 RESULTADO FINAL")
        print(f"   ✓ Arquivos criados: {result.get('processed', 0)}")
        print(f"   ⊘ Pulados: {result.get('skipped', 0)}")
        print(f"   📦 Total processado: {result.get('total', 0)}")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ ERRO: {e}")
        print("=" * 60)
        print(f"\n📝 Verifique o log em: {LOG_FILE}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
