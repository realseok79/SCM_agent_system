#!/bin/bash

# ─────────────────────────────────────────────────────────────
# SCM Agent System - Direct Local Upload & Deploy (Password Version)
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

# ── Configuration ──
VM_IP=${VM_IP:-"20.41.110.255"}
VM_USER=${VM_USER:-"azureuser"}
ARCHIVE_NAME="scm_agent_deploy.tar.gz"
REMOTE_DEPLOY_DIR="scm-agent-deploy"

# Configure control path for SSH multiplexing (reuses single password prompt)
SOCKET_DIR="$HOME/.ssh/sockets"
mkdir -p "$SOCKET_DIR"
SOCKET="$SOCKET_DIR/scm_control_socket"

# Clean up any old sockets
rm -f "$SOCKET"

echo -e "${BLUE}🚀 Starting SCM Agent System Password-based Deployment...${NC}"
echo -e "📍 Target VM: ${GREEN}$VM_IP${NC}"
echo -e "👤 SSH User: ${GREEN}$VM_USER${NC}"
echo -e "🔑 Password you set: ${YELLOW}Scm_Secure_Password_2026!${NC}"

# ── 1. Create a Lightweight Archive of Current Local Folder ──
echo -e "${YELLOW}[Step 1/4] Compressing current local directory...${NC}"

tar --exclude='node_modules' \
    --exclude='.git' \
    --exclude='venv' \
    --exclude='*.db' \
    --exclude='__pycache__' \
    --exclude='outputs' \
    --exclude='.pytest_cache' \
    -czf "$ARCHIVE_NAME" .

echo -e "${GREEN}✓ Local directory compressed successfully.${NC}"

# ── 2. Establish Secure Master SSH Connection ──
echo -e "${YELLOW}[Step 2/4] Connecting to VM...${NC}"
echo -e "👇 ${BLUE}Please type or paste your password (${YELLOW}Scm_Secure_Password_2026!${BLUE}) when prompted below:${NC}"

# Open the master SSH connection in the background
ssh -M -S "$SOCKET" -fN -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$VM_USER@$VM_IP"

echo -e "${GREEN}✓ Connection session established! (Password not needed for subsequent steps)${NC}"

# ── 3. Copy the Archive using the Master Connection ──
echo -e "${YELLOW}[Step 3/4] Uploading project archive via secure channel...${NC}"

scp -o ControlPath="$SOCKET" "$ARCHIVE_NAME" "$VM_USER@$VM_IP:~/"

echo -e "${GREEN}✓ Upload completed successfully!${NC}"

# Clean up local archive
rm "$ARCHIVE_NAME"

# ── 4. Extract and Launch on the VM ──
echo -e "${YELLOW}[Step 4/4] Extracting and running SCM Agent System on VM...${NC}"

ssh -o ControlPath="$SOCKET" "$VM_USER@$VM_IP" << EOF
  set -e
  echo "📦 Extracting files on remote VM..."
  mkdir -p "$REMOTE_DEPLOY_DIR"
  tar -xzf "$ARCHIVE_NAME" -C "$REMOTE_DEPLOY_DIR"
  rm -f "$ARCHIVE_NAME"
  
  echo "🚀 Launching VM bootstrap..."
  cd "$REMOTE_DEPLOY_DIR"
  chmod +x azure-deploy/vm-setup.sh
  ./azure-deploy/vm-setup.sh
EOF

# ── 5. Terminate the Master Connection and socket cleanup ──
echo -e "${YELLOW}🧹 Closing secure session...${NC}"
ssh -S "$SOCKET" -O exit "$VM_USER@$VM_IP" 2>/dev/null || true
rm -f "$SOCKET"

echo -e "\n${GREEN}🎉 Successfully uploaded and deployed SCM Agent System directly from your computer!${NC}"
echo -e "👉 Streamlit UI URL: ${BLUE}http://$VM_IP:8501${NC}\n"
