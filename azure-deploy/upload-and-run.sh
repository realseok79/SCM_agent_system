#!/bin/bash

# ─────────────────────────────────────────────────────────────
# SCM Agent System - Direct Local Upload & Deploy Script
# ─────────────────────────────────────────────────────────────

# Exit immediately if a command exits with a non-zero status
set -e

# Move to the project root directory
cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ── Configuration (Modify if needed) ──
VM_IP=${VM_IP:-"20.41.110.255"}
VM_USER=${VM_USER:-"azureuser"}
KEY_PATH=${KEY_PATH:-"/Users/leejinseok/Downloads/SCM-agent_key.pem"}
ARCHIVE_NAME="scm_agent_deploy.tar.gz"
REMOTE_DEPLOY_DIR="scm-agent-deploy"

echo -e "${BLUE}🚀 Preparing to deploy local project directly to Azure VM ($VM_IP)...${NC}"
echo -e "🔑 SSH Key Path: ${GREEN}$KEY_PATH${NC}"
echo -e "👤 SSH User: ${GREEN}$VM_USER${NC}"

# Ensure correct permissions on the local private key
chmod 600 "$KEY_PATH"

# ── 1. Create a Lightweight Archive of Current Local Folder ──
echo -e "${YELLOW}[Step 1/3] Compressing current local directory...${NC}"

# Exclude large, system, or runtime folders to keep upload fast
tar --exclude='node_modules' \
    --exclude='.git' \
    --exclude='venv' \
    --exclude='*.db' \
    --exclude='__pycache__' \
    --exclude='outputs' \
    --exclude='.pytest_cache' \
    -czf "$ARCHIVE_NAME" .

echo -e "${GREEN}✓ Local directory compressed successfully: $ARCHIVE_NAME${NC}"

# ── 2. Copy the Archive to the VM ──
echo -e "${YELLOW}[Step 2/3] Uploading archive to VM via SCP...${NC}"

scp -o StrictHostKeyChecking=no -i "$KEY_PATH" "$ARCHIVE_NAME" "$VM_USER@$VM_IP:~/"

echo -e "${GREEN}✓ Upload completed successfully!${NC}"

# Clean up local archive
rm "$ARCHIVE_NAME"

# ── 3. Extract and Launch on the VM ──
echo -e "${YELLOW}[Step 3/3] Extracting and running SCM Agent System on VM...${NC}"

ssh -o StrictHostKeyChecking=no -i "$KEY_PATH" "$VM_USER@$VM_IP" << EOF
  set -e
  echo "📦 Extracting files on remote VM..."
  mkdir -p "$REMOTE_DEPLOY_DIR"
  tar -xzf "$ARCHIVE_NAME" -C "$REMOTE_DEPLOY_DIR"
  rm "$ARCHIVE_NAME"
  
  echo "🚀 Launching VM bootstrap..."
  cd "$REMOTE_DEPLOY_DIR"
  chmod +x azure-deploy/vm-setup.sh
  
  # Inject the local SCM_agent_system folder path inside the VM setup context
  # Run the VM bootstrap script locally inside the folder
  ./azure-deploy/vm-setup.sh
EOF

echo -e "\n${GREEN}🎉 Successfully uploaded and deployed SCM Agent System directly from your computer!${NC}"
echo -e "👉 Streamlit UI URL: ${BLUE}http://$VM_IP:8501${NC}\n"
