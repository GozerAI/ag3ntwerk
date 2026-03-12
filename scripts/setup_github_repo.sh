#!/bin/bash
# Bash script to create a private GitHub repository and push ag3ntwerk project
# Requires: GitHub CLI (gh) installed and authenticated

set -e

PROJECT_PATH="$(cd "$(dirname "$0")/.." && pwd)"
REPO_NAME="ag3ntwerk"
REPO_DESCRIPTION="ag3ntwerk: Hierarchical AI Agent Orchestration Platform"

echo "=== ag3ntwerk GitHub Repository Setup ==="
echo ""

# Change to project directory
cd "$PROJECT_PATH"
echo "Working directory: $PROJECT_PATH"

# Check if gh CLI is installed
echo ""
echo "Checking GitHub CLI..."
if ! command -v gh &> /dev/null; then
    echo "ERROR: GitHub CLI (gh) is not installed."
    echo "Install it from: https://cli.github.com/"
    exit 1
fi
echo "GitHub CLI found: $(gh --version | head -1)"

# Check if authenticated
echo ""
echo "Checking GitHub authentication..."
if ! gh auth status &> /dev/null; then
    echo "ERROR: Not authenticated with GitHub."
    echo "Run: gh auth login"
    exit 1
fi
echo "Authenticated with GitHub"

# Initialize git if not already initialized
echo ""
echo "Checking Git repository..."
if [ ! -d ".git" ]; then
    echo "Initializing Git repository..."
    git init
    echo "Git repository initialized"
else
    echo "Git repository already exists"
fi

# Check/create .gitignore
echo ""
echo "Checking .gitignore..."
if [ ! -f ".gitignore" ]; then
    echo "Creating .gitignore..."
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
.venv/
venv/
ENV/

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Build outputs
src/ag3ntwerk/web/dist/

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# Environment
.env
.env.local
.env.*.local
*.env

# Data and caches
data/
*.db
*.sqlite
*.sqlite3
.cache/
*.log

# OS
.DS_Store
Thumbs.db

# Secrets
credentials.json
secrets.yaml
*.pem
*.key

# Coverage
htmlcov/
.coverage
.coverage.*
coverage.xml
*.cover
EOF
    echo ".gitignore created"
else
    echo ".gitignore already exists"
fi

# Check if remote origin already exists
echo ""
echo "Checking for existing remote..."
if git remote get-url origin &> /dev/null; then
    EXISTING_REMOTE=$(git remote get-url origin)
    echo "Remote origin already exists: $EXISTING_REMOTE"
    read -p "Do you want to continue and update the remote? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
    git remote remove origin
fi

# Create private GitHub repository
echo ""
echo "Creating private GitHub repository..."
if gh repo create "$REPO_NAME" --private --description "$REPO_DESCRIPTION" --source . --remote origin 2>/dev/null; then
    echo "Repository created successfully!"
else
    # Repository might already exist, try to set remote
    echo "Repository may already exist, attempting to set remote..."
    USERNAME=$(gh api user --jq '.login')
    git remote add origin "https://github.com/$USERNAME/$REPO_NAME.git"
fi

# Stage all files
echo ""
echo "Staging files..."
git add -A

# Show what will be committed
echo ""
echo "Files to be committed:"
git status --short | head -30
FILE_COUNT=$(git status --short | wc -l)
if [ "$FILE_COUNT" -gt 30 ]; then
    echo "... and $((FILE_COUNT - 30)) more files"
fi

# Create initial commit
echo ""
echo "Creating initial commit..."
git commit -m "Initial commit: ag3ntwerk AI Agent Orchestration Platform

- Hierarchical AI agent agent system (Nexus, Forge, Sentinel, Keystone, etc.)
- FastAPI backend with Ollama LLM integration
- React TypeScript frontend with Tailwind CSS
- 32+ enterprise workflows
- WebSocket real-time updates
- Goal and task management system

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

# Push to GitHub
echo ""
echo "Pushing to GitHub..."
git branch -M main
git push -u origin main

echo ""
echo "=== Setup Complete ==="
echo ""

# Get and display repo URL
REPO_URL=$(gh repo view --json url --jq '.url')
echo "Repository URL: $REPO_URL"
echo ""
echo "Next steps:"
echo "  1. Visit your repository: $REPO_URL"
echo "  2. Configure branch protection rules if needed"
echo "  3. Add collaborators in Settings > Collaborators"
echo ""
