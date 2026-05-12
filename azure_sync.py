#!/usr/bin/env python3
"""
Azure DevOps User Story to Markdown Specs Converter
Lê user stories da coluna "Agent Ready" e cria arquivos specs em MD
"""

import logging
import json
import base64
import re
import html
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import requests

from config import (
    AZURE_API_URL, AZURE_AUTH, COLUMN_NAME, SPECS_SUBFOLDER,
    LOG_FILE, LOG_LEVEL
)

# Configurar logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AzureDevOpsSync:
    """Sincroniza user stories do Azure DevOps para specs em MD"""

    def __init__(self):
        self.api_url = AZURE_API_URL
        self.auth = AZURE_AUTH
        self.column_name = COLUMN_NAME
        self.output_folder = SPECS_SUBFOLDER
        self.processed_count = 0
        self.skipped_count = 0

    def get_board_columns(self) -> Dict[str, Any]:
        """Obtém as colunas do board"""
        try:
            url = f"{self.api_url}/work/boards"
            params = {"api-version": "7.1"}
            response = requests.get(url, auth=self.auth, params=params)
            response.raise_for_status()
            logger.info("✅ Boards obtidos com sucesso")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro ao obter boards: {e}")
            raise

    def get_work_items_in_column(self, column_name: str) -> List[Dict[str, Any]]:
        """Obtém work items (user stories) em uma coluna específica"""
        try:
            # Query WIQL para pegar user stories em uma coluna
            wiql_query = f"""
            SELECT [System.Id], [System.Title], [System.Description],
                   [System.State], [System.AssignedTo], [System.CreatedDate],
                   [Microsoft.VSTS.Common.AcceptanceCriteria], 
                   [System.Tags]
            FROM workitems
            WHERE [System.WorkItemType] = 'User Story'
              AND [System.BoardColumn] = '{column_name}'
              AND [System.State] <> 'Done'
            ORDER BY [System.CreatedDate] DESC
            """

            url = f"{self.api_url}/wit/wiql"
            params = {"api-version": "7.1"}
            response = requests.post(
                url,
                auth=self.auth,
                params=params,
                json={"query": wiql_query}
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"{len(data.get('workItems', []))} user stories encontradas em '{column_name}'")
            return data.get('workItems', [])

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro ao obter work items: {e}")
            raise

    def get_work_item_details(self, work_item_id: int) -> Dict[str, Any]:
        """Obtém detalhes completos de um work item"""
        try:
            url = f"{self.api_url}/wit/workitems/{work_item_id}"
            params = {"api-version": "7.1", "$expand": "all"}
            response = requests.get(url, auth=self.auth, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro ao obter detalhes do work item {work_item_id}: {e}")
            raise

    def get_work_item_comments(self, work_item_id: int) -> List[Dict[str, Any]]:
        """Obtém comentários do work item."""
        try:
            url = f"{self.api_url}/wit/workItems/{work_item_id}/comments"
            params = {"api-version": "7.1-preview.3", "$top": 200}
            response = requests.get(url, auth=self.auth, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("comments", [])
        except requests.exceptions.RequestException as e:
            logger.warning(f"Nao foi possivel obter comentarios do item {work_item_id}: {e}")
            return []

    def _extract_functional_spec_from_comments(self, comments: List[Dict[str, Any]]) -> str:
        """Extrai a especificação funcional dos comentários quando houver."""
        if not comments:
            return "Não encontrada nos comentários."

        # Procura da mais recente para a mais antiga.
        for comment in reversed(comments):
            text = comment.get("text", "")
            if not text:
                continue

            normalized = text.lower()
            if (
                "especificação de requisitos funcionais" in normalized
                or "especificacao de requisitos funcionais" in normalized
            ):
                author = comment.get("createdBy", {}).get("displayName", "Autor desconhecido")
                created = comment.get("createdDate", "")
                clean_text = self._clean_html(text)
                return (
                    f"**Origem do comentário:** {author}  \n"
                    f"**Data:** {created}  \n\n"
                    f"{clean_text}"
                )

        return "Não encontrada nos comentários."

    def create_spec_markdown(self, work_item: Dict[str, Any]) -> str:
        """Cria conteúdo Markdown do spec baseado no work item"""
        fields = work_item.get('fields', {})
        
        title = fields.get('System.Title', 'Sem título')
        description = fields.get('System.Description', 'Sem descrição')
        acceptance_criteria = fields.get(
            'Microsoft.VSTS.Common.AcceptanceCriteria',
            'Não especificado'
        )
        assigned_to = fields.get('System.AssignedTo', {})
        assigned_name = assigned_to.get('displayName', 'Não atribuído') if isinstance(assigned_to, dict) else 'Não atribuído'
        created_date = fields.get('System.CreatedDate', '')
        tags = fields.get('System.Tags', '')
        state = fields.get('System.State', '')
        work_item_id = work_item.get('id', '')

        # Busca especificação funcional registrada em comentários.
        comments = self.get_work_item_comments(work_item_id)
        functional_spec_from_comments = self._extract_functional_spec_from_comments(comments)

        # Formatar a descrição (remover HTML se houver)
        description_clean = self._clean_html(description)
        acceptance_criteria_clean = self._clean_html(acceptance_criteria)

        spec_content = f"""# Spec: {title}

**ID:** {work_item_id}  
**Status:** {state}  
**Atribuído a:** {assigned_name}  
**Data de Criação:** {created_date}  
**Tags:** {tags if tags else 'Nenhuma'}

---

## 📋 Objetivo

{description_clean}

---

## ✅ Critérios de Aceitação

{acceptance_criteria_clean}

---

## 📘 Especificação de Requisitos Funcionais (Comentários)

{functional_spec_from_comments}

---

## 📝 Detalhes Técnicos

### Informações do Work Item
- **ID:** {work_item_id}
- **Tipo:** User Story
- **Projeto:** ALO001-26
- **Coluna:** {self.column_name}

### Links
- [Ver no Azure DevOps](https://dev.azure.com/mosten-core/ALO001-26/_workitems/edit/{work_item_id})

---

**Gerado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Origem:** Azure DevOps - {self.column_name}

"""
        return spec_content

    def _clean_html(self, text: str) -> str:
        """Remove tags HTML básicas do texto"""
        if not text:
            return "Não especificado"

        # Decodifica entidades HTML (&nbsp;, &quot;, &amp;...)
        text = html.unescape(text)
        text = text.replace('\xa0', ' ')
        
        # Substituir tags comuns
        text = text.replace('<p>', '').replace('</p>', '\n')
        text = text.replace('<br>', '\n').replace('<br/>', '\n')
        text = text.replace('<ul>', '').replace('</ul>', '')
        text = text.replace('<li>', '- ').replace('</li>', '\n')
        text = text.replace('<strong>', '**').replace('</strong>', '**')
        text = text.replace('<em>', '*').replace('</em>', '*')
        
        # Remover tags residuais
        import re
        text = re.sub(r'<[^>]+>', '', text)
        
        # Limpar espaços em branco
        text = '\n'.join([line.strip() for line in text.split('\n') if line.strip()])
        
        return text if text.strip() else "Não especificado"

    def sanitize_filename(self, filename: str) -> str:
        """Remove caracteres inválidos do nome do arquivo"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename[:200]  # Limitar a 200 caracteres

    def extract_theme_folder(self, title: str) -> str:
        """Extrai o tema da US no formato [USxx - Tema] para usar como pasta."""
        match = re.search(r'\[\s*US\d+\s*-\s*([^\]]+)\]', title, flags=re.IGNORECASE)
        if match:
            return self.sanitize_filename(match.group(1).strip())
        return "Outros"

    def build_output_filename(self, work_item_id: int, title: str) -> str:
        """Gera nome de arquivo preservando o padrão [USxx - Tema] quando existir."""
        safe_title = self.sanitize_filename((title or '').strip())
        if safe_title:
            return f"{safe_title}.md"
        return f"US_{work_item_id}.md"

    def save_spec(self, work_item: Dict[str, Any]) -> bool:
        """Salva o spec em um arquivo MD"""
        try:
            work_item_id = work_item.get('id')
            title = work_item.get('fields', {}).get('System.Title', 'unnamed')

            # Criar subpasta por tema (ex.: "Cadastro de Minha Equipe")
            theme_folder = self.extract_theme_folder(title)
            folder_path = self.output_folder / theme_folder
            folder_path.mkdir(parents=True, exist_ok=True)

            # Criar nome do arquivo: ID_Titulo.md
            filename = self.build_output_filename(work_item_id, title)
            filepath = folder_path / filename
            
            # Gerar conteúdo
            content = self.create_spec_markdown(work_item)
            
            # Salvar arquivo
            filepath.write_text(content, encoding='utf-8')
            logger.info(f"Spec salvo: {filepath}")
            
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar spec para work item {work_item_id}: {e}")
            return False

    def sync(self) -> Dict[str, int]:
        """Executa sincronização completa"""
        logger.info("=" * 60)
        logger.info("Iniciando sincronizacao Azure DevOps -> Specs MD")
        logger.info(f"   Coluna: {self.column_name}")
        logger.info(f"   Pasta de saída: {self.output_folder}")
        logger.info("=" * 60)

        try:
            # Obter work items na coluna
            work_items = self.get_work_items_in_column(self.column_name)
            
            if not work_items:
                logger.warning(f"Nenhuma user story encontrada em '{self.column_name}'")
                return {"processed": 0, "skipped": 0, "total": 0}

            total = len(work_items)
            
            # Processar cada work item
            for idx, item in enumerate(work_items, 1):
                logger.info(f"\nProcessando [{idx}/{total}]: {item.get('id')}")
                
                try:
                    # Obter detalhes completos
                    work_item_details = self.get_work_item_details(item['id'])
                    
                    # Salvar spec
                    if self.save_spec(work_item_details):
                        self.processed_count += 1
                    else:
                        self.skipped_count += 1
                        
                except Exception as e:
                    logger.error(f"Erro ao processar item {item['id']}: {e}")
                    self.skipped_count += 1

            # Resumo
            logger.info("\n" + "=" * 60)
            logger.info("SINCRONIZACAO CONCLUIDA")
            logger.info(f"   Specs criados: {self.processed_count}")
            logger.info(f"   Pulados: {self.skipped_count}")
            logger.info(f"   Pasta: {self.output_folder}")
            logger.info("=" * 60)

            return {
                "processed": self.processed_count,
                "skipped": self.skipped_count,
                "total": total
            }

        except Exception as e:
            logger.error(f"\nERRO CRITICO: {e}")
            raise


def main():
    """Função principal"""
    try:
        sync = AzureDevOpsSync()
        result = sync.sync()
        return result
    except Exception as e:
        logger.error(f"Falha na execucao: {e}")
        raise


if __name__ == "__main__":
    main()
