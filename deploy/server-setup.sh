#!/usr/bin/env bash
# One-time setup of a fresh Ubuntu 24.04 server. Run as root:
#   ssh root@SERVER_IP 'bash -s' < deploy/server-setup.sh
# Creates the `deploy` user (same SSH keys as root), installs Docker, git and make, turns on the
# firewall (SSH, HTTP, HTTPS), adds 2 GB swap, automatic security updates, and turns off SSH
# password logins. Safe to run again.
set -euo pipefail

APP_DIR=/opt/kg-tours

echo "==> packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get upgrade -yq
apt-get install -yq git make ufw unattended-upgrades ca-certificates curl

echo "==> docker"
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi

echo "==> user deploy"
if ! id deploy >/dev/null 2>&1; then
  adduser --disabled-password --gecos "" deploy
fi
usermod -aG docker deploy
install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
if [ -f /root/.ssh/authorized_keys ]; then
  install -m 600 -o deploy -g deploy /root/.ssh/authorized_keys /home/deploy/.ssh/authorized_keys
fi
install -d -o deploy -g deploy "$APP_DIR"

echo "==> firewall"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp
ufw --force enable

echo "==> swap (2 GB: the frontend build needs memory on small servers)"
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q /swapfile /etc/fstab || echo "/swapfile none swap sw 0 0" >> /etc/fstab
fi

echo "==> automatic security updates"
dpkg-reconfigure -f noninteractive unattended-upgrades

echo "==> ssh: keys only"
if [ -s /home/deploy/.ssh/authorized_keys ]; then
  # A drop-in read before cloud-init's 50-*.conf (the first value wins in sshd).
  printf 'PasswordAuthentication no\nKbdInteractiveAuthentication no\n' > /etc/ssh/sshd_config.d/00-keys-only.conf
  sshd -t
  # Ubuntu 24.04+ starts sshd per connection (ssh.socket): new logins read the file anyway.
  systemctl reload ssh 2>/dev/null || systemctl reload sshd 2>/dev/null || true
else
  echo "   (skipped: no SSH key found for root, password login stays on)"
fi

echo
echo "Done. Next, from your laptop:  ssh deploy@$(hostname -I | awk '{print $1}')"
