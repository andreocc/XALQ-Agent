import os
import re
import datetime
import logging
import json
import requests
import re
import platform
from docx import Document
from PySide6.QtCore import QSettings
import google.generativeai as genai
from core.updater import Updater

class WorkerEngine:
    def __init__(self, base_dir=None, progress_callback=None, api_key=None):
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        
        # Adjust base_dir if it's inside 'core'
        if os.path.basename(self.base_dir) == 'core':
            self.base_dir = os.path.dirname(self.base_dir)
            
        self.processing_dir = os.path.join(self.base_dir, 'processing')
        self.output_dir = os.path.join(self.base_dir, 'output')
        self.prompts_dir = os.path.join(self.base_dir, 'prompts')
        self.templates_dir = os.path.join(self.base_dir, 'templates')
        self.error_dir = os.path.join(self.base_dir, 'error')
        self.log_dir = os.path.join(self.base_dir, 'logs')
        
        self.progress_callback = progress_callback
        
        self._ensure_dirs()
        self.logger = self._setup_logging()
        
        self.settings = QSettings("XALQ", "XALQ Agent")
        self.updater = Updater(self.base_dir)
        
        # Use passed key or load from settings
        self.api_key = api_key or self.settings.value("gemini_api_key", "")
        self._configure_gemini()

    def _ensure_dirs(self):
        for d in [self.processing_dir, self.output_dir, self.prompts_dir, 
                  self.templates_dir, self.error_dir, self.log_dir]:
            os.makedirs(d, exist_ok=True)

    def _setup_logging(self):
        logger = logging.getLogger("WorkerEngine")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            fh = logging.FileHandler(os.path.join(self.log_dir, 'worker.log'), encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        return logger

    def _configure_gemini(self):
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.log_and_progress("Gemini configurado com sucesso.", "debug")
        else:
            self.log_and_progress("Gemini API Key não configurada! Adicione nas configurações.", "error")

    def log_and_progress(self, message, status_type="info"):
        if status_type == "info":
            self.logger.info(message)
        elif status_type == "error":
            self.logger.error(message)
        elif status_type == "debug":
            self.logger.debug(message)
            
        if self.progress_callback:
            self.progress_callback(message)

    def load_agent_prompt(self, agent_type):
        """
        Loads prompt content with fuzzy filename matching to handle
        encoding differences (accents, dashes, case).
        """
        import unicodedata

        def normalize(text):
            # NFKD decomposition, lowercase, remove non-ascii for robust comparison
            text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
            return text.lower().replace(" ", "").replace("-", "").replace("_", "")

        target_normalized = normalize(agent_type)

        # 1. List local files and try to find a match
        try:
            local_files = [f for f in os.listdir(self.prompts_dir) if f.endswith('.md')]
            for fname in local_files:
                # Check 1: Exact match
                if fname == agent_type or fname == f"{agent_type}.md":
                    return self.read_prompt_content(fname)
                
                # Check 2: Fuzzy match
                fname_normalized = normalize(fname.replace(".md", ""))
                if fname_normalized == target_normalized:
                    return self.read_prompt_content(fname)
                    
                # Check 3: Checking if target is a substring of filename (e.g. "revenue" in "...REVENUE...")
                if target_normalized in fname_normalized:
                     # Heuristic: if strict match fails, maybe the short name is part of the long filename
                     # But be careful not to match "revenue" to "revenue_operations" incorrectly if both exist
                     # For now, let's trust the mapping below if this fails.
                     pass

        except Exception as e:
            self.log_and_progress(f"Error listing local prompts: {e}", "error")

        # 2. Fallback to mapped types (legacy/convenience) if no local file matched
        agent_type_mapping = {
            'b2b (vende para outras empresas)': 'revenue',
            'revenue': '1.DIAGNÓSTICO – REVENUE DECISION (CORE).md',
            'operations': '1.DIAGNÓSTICO – DIGITAL OPERATIONS (CORE).md',
        }
        
        mapped_name = agent_type_mapping.get(agent_type, agent_type)
        if not mapped_name.endswith('.md'):
             mapped_name += '.md'

        # Try loading the mapped name locally (again, with fuzzy check if needed, but usually exact)
        full_path = os.path.join(self.prompts_dir, mapped_name)
        if os.path.exists(full_path):
             return self.read_prompt_content(mapped_name)

        # 3. If not found locally, try GitHub
        self.log_and_progress(f"Prompt {mapped_name} não encontrado localmente. Buscando no GitHub...", "debug")
        content = self.updater.get_github_prompt(mapped_name)
        if content:
            self.save_prompt_content(mapped_name, content)
            return content
            
        self.log_and_progress(f"Prompt not found for type: {agent_type} (Local or GitHub)", "error")
        return None

    def call_ai_api(self, prompt_content, config):
        """Routes to Gemini API."""
        return self.call_gemini_api(prompt_content, config)

    def call_gemini_api(self, prompt_content, config):
        if not self.api_key:
             self.log_and_progress("Tentativa de chamar Gemini sem API Key configurada.", "error")
             return None

        model_name = config.get('model', 'gemini-1.5-pro')
        
        try:
            model = genai.GenerativeModel(model_name)
            generation_config = genai.types.GenerationConfig(
                temperature=config.get('temperature', 0.2),
                top_p=config.get('top_p', 0.9),
                max_output_tokens=8192,
            )
            
            self.log_and_progress(f"Enviando request para Gemini ({model_name})...", "debug")
            response = model.generate_content(prompt_content, generation_config=generation_config)
            
            # Check for safety blocks or empty responses
            if not response.parts:
                if response.prompt_feedback:
                     self.log_and_progress(f"Gemini bloqueou o prompt: {response.prompt_feedback}", "error")
                else:
                     self.log_and_progress("Resposta do Gemini vazia (sem parts). Verifique safety filters.", "error")
                return None

            return response.text
        except Exception as e:
            self.log_and_progress(f"Gemini API Error: {e}", "error")
            return None

    def parse_ollama_response(self, ai_response):
        """
        Parses response looking for [SECTION]...[/SECTION] tags.
        Falls back to simpler parsing if strict tags are missing.
        """
        parsed_data = {}
        sections = ["RESUMO_EXECUTIVO", "DIAGNOSTICO", "LACUNAS", "CLASSIFICACAO", "OBSERVACOES_XALQ"]
        
        # 1. Try strict tagging [SECTION]...[/SECTION]
        for section in sections:
            pattern = fr"\[{section}\](.*?)\[/{section}\]"
            match = re.search(pattern, ai_response, re.DOTALL | re.IGNORECASE)
            if match:
                parsed_data[section] = match.group(1).strip()
            else:
                parsed_data[section] = ""

        # 2. Validation: If most sections are empty, try fallback parsing
        filled_sections = sum(1 for v in parsed_data.values() if v)
        if filled_sections < 2:
            self.log_and_progress("Tags estritas não encontradas ou incompletas. Tentando parsing flexível...", "debug")
            # Fallback: Extract between headers
            # Assuming headers might be like "Resumo Executivo:" or "## Resumo Executivo"
            # We map clean names to section keys
            
            # Create a clean version of the response for searching
            clean_response = ai_response
            
            # Map simplified headers to keys
            header_map = {
                "RESUMO EXECUTIVO": "RESUMO_EXECUTIVO",
                "DIAGNOSTICO": "DIAGNOSTICO",
                "DIAGNÓSTICO": "DIAGNOSTICO",
                "LACUNAS": "LACUNAS",
                "CLASSIFICAÇÃO": "CLASSIFICACAO",
                "CLASSIFICACAO": "CLASSIFICACAO",
                "OBSERVAÇÕES": "OBSERVACOES_XALQ",
                "OBSERVACOES": "OBSERVACOES_XALQ"
            }
            
            current_section = None
            lines = clean_response.split('\n')
            
            # Temporary buffer for manual extraction
            temp_data = {k: [] for k in sections}
            
            for line in lines:
                clean_line = line.strip().upper().replace("*", "").replace("#", "").replace(":", "")
                
                # Check if this line is a header
                found_header = None
                for header, key in header_map.items():
                   if clean_line == header:
                       found_header = key
                       break
                
                if found_header:
                    current_section = found_header
                elif current_section:
                    temp_data[current_section].append(line)
            
            # Join collected lines
            for key, lines in temp_data.items():
                if lines:
                    parsed_data[key] = "\n".join(lines).strip()
                    
        return parsed_data

    def load_data(self, file_path):
        import pandas as pd
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            # Simple validation
            if df.empty:
                return None, []
                
            # Create a list of "Index: CompanyName" for combo box
            # Improved heuristic for Company Name
            company_col = None
            candidates = ['nome da empresa', 'empresa', 'company', 'name', 'cliente', 'organization', 'razão social', 'razao social']
            
            # 1. Search for exact/partial match
            for col in df.columns:
                if any(c in str(col).lower() for c in candidates):
                    company_col = col
                    break
            
            # 2. Fallback: First column that is NOT a timestamp
            if not company_col:
                for col in df.columns:
                    col_str = str(col).lower()
                    # Check for date keywords
                    if any(x in col_str for x in ['data', 'date', 'time', 'carimbo', 'timestamp', 'hora']):
                        continue
                    company_col = col
                    break
            
            # 3. Final Fallback
            if not company_col:
                company_col = df.columns[0]
            
            items = []
            for idx, row in df.iterrows():
                val = str(row[company_col])
                items.append(f"{idx}: {val}")
                
            return df, items
        except Exception as e:
            self.log_and_progress(f"Erro ao carregar dados: {e}", "error")
            return None, []

    def save_prompt_content(self, filename, content):
        try:
            path = os.path.join(self.prompts_dir, filename)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            self.logger.error(f"Erro ao salvar prompt {filename}: {e}")
            return False

    def sanitize_filename(self, text):
        # Remove invalid chars for filenames
        if not isinstance(text, str): return "unknown"
        sanitized = re.sub(r'[<>:"/\\|?*]', '', text)
        sanitized = re.sub(r'\s+', '_', sanitized)
        # Ensure only 0-9, a-z, A-Z, _, - are kept if being strict, 
        # but allowing unicode is usually fine on modern OS.
        # Let's keep it simple:
        sanitized = re.sub(r'[^\w\-\.]', '_', sanitized)
        sanitized = re.sub(r'_{2,}', '_', sanitized)
        sanitized = re.sub(r'-{2,}', '-', sanitized)
        return sanitized.strip('_-')

    def generate_word_report(self, parsed_data, agent_type, model_name, timestamp, prefix):
        template_path = os.path.join(self.templates_dir, 'template_xalq.docx')
        if not os.path.exists(template_path):
            self.log_and_progress(f"Template not found: {template_path}", "error")
            return None
            
        try:
            doc = Document(template_path)
            
            replacements = {
                '{{RESUMO_EXECUTIVO}}': parsed_data.get('RESUMO_EXECUTIVO', ''),
                '{{DIAGNOSTICO}}': parsed_data.get('DIAGNOSTICO', ''),
                '{{LACUNAS}}': parsed_data.get('LACUNAS', ''),
                '{{CLASSIFICACAO}}': parsed_data.get('CLASSIFICACAO', ''),
                '{{OBSERVACOES_XALQ}}': parsed_data.get('OBSERVACOES_XALQ', ''),
                '{{tipo_agente}}': agent_type,
                '{{modelo_ollama}}': model_name, # Kept tag name for compatibility
                '{{timestamp}}': timestamp
            }
            for p in doc.paragraphs:
                for key, val in replacements.items():
                    if key in p.text:
                        p.text = p.text.replace(key, str(val))
                        
            # Tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for p in cell.paragraphs:
                            for key, val in replacements.items():
                                if key in p.text:
                                    # Simple replacement, preserving run style is harder without more complex logic
                                    # For now, direct text replacement
                                    text = p.text.replace(key, str(val))
                                    p.text = text
                                    # Force font? (optional)
                                    # for run in p.runs:
                                    #     run.font.name = 'Calibri'
            # Also invoke tables replacement if needed (not implemented here but good to keep in mind)

            out_name = f"{self.sanitize_filename(prefix)}_{self.sanitize_filename(model_name)}_report_{timestamp}.docx"
            out_path = os.path.join(self.output_dir, out_name)
            doc.save(out_path)
            return out_path
        except Exception as e:
            self.log_and_progress(f"Error generating report: {e}", "error")
            return None

    def get_available_models(self):
        """Return available Gemini models."""
        # Hardcoded list for now, or could fetch from genai.list_models() if key is valid
        return ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"]
        
    def get_prompts_list(self):
        """Return list of available prompt files."""
        # Hardcoded for now based on user request / known types
        # Or scan folder
        try:
            files = [f for f in os.listdir(self.prompts_dir) if f.endswith('.md')]
            # Remove extension for display
            return [os.path.splitext(f)[0] for f in files] + ["revenue", "operations"]
        except:
            return ["revenue", "operations"]

    def process_file(self, file_path, model_override=None, rows_to_process=None, prompt_type_override=None):
        import pandas as pd
        self.log_and_progress(f"Lendo arquivo: {file_path}")
        
        df, items = self.load_data(file_path)
        if df is None: return []

        generated_files = []
        
        # Config setup
        config = {
            'model': model_override or 'gemini-1.5-pro',
            'temperature': 0.2,
            'top_p': 0.9
        }
        
        # Log prompt type override if provided
        if prompt_type_override:
            self.log_and_progress(f"Tipo de análise forçado: {prompt_type_override}")

        total = len(df)
        self.log_and_progress(f"Total de linhas: {total}")

        for row_idx, row in df.iterrows():
            # Check row filter
            if rows_to_process and row_idx not in rows_to_process:
                continue

            # Prefix from company name
            prefix = f"Row_{row_idx}"
            col_name = 'Nome da Empresa'
            if col_name in row.index:
                prefix = str(row[col_name])

            self.log_and_progress(f"Processando linha {row_idx}/{total}...")
            
            # Determine Prompt Type
            if prompt_type_override:
                agent_type = prompt_type_override
                self.log_and_progress(f"Linha {row_idx}: Usando tipo manual: {agent_type}")
            else:
                col_name = 'Qual o principal modelo de atuação da empresa?'
                if col_name not in row.index:
                    self.log_and_progress(f"Linha {row_idx}: Coluna de modelo de atuação não encontrada.", "error")
                    continue
                agent_type = str(row[col_name]).strip().lower()
                self.log_and_progress(f"Linha {row_idx}: Tipo detectado: {agent_type}")
            
            # Fetch prompt (Local -> GitHub)
            prompt_template = self.load_agent_prompt(agent_type)
            if not prompt_template: 
                self.log_and_progress(f"Linha {row_idx}: Prompt não encontrado, pulando.", "error")
                continue

            self.log_and_progress(f"Linha {row_idx}: Chamando Gemini ({config['model']})...")
            ai_response = self.call_ai_api(f"{prompt_template}\nDados:\n{row.to_string()}", config)
            if not ai_response: 
                self.log_and_progress(f"Linha {row_idx}: Falha na resposta da IA.", "error")
                continue

            self.log_and_progress(f"Linha {row_idx}: Parsing resposta...")
            parsed_data = self.parse_ollama_response(ai_response)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            
            report_path = self.generate_word_report(parsed_data, agent_type, config['model'], timestamp, prefix)
            if report_path:
                self.log_and_progress(f"Linha {row_idx}: Relatório gerado.")
                generated_files.append(report_path)
            else:
                self.log_and_progress(f"Linha {row_idx}: Erro ao gerar relatório.", "error")
        
        self.log_and_progress("Processamento concluído.")
        return generated_files
