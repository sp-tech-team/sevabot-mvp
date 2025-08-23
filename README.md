# Steps to Push Your Code to GitHub

## 1. Create folder structure for images
mkdir -p images/v1

## 2. Add your screenshot files
# Take screenshots and save them as:
# - images/v1/login.png (Login page screenshot)
# - images/v1/file-manager.png (File Manager tab screenshot)  
# - images/v1/chat.png (Chat interface screenshot)

## 3. Create .gitignore file
echo "# Environment and secrets
.env
.env.local
.env.production

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/

# RAG data (will be recreated)
user_documents/
rag_index/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Keep images folder but ignore temp files
images/**/.DS_Store" > .gitignore

## 4. Initialize Git repository (if not already done)
git init

## 5. Add all files to Git (including images)
git add .
git add images/v1/*.png

## 6. Create initial commit
git commit -m "Initial commit: Sevabot RAG Assistant

- Multi-user document Q&A system
- Google OAuth authentication  
- RAG with ChromaDB and OpenAI
- Gradio web interface
- Feedback system and session management
- Added screenshots for documentation"

## 7. Create GitHub repository
# Go to GitHub.com and create a new repository named 'sevabot'
# Do NOT initialize with README (we already have one)
# Make it private for now

## 8. Link your local repo to GitHub
# Replace YOUR_USERNAME with your actual GitHub username
git remote add origin https://github.com/YOUR_USERNAME/sevabot.git

## 9. Push to GitHub
git branch -M main
git push -u origin main

## 10. Verify the upload
# Go to https://github.com/YOUR_USERNAME/sevabot
# You should see all your files uploaded including the images folder
# Check that the README.md shows the screenshots properly

## 11. Set up GitHub Secrets (for deployment)
# Go to your repo > Settings > Secrets and Variables > Actions
# Add these secrets:
# - SUPABASE_URL
# - SUPABASE_KEY  
# - SUPABASE_SERVICE_ROLE_KEY
# - OPENAI_API_KEY
# - COOKIE_SECRET

## 12. Future updates
# When you make changes:
git add .
git commit -m "Description of your changes"
git push

## Alternative: If you prefer SSH (more secure)
# First set up SSH key with GitHub, then use:
# git remote add origin git@github.com:YOUR_USERNAME/sevabot.git