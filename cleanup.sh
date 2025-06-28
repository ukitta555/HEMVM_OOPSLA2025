#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Cleaning up Docker resources...${NC}"

# Stop and remove the container if it's running
echo -e "${YELLOW}Stopping and removing container...${NC}"
docker stop movexether-testnet-container 2>/dev/null || true
docker rm movexether-testnet-container 2>/dev/null || true

# Remove the image
echo -e "${YELLOW}Removing image...${NC}"
docker rmi movexether-testnet 2>/dev/null || true

# Optional: Clean up all unused Docker resources
read -p "Do you want to clean up all unused Docker resources? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Cleaning up all unused Docker resources...${NC}"
    docker system prune -a -f
fi

echo -e "${GREEN}Cleanup complete!${NC}"

# Show remaining Docker resources
echo -e "\n${YELLOW}Remaining Docker resources:${NC}"
echo -e "${YELLOW}Images:${NC}"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | head -10

echo -e "\n${YELLOW}Containers:${NC}"
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Size}}" | head -10

echo -e "\n${YELLOW}Disk usage:${NC}"
docker system df 