#!/usr/bin/env python3
"""
Script de Verificação - Testa a configuração e conectividade
"""

import sys
import requests
from pathlib import Path
from datetime import datetime

print("\n" + "=" * 60)
print("🔍 Verificação de Configuração - Azure DevOps Auto Sync")
print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60 + "\n")

checks_passed = 0
checks_failed = 0

# Check 1: Imports
print("1️⃣  Verificando imports...")
try:
    from config import (
        AZURE_ORG, AZURE_PROJECT, AZURE_AUTH, SPECS_SUBFOLDER,
        LOG_FILE, COLUMN_NAME
    )
    from azure_sync import AzureDevOpsSync
    print("   ✅ Imports carregados com sucesso\n")
    checks_passed += 1
except Exception as e:
    print(f"   ❌ Erro ao carregar imports: {e}\n")
    checks_failed += 1
    sys.exit(1)

# Check 2: Credentials
print("2️⃣  Verificando credenciais...")
try:
    from config import AZURE_PAT, AZURE_EMAIL
    if not AZURE_PAT or AZURE_PAT == "SEU_TOKEN_AQUI":
        print("   ❌ AZURE_PAT não configurado\n")
        checks_failed += 1
    elif not AZURE_EMAIL or AZURE_EMAIL == "SEU_EMAIL@mosten.com":
        print("   ❌ AZURE_EMAIL não configurado\n")
        checks_failed += 1
    else:
        token_masked = AZURE_PAT[:10] + "..." + AZURE_PAT[-5:]
        print(f"   ✅ Token: {token_masked}")
        print(f"   ✅ Email: {AZURE_EMAIL}\n")
        checks_passed += 1
except Exception as e:
    print(f"   ❌ Erro ao verificar credenciais: {e}\n")
    checks_failed += 1

# Check 3: Output folder
print("3️⃣  Verificando pasta de saída...")
try:
    if not SPECS_SUBFOLDER.exists():
        print(f"   ⚠️  Criando pasta: {SPECS_SUBFOLDER}")
        SPECS_SUBFOLDER.mkdir(parents=True, exist_ok=True)
    print(f"   ✅ Pasta: {SPECS_SUBFOLDER}\n")
    checks_passed += 1
except Exception as e:
    print(f"   ❌ Erro ao verificar pasta: {e}\n")
    checks_failed += 1

# Check 4: Azure DevOps connectivity
print("4️⃣  Verificando conectividade com Azure DevOps...")
try:
    from config import AZURE_API_URL, AZURE_AUTH
    # Usa WIQL (endpoint válido via POST) para validar acesso ao projeto
    response = requests.post(
        f"{AZURE_API_URL}/wit/wiql",
        auth=AZURE_AUTH,
        params={"api-version": "7.1"},
        json={
            "query": "SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = @project"
        }
    )
    if response.status_code == 401:
        print("   ❌ Erro de autenticação (401). Verifique PAT e Email\n")
        checks_failed += 1
    elif response.status_code == 403:
        print("   ❌ Acesso negado (403). Verifique permissões\n")
        checks_failed += 1
    elif response.status_code == 200:
        print(f"   ✅ Conectado com sucesso")
        print(f"   ✅ Organização: {AZURE_ORG}")
        print(f"   ✅ Projeto: {AZURE_PROJECT}\n")
        checks_passed += 1
    elif response.status_code == 404:
        print("   ❌ Recurso não encontrado (404). Verifique organização/projeto no .env\n")
        checks_failed += 1
    else:
        print(f"   ⚠️  Status inesperado: {response.status_code}")
        print(f"   ⚠️  Resposta: {response.text[:200]}\n")
        checks_failed += 1
except requests.exceptions.ConnectionError:
    print("   ❌ Erro de conexão. Verifique sua internet\n")
    checks_failed += 1
except Exception as e:
    print(f"   ❌ Erro ao conectar: {e}\n")
    checks_failed += 1

# Check 5: Log file
print("5️⃣  Verificando log...")
try:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    print(f"   ✅ Log: {LOG_FILE}\n")
    checks_passed += 1
except Exception as e:
    print(f"   ❌ Erro ao verificar log: {e}\n")
    checks_failed += 1

# Check 6: Column name
print("6️⃣  Verificando coluna monitorada...")
print(f"   ℹ️  Coluna: {COLUMN_NAME}")
print(f"   ℹ️  Especifique em .env se for diferente\n")
checks_passed += 1

# Summary
print("=" * 60)
print("📊 RESULTADO DA VERIFICAÇÃO")
print(f"   ✅ Sucessos: {checks_passed}")
print(f"   ❌ Erros: {checks_failed}")
print("=" * 60)

if checks_failed == 0:
    print("\n🎉 Tudo pronto! Execute: python main.py\n")
    sys.exit(0)
else:
    print(f"\n⚠️  {checks_failed} problema(s) encontrado(s). Corrija antes de prosseguir.\n")
    sys.exit(1)
