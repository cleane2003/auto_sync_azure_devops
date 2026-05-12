# 🔑 COMO GERAR UM NOVO PERSONAL ACCESS TOKEN (PAT)

## ⚠️ Seu PAT atual não está funcionando
Status: 401 Unauthorized

Isso pode significar que:
- ❌ O token expirou
- ❌ O token foi rejeitado  
- ❌ O token não tem as permissões corretas

## 📝 Gerar Novo Token (Passo a Passo)

### 1️⃣ Acesse a página de tokens

   Abra no navegador:
   https://dev.azure.com/mosten-core/_usersSettings/tokens

   (Ou: Settings → Personal access tokens)

### 2️⃣ Clique em "New Token"

### 3️⃣ Preencha os dados:

   ✓ **Name:** AutoSync-Reader
   ✓ **Organization:** mosten-core  
   ✓ **Expiration:** 180 days (ou 1 year se preferir)
   ✓ **Scopes:** Clique em "Custom defined" e selecione:
   
     - ✓ Work Items
       - ✓ Read
     
   (Deixe outras desmarcadas)

### 4️⃣ Clique "Create"

### 5️⃣ ⚡ CÓPIA RÁPIDA

   Você verá uma tela com o novo token.
   **Copie-o AGORA** (ele só aparece uma vez!)

   Exemplo:
   ```
   abcd1234efgh5678ijkl90mnopqrst
   ```

### 6️⃣ Atualize o arquivo .env

   Abra: c:\Projects\Suporte\auto_sync\.env
   
   Altere esta linha:
   ```
   AZURE_PAT=SEU_NOVO_TOKEN_AQUI
   ```
   
   Para (por exemplo):
   ```
   AZURE_PAT=abcd1234efgh5678ijkl90mnopqrst
   ```

### 7️⃣ Teste novamente

   Execute no terminal:
   ```
   cd c:\Projects\Suporte\auto_sync
   python verify.py
   ```
   
   Deve mostrar: ✅ Tudo pronto!

## ❓ Problemas ao criar?

- **Erro "User not found"**
  → Verifique se está logado como cleane.batista@mosten.com

- **Não encontra Organization**
  → Clique em "Full history" para ver todas as orgs

- **Token aparece vazio**
  → Refaça o processo, o token é gerado uma única vez

## 🔐 Segurança

⚠️ **NEM compartilhe seu PAT**
- Nunca commite .env no git
- Token ativo = Acesso à sua conta
- Se vazar, revogue em: Settings → Personal access tokens

## ✅ Token criado?

Volte para:
```
cd c:\Projects\Suporte\auto_sync
python verify.py
```

Se ainda der erro, tente:
```
python main.py
```

E verifique o log:
```
type logs\sync.log
```
