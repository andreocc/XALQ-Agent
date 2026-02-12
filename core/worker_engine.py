import os
import json
import pandas as pd
import requests
import datetime
import logging
import unicodedata
import re
import platform
from docx import Document

class WorkerEngine:
    def __init__(self, base_dir=None, progress_callback=None):
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
        self.models_dir = os.path.join(self.base_dir, 'models')
        
        self.ollama_api_url = "http://localhost:11434/api/generate"
        self.progress_callback = progress_callback
        
        self._ensure_dirs()
        self.logger = self._setup_logging()
        self.is_arm_native = platform.machine().lower() in ['arm64', 'aarch64']

    def _ensure_dirs(self):
        for d in [self.processing_dir, self.output_dir, self.prompts_dir, 
                  self.templates_dir, self.error_dir, self.log_dir, self.models_dir]:
            os.makedirs(d, exist_ok=True)

    def _setup_logging(self):
        log_file_path = os.path.join(self.log_dir, 'xalq_worker.log')
        logger = logging.getLogger("WorkerEngine")
        if not logger.handlers:
            logger.setLevel(logging.DEBUG)
            fh = logging.FileHandler(log_file_path)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        return logger

    def log_and_progress(self, message, status_type="info"):
        if status_type == "info":
            self.logger.info(message)
        elif status_type == "error":
            self.logger.error(message)
        elif status_type == "debug":
            self.logger.debug(message)
        
        if self.progress_callback:
            self.progress_callback(message)

    def load_ollama_config(self):
        """Return default Ollama configuration without reading from file."""
        config = {
            'model': 'llama3',  # Default fallback, will be overridden by GUI selection
            'temperature': 0.2,
            'top_p': 0.9
        }
        return config

    def load_agent_prompt(self, agent_type):
        # 1. Try direct filename match (with or without extension)
        possible_filenames = [agent_type, f"{agent_type}.md"]
        for fname in possible_filenames:
            full_path = os.path.join(self.prompts_dir, fname)
            if os.path.exists(full_path) and os.path.isfile(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        return f.read()
                except Exception as e:
                    self.log_and_progress(f"Error loading prompt file {fname}: {e}", "error")
        
        # 2. Fallback to mapped types (legacy/convenience)
        agent_type_mapping = {
            'b2b (vende para outras empresas)': 'revenue',
            'revenue': '1.DIAGNÓSTICO – REVENUE DECISION (CORE).md', # Updated default for revenue
            'operations': '1.DIAGNÓSTICO – DIGITAL OPERATIONS (CORE).md', # Updated default for operations
        }
        
        mapped_name = agent_type_mapping.get(agent_type, agent_type)
        if not mapped_name.endswith('.md'):
             mapped_name += '.md'
             
        agent_prompt_path = os.path.join(self.prompts_dir, mapped_name)
        
        # Try loading the mapped path
        if os.path.exists(agent_prompt_path):
            try:
                with open(agent_prompt_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                self.log_and_progress(f"Error loading mapped prompt {mapped_name}: {e}", "error")
                return None
        
        # If still not found, log error
        self.log_and_progress(f"Prompt not found for type: {agent_type}", "error")
        return None

    def call_ai_api(self, prompt_content, config):
        """Generic AI caller that routes to Ollama or Native ONNX engine."""
        model_name = config.get('model', '')
        
        # Check if it's a native model (suffix .onnx or present in models dir)
        native_model_path = os.path.join(self.models_dir, model_name)
        if os.path.exists(native_model_path) and os.path.isdir(native_model_path):
            return self.call_native_onnx_api(prompt_content, config)
        
        return self.call_ollama_api(prompt_content, config)

    def call_native_onnx_api(self, prompt_content, config):
        """
        Placeholder for Native ONNX Runtime GenAI implementation.
        Requires onnxruntime-genai and optimized models for Snapdragon X Elite.
        """
        self.log_and_progress(f"Using Native ARM NPU/GPU for model: {config.get('model')}")
        try:
            import onnxruntime_genai as og
            model_path = os.path.join(self.models_dir, config.get('model'))
            
            # This is a simplified example of how it would work
            model = og.Model(model_path)
            tokenizer = og.Tokenizer(model)
            
            params = og.GeneratorParams(model)
            params.set_search_options(max_length=2048, temperature=config.get('temperature', 0.2))
            params.input_ids = tokenizer.encode(prompt_content)
            
            generator = og.Generator(model, params)
            response_text = ""
            while not generator.is_done():
                generator.compute_logits()
                generator.generate_next_token()
                new_token = generator.get_next_tokens()[0]
                response_text += tokenizer.decode([new_token])
                
            return response_text.strip()
        except ImportError:
            self.log_and_progress("onnxruntime-genai not found. Falling back to Ollama or error.", "error")
            return None
        except Exception as e:
            self.log_and_progress(f"Native AI error: {e}", "error")
            return None

    def call_ollama_api(self, prompt_content, ollama_config):
        if not ollama_config: return None
        payload = {
            "model": ollama_config.get('model', 'llama3'),
            "prompt": prompt_content,
            "stream": False,
            "options": {
                "temperature": ollama_config.get('temperature', 0.2),
                "top_p": ollama_config.get('top_p', 0.9)
            }
        }
        try:
            response = requests.post(self.ollama_api_url, json=payload, timeout=600)
            response.raise_for_status()
            return response.json().get('response', '').strip()
        except Exception as e:
            self.log_and_progress(f"Ollama API error: {e}", "error")
            return None

    def parse_ollama_response(self, ai_response):
        parsed_data = {}
        sections = ["RESUMO_EXECUTIVO", "DIAGNOSTICO", "LACUNAS", "CLASSIFICACAO", "OBSERVACOES_XALQ"]
        response_with_end_marker = ai_response + "\n[END_OF_RESPONSE]"
        for i, section_name in enumerate(sections):
            end_pattern = f"\s*\[{sections[i+1]}\]" if i+1 < len(sections) else "\s*\[END_OF_RESPONSE\]"
            match = re.search(f"\[{section_name}\]\s*(.*?)(?={end_pattern})", response_with_end_marker, re.DOTALL)
            parsed_data[section_name] = match.group(1).strip() if match else ""
        return parsed_data

    def sanitize_filename(self, filename_str):
        normalized = unicodedata.normalize('NFKD', filename_str).encode('ascii', 'ignore').decode('utf-8')
        sanitized = normalized.replace(' ', '_')
        sanitized = re.sub(r'[^\w.-]', '', sanitized)
        sanitized = re.sub(r'_{2,}', '_', sanitized)
        sanitized = re.sub(r'-{2,}', '-', sanitized)
        return sanitized.strip('_-')

    def generate_word_report(self, parsed_data, agent_type, ollama_model, timestamp, prefix):
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
                '{{modelo_ollama}}': ollama_model,
                '{{timestamp}}': timestamp
            }
            for p in doc.paragraphs:
                text = p.text
                for k, v in replacements.items():
                    if k in text: text = text.replace(k, v)
                if p.text != text:
                    p.clear()
                    p.add_run(text)
            
            out_name = f"{self.sanitize_filename(prefix)}_{self.sanitize_filename(ollama_model)}_report_{timestamp}.docx"
            out_path = os.path.join(self.output_dir, out_name)
            doc.save(out_path)
            return out_path
        except Exception as e:
            self.log_and_progress(f"Error generating report: {e}", "error")
            return None

    def get_ollama_models(self):
        """Fetch available models from Ollama API and Native folder."""
        models = []
        
        # 1. Native Models (ARM Optimized)
        try:
            if os.path.exists(self.models_dir):
                native_models = [d for d in os.listdir(self.models_dir) if os.path.isdir(os.path.join(self.models_dir, d))]
                for nm in native_models:
                    models.append(f"{nm} (Nativo ARM)")
        except Exception as e:
            self.logger.error(f"Error listing native models: {e}")

        # 2. Ollama Models
        try:
            response = requests.get(self.ollama_api_url.replace("/api/generate", "/api/tags"), timeout=5)
            response.raise_for_status()
            data = response.json()
            for model in data.get('models', []):
                models.append(model['name'])
        except Exception as e:
            self.log_and_progress(f"Erro ao buscar modelos Ollama: {e}", "debug")
            
        return models

    def get_prompts_list(self):
        """Return list of available prompt files."""
        try:
            files = [f for f in os.listdir(self.prompts_dir) if f.endswith('.md')]
            return files
        except Exception as e:
            self.log_and_progress(f"Erro ao listar prompts: {e}", "error")
            return []

    def save_prompt_content(self, filename, content):
        """Save content to a prompt file."""
        try:
            path = os.path.join(self.prompts_dir, filename)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            self.log_and_progress(f"Erro ao salvar prompt {filename}: {e}", "error")
            return False

    def read_prompt_content(self, filename):
        """Read content from a prompt file."""
        try:
            path = os.path.join(self.prompts_dir, filename)
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.log_and_progress(f"Erro ao ler prompt {filename}: {e}", "error")
            return None

    def load_data(self, file_path):
        """Loads the file and returns dataframe and list of company/row identifiers."""
        try:
            file_name = os.path.basename(file_path)
            if file_name.endswith('.csv'): df = pd.read_csv(file_path)
            elif file_name.endswith(('.xls', '.xlsx')): df = pd.read_excel(file_path)
            else: return None, []
            
            # Heuristic to find company name column
            company_col = None
            candidates = ['Empresa', 'Company', 'Nome', 'Cliente', 'Organization']
            for col in df.columns:
                if any(c.lower() in col.lower() for c in candidates):
                    company_col = col
                    break
            
            if not company_col:
                company_col = df.columns[0] # Fallback to first column

            # Create a list of "Index: Value" for UI
            items = []
            for idx, row in df.iterrows():
                val = str(row[company_col])
                items.append(f"{idx+1}: {val}")
            
            return df, items
        except Exception as e:
            self.log_and_progress(f"Erro ao carregar dados: {e}", "error")
            return None, []

    def process_file(self, file_path, model_override=None, rows_to_process=None, prompt_type_override=None):
        file_name = os.path.basename(file_path)
        self.log_and_progress(f"Iniciando processamento: {file_name}")
        
        try:
            if file_name.endswith('.csv'): df = pd.read_csv(file_path)
            elif file_name.endswith(('.xls', '.xlsx')): df = pd.read_excel(file_path)
            else: raise ValueError("Formato não suportado")
        except Exception as e:
            self.log_and_progress(f"Erro ao ler arquivo: {e}", "error")
            return []

        config = self.load_ollama_config()
        
        # Clean model name if it has (Nativo ARM) suffix
        if model_override:
            clean_model_name = model_override.replace(" (Nativo ARM)", "")
            config['model'] = clean_model_name
            self.log_and_progress(f"Usando modelo selecionado: {clean_model_name}")
        
        # Log prompt type override if provided
        if prompt_type_override:
            self.log_and_progress(f"Usando tipo de prompt: {prompt_type_override}")

        model_name = config.get('model', 'llama3')
        total = len(df)
        self.log_and_progress(f"Total de linhas: {total}")

        generated_files = []

        for i, row in df.iterrows():
            row_idx = i + 1
            
            # Filter logic
            if rows_to_process and row_idx not in rows_to_process:
                continue

            self.log_and_progress(f"Processando linha {row_idx}/{total}...")
            
            # Use prompt_type_override if provided, otherwise detect from data
            if prompt_type_override:
                agent_type = prompt_type_override
                self.log_and_progress(f"Linha {row_idx}: Usando tipo de prompt manual: {agent_type}")
            else:
                col_name = 'Qual o principal modelo de atuação da empresa?'
                if col_name not in row.index:
                    self.log_and_progress(f"Coluna não encontrada na linha {row_idx}", "error")
                    continue
                agent_type = str(row[col_name]).strip().lower()
                self.log_and_progress(f"Linha {row_idx}: Tipo de agente detectado: {agent_type}")
            
            prompt_template = self.load_agent_prompt(agent_type)
            if not prompt_template: continue

            self.log_and_progress(f"Linha {row_idx}: Chamando AI Engine...")
            ai_response = self.call_ai_api(f"{prompt_template}\nDados:\n{row.to_string()}", config)
            if not ai_response: continue

            self.log_and_progress(f"Linha {row_idx}: Parsing concluído.")
            parsed_data = self.parse_ollama_response(ai_response)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            prefix = f"{os.path.splitext(file_name)[0]}_row{row_idx}"
            
            report_path = self.generate_word_report(parsed_data, agent_type, model_name, timestamp, prefix)
            if report_path:
                self.log_and_progress(f"Linha {row_idx}: Relatório gerado.")
                generated_files.append(report_path)
            else:
                self.log_and_progress(f"Linha {row_idx}: Erro ao gerar relatório.", "error")
        
        self.log_and_progress("Processamento concluído com sucesso.")
        return generated_files
