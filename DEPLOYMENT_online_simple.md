
# Deploy chatPsych with Docker, Nginx, and SSL

## 1. Prerequisites

- A machine or cloud instance
- **Docker** & **Docker Compose** installed
- A domain (e.g. `chatpsych-playground.org`) pointed to your server’s IP

First, Open a terminal in your machine.

## 2. Clone and Configure

```bash
sudo apt update
sudo apt install docker.io
sudo apt install docker-compose
sudo mkdir -p /srv/chatpsych
sudo chown $USER:$USER /srv/chatpsych
git clone https://github.com/Oliver-Lack/chatPsych.git /srv/chatpsych
cd /srv/chatpsych
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
sudo nano .dockerIgnore
sudo nano docker-compose.yml
```

## 5. Deploy!

```bash
sudo docker-compose up --build -d
```
Done. Visit your machines IP address or set custom domain that you connected.  

---

Ready to go.

---

## Want to check the Docker container is up and running?

```bash
sudo docker-compose ps
sudo docker-compose logs
```

## Having problems with DNS connection?
Setting up domain connected to instance may require double checking that you have an A record in your DNS pointing to the machines public IP.
Also, it may take a while (potentially hours) for DNS settings to propagate. Just do some web troubleshooting to make sure the machine has the correct 
open ports, and the Lets encrypt SSL certificate sometimes is delayed (some browsers don't like http at all. Lets encrypt makes it https).
To reset the container, incase you change DNS or instance settings after making the container:
```bash
sudo docker-compose down
sudo docker-compose up -d
```

## For extra security and backup...
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

## Want to Backup/Export Data into new directory called `data-copy`?

```bash
docker cp chatpsych_app_1:/app/data ./data-copy
# This copies the data directory from the app to a directory outside the container but in the instance/machine called data-copy
```
