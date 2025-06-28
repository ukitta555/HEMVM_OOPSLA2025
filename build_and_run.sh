#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building MoveEth Docker container...${NC}"

# Build the Docker image
# docker build -t movexether-testnet . --progress=plain --no-cache
docker build -t movexether-testnet .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Build successful!${NC}"
    echo -e "${YELLOW}Image size:${NC}"
    docker images movexether-testnet --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
    
    echo -e "\n${GREEN}Starting the testnet...${NC}"
    echo -e "${YELLOW}The testnet will be available on port 8081${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop the container${NC}"
    
    # Run the container
    docker run --rm --name movexether-testnet-container movexether-testnet
    
else
    echo -e "${RED}Build failed!${NC}"
    exit 1
fi 