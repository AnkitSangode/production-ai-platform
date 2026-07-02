from pathlib import Path

PROJECT_NAME = "production-ai-platform"

# Directories
directories = [
    PROJECT_NAME,
    f"{PROJECT_NAME}/backend",
    f"{PROJECT_NAME}/frontend",
    f"{PROJECT_NAME}/infrastructure",
    f"{PROJECT_NAME}/docs",
    f"{PROJECT_NAME}/scripts",
]

# Files
files = [
    f"{PROJECT_NAME}/README.md",
    f"{PROJECT_NAME}/.gitignore",
]

# Create directories
for directory in directories:
    Path(directory).mkdir(parents=True, exist_ok=True)

# Create files
for file in files:
    path = Path(file)
    path.touch(exist_ok=True)

print("=" * 50)
print("✅ Production AI Platform initialized successfully!")
print("=" * 50)