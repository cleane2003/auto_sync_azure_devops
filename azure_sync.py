#!/usr/bin/env python3
"""
Azure DevOps Feature e User Story to Markdown Sync
Lê features e user stories da coluna "Agent Ready" e cria arquivos MD vinculados
"""

import logging
import json
import base64
import re
import html
import unicodedata
from os.path import relpath
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import quote
import requests

from config import (
    AZURE_API_URL, AZURE_AUTH, COLUMN_NAME, SPECS_SUBFOLDER, FEATURES_SUBFOLDER,
    FEATURE_COLUMN, LOG_FILE, LOG_LEVEL
)

USER_STORY_TYPE = 'User Story'
FEATURE_TYPE = 'Feature'
HIERARCHY_FORWARD = 'System.LinkTypes.Hierarchy-Forward'
HIERARCHY_REVERSE = 'System.LinkTypes.Hierarchy-Reverse'

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
    """Sincroniza features e user stories do Azure DevOps para arquivos MD"""

    def __init__(self):
        self.api_url = AZURE_API_URL
        self.auth = AZURE_AUTH
        self.column_name = COLUMN_NAME
        self.feature_column = FEATURE_COLUMN
        self.output_folder = SPECS_SUBFOLDER
        self.features_folder = FEATURES_SUBFOLDER
        self.processed_count = 0
        self.skipped_count = 0
        self.features_processed_count = 0
        self.features_skipped_count = 0
        self.work_item_cache: Dict[int, Dict[str, Any]] = {}
        self.spec_paths_by_id: Dict[int, Path] = {}
        self.feature_paths_by_id: Dict[int, Path] = {}

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

    def get_work_items_in_column(
        self,
        work_item_type: str,
        column_name: str | None = None,
        state_name: str | None = None
    ) -> List[Dict[str, Any]]:
        """Obtém work items de um tipo específico com filtros opcionais de coluna/estado."""
        try:
            where_clauses = [f"[System.WorkItemType] = '{work_item_type}'"]
            if column_name:
                where_clauses.append(f"[System.BoardColumn] = '{column_name}'")
            if state_name:
                where_clauses.append(f"[System.State] = '{state_name}'")
            else:
                where_clauses.append("[System.State] <> 'Done'")

            where_sql = "\n              AND ".join(where_clauses)

            # Query WIQL para pegar work items de acordo com os filtros.
            wiql_query = f"""
            SELECT [System.Id], [System.Title], [System.Description],
                   [System.State], [System.AssignedTo], [System.CreatedDate],
                   [Microsoft.VSTS.Common.AcceptanceCriteria], 
                   [System.Tags]
            FROM workitems
            WHERE {where_sql}
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
            filter_label = column_name or state_name or "filtro padrão"
            logger.info(f"{len(data.get('workItems', []))} {work_item_type.lower()}s encontradas em '{filter_label}'")
            return data.get('workItems', [])

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro ao obter work items: {e}")
            raise

    def get_work_item_details(self, work_item_id: int) -> Dict[str, Any]:
        """Obtém detalhes completos de um work item"""
        if work_item_id in self.work_item_cache:
            return self.work_item_cache[work_item_id]

        try:
            url = f"{self.api_url}/wit/workitems/{work_item_id}"
            params = {"api-version": "7.1", "$expand": "all"}
            response = requests.get(url, auth=self.auth, params=params)
            response.raise_for_status()
            data = response.json()
            self.work_item_cache[work_item_id] = data
            return data
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

    def _extract_relation_ids(self, work_item: Dict[str, Any], relation_type: str) -> List[int]:
        relations = work_item.get('relations', []) or []
        relation_ids: List[int] = []

        for relation in relations:
            if relation.get('rel') != relation_type:
                continue

            url = relation.get('url', '')
            match = re.search(r'/workItems/(\d+)$', url, flags=re.IGNORECASE)
            if match:
                relation_ids.append(int(match.group(1)))

        return relation_ids

    def _extract_primary_parent_feature(self, work_item: Dict[str, Any]) -> Dict[str, Any] | None:
        parent_ids = self._extract_relation_ids(work_item, HIERARCHY_REVERSE)
        if not parent_ids:
            return None

        parent_details = self.get_work_item_details(parent_ids[0])
        parent_fields = parent_details.get('fields', {})
        if parent_fields.get('System.WorkItemType') != FEATURE_TYPE:
            return None

        return parent_details

    def _extract_child_user_stories(self, work_item: Dict[str, Any]) -> List[Dict[str, Any]]:
        child_ids = self._extract_relation_ids(work_item, HIERARCHY_FORWARD)
        child_user_stories: List[Dict[str, Any]] = []

        for child_id in child_ids:
            child_details = self.get_work_item_details(child_id)
            child_fields = child_details.get('fields', {})
            if child_fields.get('System.WorkItemType') == USER_STORY_TYPE:
                child_user_stories.append(child_details)

        return child_user_stories

    def _build_spec_path(self, work_item_id: int, title: str) -> Path:
        theme_folder = self.extract_theme_folder(title)
        filename = self.build_output_filename(work_item_id, title)
        return self.output_folder / theme_folder / filename

    def _build_feature_path(self, work_item_id: int, title: str) -> Path:
        feature_folder = self.extract_feature_folder(title)
        filename = self.build_feature_output_filename(work_item_id, title)
        return self.features_folder / feature_folder / filename

    def _build_markdown_link(self, label: str, target_path: Path, from_path: Path) -> str:
        relative_path = relpath(target_path, start=from_path.parent)
        relative_posix = Path(relative_path).as_posix()
        encoded_path = "/".join(
            quote(part, safe="._-()") for part in relative_posix.split("/")
        )
        return f"[{label}](<{encoded_path}>)"

    def _build_azure_work_item_link(self, work_item_id: int, label: str) -> str:
        return f"[{label}](https://dev.azure.com/mosten-core/ALO001-26/_workitems/edit/{work_item_id})"

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
        parent_feature = self._extract_primary_parent_feature(work_item)

        # Formatar a descrição (remover HTML se houver)
        description_clean = self._clean_html(description)
        acceptance_criteria_clean = self._clean_html(acceptance_criteria)

        feature_link_section = "Não relacionada a nenhuma Feature encontrada."
        if parent_feature:
            parent_feature_fields = parent_feature.get('fields', {})
            parent_feature_id = parent_feature.get('id', '')
            parent_feature_title = parent_feature_fields.get('System.Title', 'Sem título')
            parent_feature_path = self._build_feature_path(parent_feature_id, parent_feature_title)
            spec_path = self.spec_paths_by_id.get(work_item_id) or self._build_spec_path(work_item_id, title)
            feature_label = f"Feature #{parent_feature_id} - {parent_feature_title}"
            feature_link = self._build_azure_work_item_link(parent_feature_id, feature_label)

            feature_file_link = self._build_markdown_link('Abrir Feature', parent_feature_path, spec_path)
            feature_link_section = f"- {feature_link}  \n  - {feature_file_link}"

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
- **Tipo:** {USER_STORY_TYPE}
- **Projeto:** ALO001-26
- **Coluna:** {self.column_name}

### Feature relacionada
{feature_link_section}

### Links
- [Ver no Azure DevOps](https://dev.azure.com/mosten-core/ALO001-26/_workitems/edit/{work_item_id})

---

**Gerado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Origem:** Azure DevOps - {self.column_name}

"""
        return spec_content

    def create_feature_markdown(self, work_item: Dict[str, Any], child_user_stories: List[Dict[str, Any]]) -> str:
        """Cria conteúdo Markdown da Feature com links para US e specs."""
        fields = work_item.get('fields', {})

        title = fields.get('System.Title', 'Sem título')
        description = fields.get('System.Description', 'Não especificado')
        assigned_to = fields.get('System.AssignedTo', {})
        assigned_name = assigned_to.get('displayName', 'Não atribuído') if isinstance(assigned_to, dict) else 'Não atribuído'
        created_date = fields.get('System.CreatedDate', '')
        tags = fields.get('System.Tags', '')
        state = fields.get('System.State', '')
        work_item_id = work_item.get('id', '')

        description_clean = self._clean_html(description)

        related_items_block = "\n".join(
            self._format_feature_child_story(child_story, work_item) for child_story in child_user_stories
        ) or "Nenhuma user story relacionada encontrada."

        feature_content = f"""# Feature: {title}

**ID:** {work_item_id}  
**Status:** {state}  
**Atribuído a:** {assigned_name}  
**Data de Criação:** {created_date}  
**Tags:** {tags if tags else 'Nenhuma'}

---

## 📋 Objetivo

{description_clean}

---

## 🔗 User Stories e Specs vinculadas

{related_items_block}

---

## 📝 Detalhes Técnicos

### Informações do Work Item
- **ID:** {work_item_id}
- **Tipo:** {FEATURE_TYPE}
- **Projeto:** ALO001-26
- **Coluna:** {self.feature_column}

### Links
- [Abrir pasta de Specs](../../specs)

---

**Gerado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Origem:** Azure DevOps - {self.feature_column}

"""
        return feature_content

    def _format_feature_child_story(self, child_work_item: Dict[str, Any], feature_work_item: Dict[str, Any]) -> str:
        child_fields = child_work_item.get('fields', {})
        child_id = child_work_item.get('id', '')
        child_title = child_fields.get('System.Title', 'Sem título')
        spec_path = self._build_spec_path(child_id, child_title)
        feature_path = self._build_feature_path(feature_work_item.get('id', ''), feature_work_item.get('fields', {}).get('System.Title', 'Sem título'))

        if spec_path.exists():
            spec_link = self._build_markdown_link('Abrir Spec', spec_path, feature_path)
            return f"- US #{child_id} - {child_title}  \n  - {spec_link}"

        return f"- US #{child_id} - {child_title}  \n  - Spec pendente (arquivo ainda nao gerado)"

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
        """Normaliza nome removendo acentos e espaços para manter padrão estável."""
        if not filename:
            return ""

        normalized = unicodedata.normalize('NFKD', filename)
        ascii_only = normalized.encode('ascii', 'ignore').decode('ascii')
        compact_spaces = re.sub(r'\s+', '_', ascii_only.strip())

        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            compact_spaces = compact_spaces.replace(char, '_')

        compact_spaces = re.sub(r'_+', '_', compact_spaces).strip('_')
        return compact_spaces[:200]  # Limitar a 200 caracteres

    def extract_theme_folder(self, title: str) -> str:
        """Extrai o tema da US em variações como [USxx_Tema], [USxx-Tema], [USxx - Tema] e [USxx Tema]."""
        match = re.search(r'\[\s*US\d+\s*(?:[_-]\s*|\s+)?([^\]]+)\]', title, flags=re.IGNORECASE)
        if match:
            return self.sanitize_filename(match.group(1).strip())
        return "Outros"

    def extract_feature_folder(self, title: str) -> str:
        """Extrai a categoria da Feature no formato [Admin], [APP], [APP Motoboy], etc."""
        match = re.match(r'^\[\s*([^\]]+?)\s*\]', (title or '').strip())
        if match:
            return self.sanitize_filename(match.group(1).strip())
        return "Outros"

    def build_output_filename(self, work_item_id: int, title: str) -> str:
        """Gera nome de arquivo de US no padrão [USxx_Tema]_Descricao.md."""
        us_match = re.match(r'^\[\s*US(\d+)\s*(?:-\s*)?([^\]]+)\]\s*(.*)$', (title or '').strip(), flags=re.IGNORECASE)
        if us_match:
            us_number = us_match.group(1)
            us_theme = self.sanitize_filename(us_match.group(2))
            us_description = self.sanitize_filename(us_match.group(3))

            us_block = f"[US{us_number}_{us_theme}]" if us_theme else f"[US{us_number}]"
            if us_description:
                return f"{us_block}_{us_description}.md"
            return f"{us_block}.md"

        safe_title = self.sanitize_filename((title or '').strip())
        if safe_title:
            return f"{safe_title}.md"
        return f"US_{work_item_id}.md"

    def build_feature_output_filename(self, work_item_id: int, title: str) -> str:
        """Gera nome de arquivo para Feature com ID para evitar colisões de nome."""
        safe_title = self.sanitize_filename((title or '').strip())
        if safe_title:
            return f"{work_item_id}_{safe_title}.md"
        return f"Feature_{work_item_id}.md"

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
            self.spec_paths_by_id[work_item_id] = filepath
            logger.info(f"Spec salvo: {filepath}")
            
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar spec para work item {work_item_id}: {e}")
            return False

    def save_feature(self, work_item: Dict[str, Any]) -> bool:
        """Salva a feature em um arquivo MD"""
        try:
            work_item_id = work_item.get('id')
            title = work_item.get('fields', {}).get('System.Title', 'unnamed')

            filepath = self._build_feature_path(work_item_id, title)
            filepath.parent.mkdir(parents=True, exist_ok=True)

            child_user_stories = self._extract_child_user_stories(work_item)
            content = self.create_feature_markdown(work_item, child_user_stories)

            filepath.write_text(content, encoding='utf-8')
            self.feature_paths_by_id[work_item_id] = filepath
            logger.info(f"Feature salva: {filepath}")

            return True
        except Exception as e:
            logger.error(f"Erro ao salvar feature para work item {work_item_id}: {e}")
            return False

    def sync_specs(self) -> Dict[str, int]:
        """Sincroniza as user stories e gera specs."""
        logger.info("=" * 60)
        logger.info("Iniciando sincronizacao Azure DevOps -> Specs MD")
        logger.info(f"   Coluna: {self.column_name}")
        logger.info(f"   Pasta de saída: {self.output_folder}")
        logger.info("=" * 60)

        work_items = self.get_work_items_in_column(USER_STORY_TYPE, self.column_name)
        if not work_items:
            logger.warning(f"Nenhuma user story encontrada em '{self.column_name}'")
            return {"processed": 0, "skipped": 0, "total": 0}

        total = len(work_items)
        for idx, item in enumerate(work_items, 1):
            logger.info(f"\nProcessando US [{idx}/{total}]: {item.get('id')}")

            try:
                work_item_details = self.get_work_item_details(item['id'])
                if self.save_spec(work_item_details):
                    self.processed_count += 1
                else:
                    self.skipped_count += 1

            except Exception as e:
                logger.error(f"Erro ao processar US {item['id']}: {e}")
                self.skipped_count += 1

        return {"processed": self.processed_count, "skipped": self.skipped_count, "total": total}

    def sync_features(self) -> Dict[str, int]:
        """Sincroniza as features e gera arquivos vinculados."""
        logger.info("=" * 60)
        logger.info("Iniciando sincronizacao Azure DevOps -> Features MD")
        logger.info(f"   Coluna: {self.feature_column}")
        logger.info(f"   Pasta de saída: {self.features_folder}")
        logger.info("=" * 60)

        work_items = self.get_work_items_in_column(FEATURE_TYPE, self.feature_column)
        if not work_items:
            logger.warning(f"Nenhuma feature encontrada em '{self.feature_column}'")
            return {"processed": 0, "skipped": 0, "total": 0}

        total = len(work_items)
        for idx, item in enumerate(work_items, 1):
            logger.info(f"\nProcessando Feature [{idx}/{total}]: {item.get('id')}")

            try:
                work_item_details = self.get_work_item_details(item['id'])
                if self.save_feature(work_item_details):
                    self.features_processed_count += 1
                else:
                    self.features_skipped_count += 1

            except Exception as e:
                logger.error(f"Erro ao processar feature {item['id']}: {e}")
                self.features_skipped_count += 1

        return {
            "processed": self.features_processed_count,
            "skipped": self.features_skipped_count,
            "total": total
        }

    def sync(self) -> Dict[str, int]:
        """Executa sincronização completa"""
        try:
            spec_result = self.sync_specs()
            feature_result = self.sync_features()

            logger.info("\n" + "=" * 60)
            logger.info("SINCRONIZACAO CONCLUIDA")
            logger.info(f"   Specs criados: {spec_result['processed']}")
            logger.info(f"   Features criadas: {feature_result['processed']}")
            logger.info(f"   Pulados em specs: {spec_result['skipped']}")
            logger.info(f"   Pulados em features: {feature_result['skipped']}")
            logger.info(f"   Pasta specs: {self.output_folder}")
            logger.info(f"   Pasta features: {self.features_folder}")
            logger.info("=" * 60)

            return {
                "processed": spec_result['processed'],
                "skipped": spec_result['skipped'],
                "total": spec_result['total'],
                "feature_processed": feature_result['processed'],
                "feature_skipped": feature_result['skipped'],
                "feature_total": feature_result['total']
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
