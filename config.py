import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

# Azure DevOps Configuration
AZURE_ORG = os.getenv('AZURE_ORG', 'mosten-core')
AZURE_PROJECT = os.getenv('AZURE_PROJECT', 'ALO001-26')
AZURE_PAT = os.getenv('AZURE_PAT')
AZURE_EMAIL = os.getenv('AZURE_EMAIL')

# Validar credenciais
if not AZURE_PAT:
    raise ValueError("AZURE_PAT nao configurado. Configure no arquivo .env")
if not AZURE_EMAIL:
    raise ValueError("AZURE_EMAIL nao configurado. Configure no arquivo .env")

# URLs e endpoints
AZURE_BASE_URL = f"https://dev.azure.com/{AZURE_ORG}"
AZURE_API_URL = f"{AZURE_BASE_URL}/{AZURE_PROJECT}/_apis"
# Autenticação básica para Azure DevOps com PAT.
AZURE_AUTH = ("", AZURE_PAT)

# Output Configuration
DOCS_FOLDER = Path(os.getenv('DOCS_FOLDER', r'C:\Projects\deliflow-monorepo\docs'))
SPECS_SUBFOLDER = DOCS_FOLDER / "specs"
FEATURES_SUBFOLDER = DOCS_FOLDER / "features"

# Ensure output folders exist
SPECS_SUBFOLDER.mkdir(parents=True, exist_ok=True)
FEATURES_SUBFOLDER.mkdir(parents=True, exist_ok=True)

# Execution Configuration
COLUMN_NAME = os.getenv('COLUMN_NAME', 'Agent Ready')
FEATURE_COLUMN = os.getenv('FEATURE_COLUMN', 'In Progress')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
VERBOSE_CONFIG = _env_bool('AZURE_VERBOSE_CONFIG', False)

# Script paths
SCRIPT_DIR = Path(__file__).parent
LOG_FILE = SCRIPT_DIR / 'logs' / 'sync.log'
LOG_FILE.parent.mkdir(exist_ok=True)

if VERBOSE_CONFIG:
    print("Configuracao carregada:")
    print(f"   - Organizacao: {AZURE_ORG}")
    print(f"   - Projeto: {AZURE_PROJECT}")
    print(f"   - Pasta de saida: {SPECS_SUBFOLDER}")
    print(f"   - Pasta de features: {FEATURES_SUBFOLDER}")
    print(f"   - Coluna monitorada: {COLUMN_NAME}")
    print(f"   - Coluna de features: {FEATURE_COLUMN}")
    print(f"   - Autenticacao: PAT ({AZURE_PAT[:10]}...)")
