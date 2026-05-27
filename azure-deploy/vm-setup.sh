#!/bin/bash

# ─────────────────────────────────────────────────────────────
# SCM Agent System - Azure VM Automated Setup & Deployment Script
# ─────────────────────────────────────────────────────────────

# Exit immediately if a command exits with a non-zero status
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting SCM Agent System VM Bootstrap on Azure...${NC}"

# ── 1. Check OS and Install Docker ──
echo -e "${YELLOW}[Step 1/5] Checking Docker installation...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}🐳 Docker not found. Installing Docker...${NC}"
    
    # Update package index
    sudo apt-get update -y
    
    # Install prerequisites
    sudo apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
        
    # Add Docker's official GPG key
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes
    
    # Set up the stable repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
      
    # Install Docker Engine
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    # Start and enable Docker service
    sudo systemctl start docker
    sudo systemctl enable docker
    
    # Add current user to docker group to run without sudo
    sudo usermod -aG docker $USER
    
    echo -e "${GREEN}✓ Docker installed and configured successfully!${NC}"
else
    echo -e "${GREEN}✓ Docker is already installed.${NC}"
fi

# ── 2. Check and Install Docker Compose ──
echo -e "${YELLOW}[Step 2/5] Checking Docker Compose installation...${NC}"

if ! docker compose version &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}🐙 Installing Docker Compose...${NC}"
    sudo apt-get install -y docker-compose
    echo -e "${GREEN}✓ Docker Compose installed successfully!${NC}"
else
    echo -e "${GREEN}✓ Docker Compose is already installed.${NC}"
fi

# ── 3. Clone Repository or Use Local Upload ──
echo -e "${YELLOW}[Step 3/5] Setting up the project repository...${NC}"

if [ -f "docker-compose.yml" ]; then
    echo -e "${GREEN}✓ Local upload detected (docker-compose.yml is present). Skipping repository cloning.${NC}"
elif [ -f "../docker-compose.yml" ]; then
    echo -e "${GREEN}✓ Local upload detected in parent directory. Moving up.${NC}"
    cd ..
else
    REPO_DIR="SCM_agent_system"
    if [ -d "$REPO_DIR" ]; then
        echo -e "${YELLOW}⚠ Directory $REPO_DIR already exists. Pulling latest updates...${NC}"
        cd "$REPO_DIR"
        git pull
    else
        echo -e "${BLUE}📥 Cloning repository...${NC}"
        git clone https://github.com/realseok79/SCM_agent_system.git
        cd "$REPO_DIR"
    fi
fi

# ── 4. Set up Environment Variables (.env) ──
echo -e "${YELLOW}[Step 4/5] Setting up environment variables (.env)...${NC}"

if [ ! -f .env ]; then
    echo -e "Creating default .env file..."
    cp .env.example .env
fi

# Keep existing DB_PASSWORD or set a secure one
sed -i 's/DB_PASSWORD=scm_secure_2026/DB_PASSWORD=scm_secure_2026/g' .env

# We will let the user know how to add their Gemini / OpenAI API key
echo -e "${GREEN}✓ Environment configured.${NC}"

# ── 5. Run the Multi-Container Application ──
echo -e "${YELLOW}[Step 5/5] Launching multi-container setup via Docker Compose...${NC}"

# Detect docker compose version and use the available one
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo -e "${RED}❌ Neither 'docker compose' nor 'docker-compose' command was found!${NC}"
    exit 1
fi

echo -e "🚀 Using Compose Command: ${BLUE}$COMPOSE_CMD${NC}"

# Rebuild and recreate only the frontend container safely to bypass docker-compose v1 bugs
$COMPOSE_CMD build frontend
$COMPOSE_CMD stop frontend || true
$COMPOSE_CMD rm -f frontend || true
$COMPOSE_CMD up -d frontend

echo -e "\n${GREEN}🎉 SCM Agent System successfully deployed on the VM!${NC}"
echo -e "🐳 Active Containers:${NC}"
$COMPOSE_CMD ps

echo -e "\n${YELLOW}💡 IMPORTANT NETWORK SECURITY GROUP (NSG) STEP:${NC}"
echo -e "To access the Streamlit UI from your browser, please ensure you open port ${GREEN}8501${NC} in the Azure Portal NSG (Network Security Group) for this VM!"
echo -e "👉 ${BLUE}http://20.41.110.255:8501${NC}\n"
