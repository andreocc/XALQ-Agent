from PySide6.QtCore import QSettings, QCoreApplication
import sys

# QSettings needs a QCoreApplication instance usually to work reliably with organizational defaults, 
# but with explicit constructor QSettings("Org", "App") it should work standalone.
app = QCoreApplication(sys.argv)

settings = QSettings("XALQ", "XALQ Agent")
key = settings.value("gemini_api_key", "NOT_FOUND")
print(f"Stored Gemini Key: '{key}'")

pat = settings.value("github_pat", "NOT_FOUND")
print(f"Stored GitHub PAT: '{pat}'")
