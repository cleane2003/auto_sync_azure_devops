# 🤖 Azure DevOps Auto Sync - User Stories to Specs

Automação que lê user stories da coluna **"Agent Ready"** no Azure DevOps e cria arquivos specs em Markdown na pasta `docs` do seu projeto.

## 📋 O que faz

✅ Acessa Azure DevOps via API  
✅ Filtra user stories na coluna "Agent Ready"  
✅ Lê título, descrição e critérios de aceitação  
✅ Gera arquivos `.md` formatados  
✅ Salva em `C:\Projects\deliflow-monorepo\docs\specs\`  
✅ Pode rodar manualmente ou agendado  

## 🚀 Instalação

### 1️⃣ Pré-requisitos

- Python 3.8+
- Azure DevOps Personal Access Token (PAT)
- Acesso à organização `mosten-core`

### 2️⃣ Configurar Credenciais

1. Crie o arquivo `.env` na pasta `auto_sync`:

```bash
cd c:\Projects\Suporte\auto_sync
cp .env.example .env
```

2. Edite `.env` com suas credenciais:

```env
AZURE_ORG=mosten-core
AZURE_PROJECT=ALO001-26
AZURE_PAT=SEU_TOKEN_AQUI
AZURE_EMAIL=cleane.batista@mosten.com
DOCS_FOLDER=C:\Projects\deliflow-monorepo\docs
COLUMN_NAME=Agent Ready
```

### 3️⃣ Instalar Dependências

```bash
pip install -r requirements.txt
```

## 📖 Uso

### ▶️ Execução Manual

```bash
python main.py
```

Saída esperada:
```
============================================================
🤖 Azure DevOps Auto Sync - User Stories to Specs
⏰ 2026-05-12 14:30:45
============================================================

✅ Configuração carregada:
   - Organização: mosten-core
   - Projeto: ALO001-26
   - Pasta de saída: C:\Projects\deliflow-monorepo\docs\specs
   - Coluna monitorada: Agent Ready

🚀 Iniciando sincronização...
   ✓ 5 user stories encontradas

✅ SINCRONIZAÇÃO CONCLUÍDA
   ✓ Specs criados: 5
   ⊘ Pulados: 0
   📁 Pasta: C:\Projects\deliflow-monorepo\docs\specs
```

### ⏰ Agendamento Automático (Windows)

**Instalar tarefa agendada (executar diariamente às 9:00 AM):**

```powershell
# Clique com botao direito no PowerShell -> "Executar como Administrador"
powershell -ExecutionPolicy Bypass -File "C:\Projects\Suporte\auto_sync\scheduler.ps1" -Action Install -Frequency Daily -Hour 9
```

**Outras opções:**

```powershell
# Executar a cada hora
powershell -ExecutionPolicy Bypass -File "C:\Projects\Suporte\auto_sync\scheduler.ps1" -Action Install -Frequency Hourly

# Executar toda segunda-feira as 14:00
powershell -ExecutionPolicy Bypass -File "C:\Projects\Suporte\auto_sync\scheduler.ps1" -Action Install -Frequency Weekly -Hour 14

# Remover a tarefa agendada
powershell -ExecutionPolicy Bypass -File "C:\Projects\Suporte\auto_sync\scheduler.ps1" -Action Uninstall

# Executar manualmente via PowerShell
powershell -ExecutionPolicy Bypass -File "C:\Projects\Suporte\auto_sync\scheduler.ps1" -Action Run
```

## 📂 Estrutura de Arquivos

```
auto_sync/
├── main.py                 # Entry point
├── azure_sync.py           # Lógica principal
├── config.py               # Configurações
├── scheduler.ps1           # Agendador Windows
├── requirements.txt        # Dependências Python
├── .env                    # Credenciais (não commitar!)
├── .env.example            # Template de .env
├── README.md               # Este arquivo
└── logs/
    ├── sync.log           # Log de sincronizações
    └── scheduler.log      # Log do agendador
```

## 📝 Formato dos Specs Gerados

Cada arquivo `.md` contém:

```markdown
# Spec: [Título da User Story]

**ID:** 12345
**Status:** Active
**Atribuído a:** Dev Name
**Data de Criação:** 2026-05-12

---

## 📋 Objetivo
[Descrição da user story]

---

## ✅ Critérios de Aceitação
- Critério 1
- Critério 2
- Critério 3

---

## 📝 Detalhes Técnicos
[...informações técnicas...]

---

**Gerado em:** 2026-05-12 14:30:45
```

## 🔑 Gerar Personal Access Token (PAT)

1. Acesse: https://dev.azure.com/mosten-core/_usersSettings/tokens
2. Clique em **"New Token"**
3. Configure:
   - **Name:** `AutoSync`
   - **Organization:** `mosten-core`
   - **Expiration:** 1 year
   - **Scopes:** `Work Items (Read)`
4. Clique em **"Create"**
5. **Copie o token** (só aparece uma vez!)
6. Cole no arquivo `.env`

## 📊 Logs

Os logs são salvos em:
- **Sincronizações:** `logs/sync.log`
- **Agendador:** `logs/scheduler.log`

Acompanhe em tempo real:
```bash
tail -f logs/sync.log
```

## 🐛 Troubleshooting

### Erro: "AZURE_PAT não configurado"
→ Configure o arquivo `.env` (veja seção de configuração acima)

### Erro: "401 Unauthorized"
→ PAT expirou ou email está errado. Gere um novo PAT.

### Erro: "Nenhuma user story encontrada"
→ Verifique se há user stories na coluna "Agent Ready"  
→ Confirme que a coluna se chama exatamente "Agent Ready" (case-sensitive)

### Specs não aparecem na pasta
→ Verifique o caminho em `.env` (deve existir a pasta `C:\Projects\deliflow-monorepo\docs`)  
→ Verifique permissões de escrita

## 🔐 Segurança

⚠️ **NUNCA commitar `.env` com credenciais reais!**

- `.env` está no `.gitignore`
- Use `.env.example` como template
- Rotacione PATs regularmente
- Use tokens com escopo mínimo (apenas "Work Items - Read")

## 📞 Suporte

Para problemas:
1. Verifique o log em `logs/sync.log`
2. Confirme configurações em `.env`
3. Teste a conexão: `python -c "import config"`
4. Verifique conectividade: `ping dev.azure.com`

## 📈 Próximas Melhorias

- [ ] Webhook em vez de polling (atualização em tempo real)
- [ ] Suporte a múltiplas colunas
- [ ] Versionamento de specs
- [ ] Sincronização bidirecional
- [ ] Dashboard web

---

**Versão:** 1.0.0  
**Última atualização:** 2026-05-12
