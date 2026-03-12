# PowerShell script to create a private GitHub repository and push c-suite project
# Requires: GitHub CLI (gh) installed and authenticated

$ErrorActionPreference = "Stop"

$projectPath = "F:\Projects\c-suite"
$repoName = "c-suite"
$repoDescription = "C-Suite: Hierarchical AI Agent Orchestration Platform"

Write-Host "=== C-Suite GitHub Repository Setup ===" -ForegroundColor Cyan
Write-Host ""

# Change to project directory
Set-Location $projectPath
Write-Host "Working directory: $projectPath" -ForegroundColor Gray

# Check if gh CLI is installed
Write-Host "`nChecking GitHub CLI..." -ForegroundColor Yellow
try {
    $ghVersion = gh --version
    Write-Host "GitHub CLI found: $($ghVersion[0])" -ForegroundColor Green
} catch {
    Write-Host "ERROR: GitHub CLI (gh) is not installed." -ForegroundColor Red
    Write-Host "Install it from: https://cli.github.com/" -ForegroundColor Yellow
    exit 1
}

# Check if authenticated
Write-Host "`nChecking GitHub authentication..." -ForegroundColor Yellow
try {
    $authStatus = gh auth status 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Not authenticated with GitHub." -ForegroundColor Red
        Write-Host "Run: gh auth login" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Authenticated with GitHub" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Authentication check failed." -ForegroundColor Red
    exit 1
}

# Initialize git if not already initialized
Write-Host "`nChecking Git repository..." -ForegroundColor Yellow
if (-not (Test-Path ".git")) {
    Write-Host "Initializing Git repository..." -ForegroundColor Gray
    git init
    Write-Host "Git repository initialized" -ForegroundColor Green
} else {
    Write-Host "Git repository already exists" -ForegroundColor Green
}

# Check/create .gitignore
Write-Host "`nChecking .gitignore..." -ForegroundColor Yellow
if (-not (Test-Path ".gitignore")) {
    Write-Host "Creating .gitignore..." -ForegroundColor Gray
    @"
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
src/csuite/web/dist/

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
"@ | Out-File -FilePath ".gitignore" -Encoding utf8
    Write-Host ".gitignore created" -ForegroundColor Green
} else {
    Write-Host ".gitignore already exists" -ForegroundColor Green
}

# Check if remote origin already exists
Write-Host "`nChecking for existing remote..." -ForegroundColor Yellow
$remoteExists = git remote get-url origin 2>$null
if ($remoteExists) {
    Write-Host "Remote origin already exists: $remoteExists" -ForegroundColor Yellow
    $response = Read-Host "Do you want to continue and update the remote? (y/n)"
    if ($response -ne "y") {
        Write-Host "Aborted." -ForegroundColor Red
        exit 0
    }
    git remote remove origin
}

# Create private GitHub repository
Write-Host "`nCreating private GitHub repository..." -ForegroundColor Yellow
try {
    gh repo create $repoName --private --description $repoDescription --source . --remote origin
    Write-Host "Repository created successfully!" -ForegroundColor Green
} catch {
    # Repository might already exist, try to set remote
    Write-Host "Repository may already exist, attempting to set remote..." -ForegroundColor Yellow
    $username = gh api user --jq '.login'
    git remote add origin "https://github.com/$username/$repoName.git"
}

# Stage all files
Write-Host "`nStaging files..." -ForegroundColor Yellow
git add -A

# Show what will be committed
Write-Host "`nFiles to be committed:" -ForegroundColor Gray
git status --short | Select-Object -First 30
$fileCount = (git status --short | Measure-Object).Count
if ($fileCount -gt 30) {
    Write-Host "... and $($fileCount - 30) more files" -ForegroundColor Gray
}

# Create initial commit
Write-Host "`nCreating initial commit..." -ForegroundColor Yellow
git commit -m "Initial commit: C-Suite AI Agent Orchestration Platform

- Hierarchical AI executive agent system (COO, CTO, CIO, CFO, etc.)
- FastAPI backend with Ollama LLM integration
- React TypeScript frontend with Tailwind CSS
- 32+ enterprise workflows
- WebSocket real-time updates
- Goal and task management system

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

# Push to GitHub
Write-Host "`nPushing to GitHub..." -ForegroundColor Yellow
git branch -M main
git push -u origin main

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host ""

# Get and display repo URL
$repoUrl = gh repo view --json url --jq '.url'
Write-Host "Repository URL: $repoUrl" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Visit your repository: $repoUrl"
Write-Host "  2. Configure branch protection rules if needed"
Write-Host "  3. Add collaborators in Settings > Collaborators"
Write-Host ""
