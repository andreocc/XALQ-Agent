# justfile

default:
    @just --list

# Run application
run:
    python Xalq.py

# Run tests
test:
    pytest tests/ -v --cov=core --cov=ui

# Install dependencies
install:
    pip install -r requirements.txt

# Lint code
lint:
    flake8 core/ ui/ --max-line-length=120
    black --check core/ ui/

# Format code
format:
    black core/ ui/

# Clean cache and logs
clean:
    rm -rf __pycache__ .pytest_cache .coverage
    del /Q logs\*.log 2>NUL
