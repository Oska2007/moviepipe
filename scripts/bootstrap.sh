#!/usr/bin/env bash
set -euo pipefail

echo "[1/6] Installing base packages..."
sudo apt-get update
sudo apt-get install -y ca-certificates curl git ufw

echo "[2/6] Installing Docker..."
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sudo sh
fi

echo "[3/6] Installing Docker Compose plugin..."
sudo apt-get install -y docker-compose-plugin

echo "[4/6] Configuring 2GB swap..."
if ! swapon --show | grep -q '/swapfile'; then
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi

echo "[5/6] Creating directories..."
mkdir -p data media temp

echo "[6/6] Firewall..."
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

echo "Bootstrap complete. Now copy .env.example to .env and configure credentials."