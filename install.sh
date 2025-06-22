#!/bin/bash

# PKOS Linux Mirrorlist Manager Installation Script
# Developer: Aamir Abdullah
# Email: aamirabdullah33@gmail.com
# License: Open Source

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Application info
APP_NAME="PKOS Linux Mirrorlist Manager"
APP_VERSION="2.0.0"
DEVELOPER="Aamir Abdullah"
EMAIL="aamirabdullah33@gmail.com"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}║           ${GREEN}PKOS Linux Mirrorlist Manager${BLUE}                    ║${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}║  ${YELLOW}Version:${NC} ${APP_VERSION}                                        ${BLUE}║${NC}"
echo -e "${BLUE}║  ${YELLOW}Developer:${NC} ${DEVELOPER}                              ${BLUE}║${NC}"
echo -e "${BLUE}║  ${YELLOW}Email:${NC} ${EMAIL}                        ${BLUE}║${NC}"
echo -e "${BLUE}║  ${YELLOW}License:${NC} Open Source (MIT)                              ${BLUE}║${NC}"
echo -e "${BLUE}║                                                              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo

# Check if running on Arch-based system
if ! command -v pacman &> /dev/null; then
    echo -e "${RED}Error: This application is designed for Arch Linux and Arch-based distributions.${NC}"
    echo -e "${YELLOW}pacman package manager not found.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Arch-based system detected${NC}"

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not installed.${NC}"
    echo -e "${YELLOW}Please install Python 3: sudo pacman -S python${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
echo -e "${GREEN}✓ Python ${PYTHON_VERSION} found${NC}"

# Check for required dependencies
echo -e "${BLUE}Checking dependencies...${NC}"

MISSING_DEPS=()

if ! python3 -c "import PyQt6" &> /dev/null; then
    MISSING_DEPS+=("python-pyqt6")
fi

if ! python3 -c "import requests" &> /dev/null; then
    MISSING_DEPS+=("python-requests")
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo -e "${YELLOW}Missing dependencies detected: ${MISSING_DEPS[*]}${NC}"
    echo -e "${BLUE}Installing dependencies...${NC}"
    
    if sudo pacman -S --needed "${MISSING_DEPS[@]}"; then
        echo -e "${GREEN}✓ Dependencies installed successfully${NC}"
    else
        echo -e "${RED}Error: Failed to install dependencies${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ All dependencies are satisfied${NC}"
fi

# Create application directory
APP_DIR="/opt/pkos-mirrorlist-manager"
echo -e "${BLUE}Creating application directory...${NC}"

if sudo mkdir -p "$APP_DIR"; then
    echo -e "${GREEN}✓ Application directory created: $APP_DIR${NC}"
else
    echo -e "${RED}Error: Failed to create application directory${NC}"
    exit 1
fi

# Copy application files
echo -e "${BLUE}Installing application files...${NC}"

if sudo cp -r . "$APP_DIR/"; then
    echo -e "${GREEN}✓ Application files copied${NC}"
else
    echo -e "${RED}Error: Failed to copy application files${NC}"
    exit 1
fi

# Set permissions
sudo chmod +x "$APP_DIR/main.py"
sudo chmod +x "$APP_DIR/main_improved.py"
sudo chmod +x "$APP_DIR/install.sh"

# Create desktop entry
DESKTOP_FILE="/usr/share/applications/pkos-mirrorlist-manager.desktop"
echo -e "${BLUE}Creating desktop entry...${NC}"

sudo tee "$DESKTOP_FILE" > /dev/null << EOF
[Desktop Entry]
Name=PKOS Linux Mirrorlist Manager
Comment=Manage Arch Linux mirror lists with a modern GUI
GenericName=Mirror List Manager
Exec=python3 $APP_DIR/main.py
Icon=preferences-system-network
Terminal=false
Type=Application
Categories=System;Settings;Network;
Keywords=mirror;pacman;arch;linux;pkos;network;repository;
StartupNotify=true

# Branding Information
X-PKOS-Developer=$DEVELOPER
X-PKOS-Email=$EMAIL
X-PKOS-License=Open Source
X-PKOS-Version=$APP_VERSION
EOF

if [ -f "$DESKTOP_FILE" ]; then
    echo -e "${GREEN}✓ Desktop entry created${NC}"
else
    echo -e "${RED}Error: Failed to create desktop entry${NC}"
fi

# Create command line shortcuts
echo -e "${BLUE}Creating command line shortcuts...${NC}"

# Main application launcher
sudo tee "/usr/local/bin/pkos-mirrorlist-manager" > /dev/null << EOF
#!/bin/bash
# PKOS Linux Mirrorlist Manager
# Developer: $DEVELOPER
# Email: $EMAIL
cd "$APP_DIR"
python3 main.py "\$@"
EOF

sudo chmod +x "/usr/local/bin/pkos-mirrorlist-manager"

echo -e "${GREEN}✓ Command line shortcuts created${NC}"

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    sudo update-desktop-database /usr/share/applications/
    echo -e "${GREEN}✓ Desktop database updated${NC}"
fi

# Installation complete
echo
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║                    INSTALLATION COMPLETE!                   ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}╚═════════════════════════════════════════════════════��════════╝${NC}"
echo
echo -e "${BLUE}How to run:${NC}"
echo -e "  ${YELLOW}Command Line:${NC} pkos-mirrorlist-manager"
echo -e "  ${YELLOW}From Menu:${NC}    Look for 'PKOS Linux Mirrorlist Manager' in System settings"
echo
echo -e "${BLUE}Application Details:${NC}"
echo -e "  ${YELLOW}Installed to:${NC}   $APP_DIR"
echo -e "  ${YELLOW}Desktop Entry:${NC}  $DESKTOP_FILE"
echo -e "  ${YELLOW}Developer:${NC}      $DEVELOPER"
echo -e "  ${YELLOW}Email:${NC}          $EMAIL"
echo -e "  ${YELLOW}License:${NC}        Open Source (MIT)"
echo -e "  ${YELLOW}Version:${NC}        $APP_VERSION"
echo
echo -e "${GREEN}Thank you for using PKOS Linux Mirrorlist Manager!${NC}"
echo -e "${BLUE}For support, please contact: ${EMAIL}${NC}"
echo