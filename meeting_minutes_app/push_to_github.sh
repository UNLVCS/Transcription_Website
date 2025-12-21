#!/bin/bash

# Quick Git Push Script for Meeting Minutes Generator
# This script helps you quickly push to GitHub

echo "=================================="
echo "Git Push Helper Script"
echo "=================================="
echo ""

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed. Install with: sudo apt install git"
    exit 1
fi

echo "Choose your option:"
echo ""
echo "1) Push to EXISTING repository as NEW BRANCH (Recommended)"
echo "2) Create NEW repository"
echo "3) Just show me the commands (I'll run them myself)"
echo ""
read -p "Enter your choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "📋 Pushing to existing repository as new branch..."
        echo ""
        read -p "Enter your existing repository path (e.g., ~/Transcription_Website): " repo_path
        read -p "Enter new branch name (e.g., production-ready): " branch_name
        
        if [ ! -d "$repo_path" ]; then
            echo "❌ Repository path does not exist: $repo_path"
            exit 1
        fi
        
        echo ""
        echo "Copying files..."
        cd "$repo_path"
        git checkout -b "$branch_name"
        cp -r "$(dirname "$0")"/* .
        
        echo ""
        echo "Adding files to git..."
        git add .
        
        echo ""
        echo "Files to be committed:"
        git status --short
        
        echo ""
        read -p "Enter commit message (or press Enter for default): " commit_msg
        if [ -z "$commit_msg" ]; then
            commit_msg="Production-ready Meeting Minutes Generator with Gemini API"
        fi
        
        git commit -m "$commit_msg"
        
        echo ""
        echo "Pushing to GitHub..."
        git push -u origin "$branch_name"
        
        echo ""
        echo "✅ Done! Your branch '$branch_name' has been pushed to GitHub."
        echo ""
        echo "Next steps:"
        echo "1. Visit your GitHub repository"
        echo "2. You should see a 'Compare & pull request' button"
        echo "3. Create a pull request to merge into main (optional)"
        ;;
        
    2)
        echo ""
        echo "📋 Creating new repository..."
        echo ""
        read -p "Enter your GitHub username: " username
        read -p "Enter new repository name (e.g., meeting-minutes-generator): " repo_name
        
        echo ""
        echo "⚠️  FIRST, create the repository on GitHub:"
        echo "1. Go to https://github.com/new"
        echo "2. Repository name: $repo_name"
        echo "3. Choose Public or Private"
        echo "4. DO NOT initialize with README"
        echo "5. Click 'Create repository'"
        echo ""
        read -p "Press Enter after you've created the repository on GitHub..."
        
        echo ""
        echo "Initializing local repository..."
        cd "$(dirname "$0")"
        git init
        git add .
        
        read -p "Enter commit message (or press Enter for default): " commit_msg
        if [ -z "$commit_msg" ]; then
            commit_msg="Initial commit: Production-ready Meeting Minutes Generator"
        fi
        
        git commit -m "$commit_msg"
        git branch -M main
        
        echo ""
        read -p "Use HTTPS or SSH? (https/ssh, default: https): " protocol
        if [ "$protocol" = "ssh" ]; then
            remote_url="git@github.com:$username/$repo_name.git"
        else
            remote_url="https://github.com/$username/$repo_name.git"
        fi
        
        git remote add origin "$remote_url"
        
        echo ""
        echo "Pushing to GitHub..."
        git push -u origin main
        
        echo ""
        echo "✅ Done! Your repository has been created and pushed to GitHub."
        echo "Visit: https://github.com/$username/$repo_name"
        ;;
        
    3)
        echo ""
        echo "📋 Here are the commands you need to run:"
        echo ""
        echo "=== Option A: Push to existing repo as new branch ==="
        echo ""
        echo "cd /path/to/your/existing/repository"
        echo "git checkout -b production-ready"
        echo "cp -r /path/to/meeting_minutes_app/* ."
        echo "git add ."
        echo "git commit -m 'Production-ready Meeting Minutes Generator'"
        echo "git push -u origin production-ready"
        echo ""
        echo "=== Option B: Create new repository ==="
        echo ""
        echo "# First create repo on GitHub: https://github.com/new"
        echo "cd /path/to/meeting_minutes_app"
        echo "git init"
        echo "git add ."
        echo "git commit -m 'Initial commit: Production-ready Meeting Minutes Generator'"
        echo "git remote add origin https://github.com/USERNAME/REPO_NAME.git"
        echo "git branch -M main"
        echo "git push -u origin main"
        echo ""
        echo "See GIT_PUSH_GUIDE.md for detailed instructions."
        ;;
        
    *)
        echo "❌ Invalid choice. Please run the script again and choose 1, 2, or 3."
        exit 1
        ;;
esac
