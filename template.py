from pathlib import Path

directories = [
    "backend/app",
    "backend/tests",
    "frontend",
    "docs",
    "infrastructure",
    "scripts",
]

files = [
    "backend/app/__init__.py",
    "backend/app/main.py",
    "backend/tests/__init__.py",
    "backend/.env.example",
]

for directory in directories:
    Path(directory).mkdir(parents=True, exist_ok=True)

for file in files:
    path = Path(file)
    if not path.exists():
        path.touch()

print("✅ Project structure updated.")