import os
import json
import requests
import logging
from functools import lru_cache
from PySide6.QtCore import QSettings

class Updater:
    def __init__(self, base_dir=None):
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        if os.path.basename(self.base_dir) == 'core':
            self.base_dir = os.path.dirname(self.base_dir)
            
        self.version_file = os.path.join(self.base_dir, 'version.json')
        self.github_repo_url = "https://raw.githubusercontent.com/andreocc/XALQ-Agent/main"
        self.logger = logging.getLogger("Updater")
        
        self.settings = QSettings("XALQ", "XALQ Agent")

    def get_local_version(self):
        try:
            with open(self.version_file, 'r') as f:
                data = json.load(f)
                return data
        except Exception as e:
            self.logger.error(f"Error reading local version file: {e}")
            return {"version": "0.0.0", "critical_update": False}

    def check_for_updates(self):
        """
        Checks for updates by comparing local version with remote version.json.
        Returns tuple: (is_update_available, remote_version_data)
        """
        try:
            url = f"{self.github_repo_url}/version.json"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            remote_data = response.json()
            
            local_data = self.get_local_version()
            local_ver = local_data.get("version", "0.0.0")
            remote_ver = remote_data.get("version", "0.0.0")
            
            if self._compare_versions(remote_ver, local_ver) > 0:
                return True, remote_data
            
            return False, remote_data
        except Exception as e:
            self.logger.error(f"Error checking for updates: {e}")
            print(f"Update check failed: {e}")
            return False, None

    def _compare_versions(self, v1, v2):
        """
        Compare two semver strings.
        Returns:
            1 if v1 > v2
           -1 if v1 < v2
            0 if v1 == v2
        """
        def normalize(v):
            return [int(x) for x in v.split(".")]

        try:
            parts1 = normalize(v1)
            parts2 = normalize(v2)
            
            if parts1 > parts2: return 1
            if parts1 < parts2: return -1
            return 0
        except ValueError:
            return 0

    @lru_cache(maxsize=32)
    def get_github_prompt(self, filename):
        """
        Fetches a prompt file from GitHub using the configured PAT.
        Uses LRU cache to minimize requests.
        """
        pat = self.settings.value("github_pat", "")
        headers = {}
        if pat:
            headers["Authorization"] = f"token {pat}"
        
        # Ensure filename has .md extension
        if not filename.endswith('.md'):
            filename += '.md'
            
        url = f"{self.github_repo_url}/prompts/{filename}"
        
        try:
            self.logger.debug(f"Fetching prompt from GitHub: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            self.logger.error(f"Error fetching prompt {filename}: {e}")
            return None

    def perform_update(self):
        """
        Executes 'git pull' to update the repository.
        Returns: (success, message)
        """
        import subprocess
        try:
            # Force reset to ensure local changes (like version.json) don't block update
            subprocess.run(
                ["git", "reset", "--hard", "origin/main"],
                cwd=self.base_dir,
                capture_output=True,
                text=True,
                check=False # Don't fail if this fails, just try pull
            )

            # Run git pull origin main to avoid "no tracking info" error
            # Using shell=True for better path resolution on Windows if needed, but list is safer.
            result = subprocess.run(
                ["git", "pull", "origin", "main"], 
                cwd=self.base_dir, 
                capture_output=True, 
                text=True, 
                check=True
            )
            self.logger.info(f"Git pull output: {result.stdout}")
            return True, "Atualização realizada com sucesso! Por favor, reinicie o aplicativo."
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git pull failed: {e.stderr}")
            return False, f"Falha ao executar git pull: {e.stderr}"
        except Exception as e:
            self.logger.error(f"Update error: {e}")
            return False, f"Erro inesperado na atualização: {str(e)}"
