#!/bin/bash
set -e

cd /home/evgeniy/project/promelectron
make dev

echo "Waiting for services to start..."
sleep 5

echo "Backend health:"
curl -s http://localhost:8000/ | head -1 || echo "Backend not ready yet"

echo "Frontend health:"
curl -s http://localhost:5173/ | head -1 || echo "Frontend not ready yet"
