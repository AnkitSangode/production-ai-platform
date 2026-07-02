from pathlib import Path

PROJECT_NAME = "production-ai-platform"

# Directories to create
directories = [
    PROJECT_NAME,
    f"{PROJECT_NAME}/backend",
    f"{PROJECT_NAME}/frontend",
    f"{PROJECT_NAME}/infrastructure",
    f"{PROJECT_NAME}/docs",
    f"{PROJECT_NAME}/scripts",
]

# Files to create
files = [
    f"{PROJECT_NAME}/README.md",
    f"{PROJECT_NAME}/.gitignore",
]

# Create directories and .gitkeep
for directory in directories:
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)

    # Don't create .gitkeep in the project root
    if dir_path.name != PROJECT_NAME:
        gitkeep = dir_path / ".gitkeep"
        gitkeep.touch(exist_ok=True)

# Create root files
for file in files:
    Path(file).touch(exist_ok=True)

print("=" * 60)
print("✅ Production AI Platform initialized successfully!")
print("=" * 60)