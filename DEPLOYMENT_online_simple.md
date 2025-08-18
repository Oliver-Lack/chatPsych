
# Deploy chatPsych with Docker, Nginx, and SSL

## 1. Prerequisites

- A machine or cloud instance
- **Docker** & **Docker Compose** installed
- A domain (e.g. `chatpsych-playground.org`) pointed to your server’s IP

First, Open a terminal in your machine.

## 2. Clone and Configure

```bash
git clone https://github.com/Oliver-Lack/chatPsych.git
cd chatPsych
cp .env.example .env
sudo nano .env   # fill in your API keys & secrets then control+O, enter, then control+X
```

## 3. Setup the Docker Build
Go to the chatpsych directory that was just cloned and sudo nano each of the files below. 
Change the required details. For example, the email and domain names in the docker-compose.yml. 
For custom domain, edit `VIRTUAL_HOST` and `LETSENCRYPT_HOST` in `docker-compose.yml` to the new domain.
Most of the other settings can remain as default.

```
sudo nano Dockerfile
sudo nano .dockerignore
sudo nano docker-compose.yml
```

## 5. Deploy!

```bash
docker compose up --build -d
```
Done. Visit: https://chatpsych-playground.org  
SSL certs are automatic.

## 7. Backup/Export Data

```bash
docker compose exec app bash
# or:
docker cp chatpsych_app_1:/app/data ./data-copy
# This copies the data directory from the app to a directory outside the container but in the instance/machine called data-copy
```

---

Ready to go.

---

## For extra security...
While connected to your machine, consider setting up a firewall and fail2ban to protect your services. Also, setting up some swap space can help prevent memory issues.
Here is some example commands you can put into the terminal outside of the Docker container:
```bash
# Swap space
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -m
# Firewall
sudo apt install ufw
sudo ufw allow OpenSSH
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
# Host-level: Install and configure fail2ban to protect against brute-force attacks
sudo apt install fail2ban
sudo systemctl enable --now fail2ban
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo nano /etc/fail2ban/jail.local
# (Optional: tune settings in [sshd] or other sections)
sudo systemctl restart fail2ban
sudo fail2ban-client status
sudo fail2ban-client status sshd
```