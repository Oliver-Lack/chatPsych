# Server Deployment Guide (chatPsych)

This method uses apache2, certbot, gunicorn, and Flask to deploy chatPsych as a web app Python environment.

## 0) Before you launch (Info only)
- Buy a domain. Point DNS to your server’s Elastic IP.
- Services for this deployment guide: AWS EC2, Ubuntu, Flask, Gunicorn, Apache2, Certbot.
- Note: you can deploy with any server running Ubuntu or similar Linux distro in the same way as described below.

## 1) Launch EC2 and SSH

Step 1: Launch an EC2 instance with Ubuntu 22.04 LTS.
- Choose an instance type (t3.medium good for 50ish participants concurrently).
- Configure security group to allow HTTP (80), HTTPS (443), and SSH (22) access.
- Download the key pair (e.g., `chatpsych.pem`) and set permissions:
From local computer directory holding the pem file run SSH terminal command:
For example: 
ssh -i "chatpsych.pem" ubuntu@ec2-52-64-0-79.ap-southeast-2.compute.amazonaws.com

## 2) Initial setup on the instance

While SSH into the EC2 instance — run:
sudo apt-get update
sudo apt-get install python3.venv
sudo mkdir /srv/chatpsych
sudo chown ubuntu:ubuntu /srv/chatpsych

## 3) Upload codebase to the server

Info only:
- From your local project folder, send files to /srv/chatpsych on the instance.

Local computer — run (pick one of examples below or make your own; edit paths/domains as needed):
Ex. rsync -avz -e "ssh -i /Users/a1809024/Desktop/PMC/AI_Interface/AWS/chatpsych.pem" ./* ubuntu@chatpsych-pilot.xyz:/srv/chatpsych/
Ex. rsync -avz --exclude="vent" --exclude="__pycache__" ../Chatpsych_1_0/ ubuntu@chatpsych.xyz:/srv/chatpsych/	
Ex. scp -i /Users/a1809024/Desktop/PMC/AI_Interface/AWS -r ./ ubuntu@chatpsych-pilot.xyz:/srv/chatpsych

Alternatively you could just clone chatPsych repository (or your own repository adaption) from GitHub using https: 
Ex. 
sudo apt install git-all
git clone https://github.com/Oliver-Lack/chatPsych.git

## 4) App environment and service

In EC2 instance — run:
cd /srv/chatpsych && ls -l
python3 -m venv venv
source venv/bin/activate
sudo apt install python3-pip
pip install Flask
pip install gunicorn
pip install -r requirements.txt
deactivate
sudo nano /etc/systemd/system/chatpsych.service

In EC2 instance — edit the now opened file (paste below, then Ctrl+O, Enter, Ctrl+X):
```nano
[Unit]
Description=Chatpsych Flask App
After=network.target

[Service]
User=chatpsych_user
Group=chatpsych_user
WorkingDirectory=/srv/chatpsych/
ExecStart=/srv/chatpsych/venv/bin/gunicorn chatpsych:app -w 4 -b 127.0.0.1:8000        
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Then, in EC2 instance — run:
sudo systemctl daemon-reload
sudo systemctl enable --now chatpsych.service
sudo apt install apache2
cd /etc/apache2/sites-available/
sudo rm default-ssl.conf
sudo service apache2 start
sudo mv 000-default.conf chatpsych.xyz.conf
sudo nano chatpsych.xyz.conf

In EC2 instance — edit file that is now open (paste, then Ctrl+O, Enter, Ctrl+X):
```nano
<VirtualHost *:80>
        ServerName chatpsych.xyz
        ServerAlias www.chatpsych.xyz

        ProxyPass / http://127.0.0.1:8000/
        ProxyPassReverse / http://127.0.0.1:8000/
</VirtualHost>
```

Then, in EC2 instance — run:
sudo a2enmod proxy proxy_http
sudo a2dissite 000-default.conf
sudo a2ensite chatpsych.xyz.conf
sudo service chatpsych start
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
sudo certbot --apache

Info only:
- In Certbot: set SSL for both domains by selecting 1, 2, Enter.

In EC2 instance — run:
sudo crontab -e

Info only:
- Choose nano “1”. Paste the line below to auto-renew. Save/exit.

EC2 instance — paste in crontab:
0 4 * * 1 /usr/bin/certbot --renew && /usr/sbin/service apache2 reload

In EC2 instance — run:
sudo adduser --system --no-create-home --group chatpsych_user
sudo nano /etc/systemd/system/chatpsych.service

Info only:
- Ensure [Service] has User=chatpsych_user and Group=chatpsych_user.

EC2 instance — run:
sudo chown -R chatpsych_user:chatpsych_user /srv/chatpsych/
sudo systemctl daemon-reload
sudo service chatpsych restart
sudo service chatpsych status

## 5) Environment variables

In EC2 instance — run:
cd /srv/chatpsych
source venv/bin/activate
sudo /srv/chatpsych/venv/bin/pip install python-dotenv
sudo nano /srv/chatpsych/.env

EC2 instance — edit file (example; put your real secrets. There is an example .env file in the chatPsych repo):
```nano
OPENAI_API_KEY=Secret Key

ANTHROPIC_API_KEY=Secret Key

FLASK_SECRET_KEY=Secret Key

researcher_username="chatpsych"
researcher_password="laplace666$"
```

EC2 instance — run:
sudo nano /etc/systemd/system/chatpsych.service

Info only:
- Add this line inside [Service]:
- EnvironmentFile=/srv/chatpsych/.env

EC2 instance — run:
sudo systemctl daemon-reload
sudo systemctl restart chatpsych
sudo systemctl status chatpsych
deactivate

## 6) Optional: swap (stability)

EC2 instance — run:
sudo fallocate -l 1G /swapfile
sudo chmod 0600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
free -m
sudo nano /etc/fstab

EC2 instance — edit file (add at end):
/swapfile       none            swap    sw              0 0

EC2 instance — run:
sudo reboot

## 7) Server Performance Logging

Info only:
- Logs CPU, memory, network. Runs in background.

In the EC2 instance — run:
mkdir -p /logs
cd /logs
sudo nano /logs/log_resources.sh

EC2 instance — edit file (paste):
while true; do
    sar -u 1 1 >> /logs/cpu_usage.log
    sar -r 1 1 >> /logs/memory_usage.log
    sar -n DEV 1 1 >> /logs/network_traffic.log
    sleep 10
done

In the EC2 instance — run:
chmod +x /logs/log_resources.sh
sudo nohup /logs/log_resources.sh &

Info only:
- To stop, find PID and kill.

EC2 instance — run:
ps aux | grep log_resources.sh
kill <PID>

## 8) Visualize logs (quick console plots)

In the EC2 instance — run:
cd /logs
sudo bash -c "awk '/^[0-9]/ {print \$1, \$8}' cpu_usage.log > cpu_plot_data.log"
sudo bash -c "awk '/^[0-9]/ {print \$1, \$8}' memory_usage.log > memory_plot_data.log"
sudo bash -c "awk '/^[0-9]/ {print \$1, \$8}' network_traffic.log > network_plot_data.log"

EC2 instance — run:
gnuplot <<-EOFMarker
    set terminal dumb
    set xdata time
    set timefmt "%H:%M:%S"
    set format x "%H:%M"

    set xlabel "Time"
    set ylabel "Idle (%)"
    plot "cpu_plot_data.log" using 1:2 with lines title "CPU Idle"

    set ylabel "Usage"
	set yrange [0:100]
    plot "memory_plot_data.log" using 1:2 with lines title "Memory Usage"

    set ylabel "Traffic (bytes)"
    plot "network_plot_data.log" using 1:2 with lines title "Network Traffic"
EOFMarker

## 9) Live monitoring

In the EC2 instance — run:
sudo apt install htop
htop

## 10) Final check (Info only)
- Visit your server IP or chatpsych domain. DNS may take up to 6 hours.

## Extra security measures (optional)

1. **Harden SSH**  
   Edit SSH config to improve security, 
   but you'll then need to specify this new port when SSH connecting:  
   ```
   sudo nano /etc/ssh/sshd_config
   ```
   - Change the SSH `Port` (e.g., 2222).
   - Set `PermitRootLogin no`.
   - Add `AllowUsers ubuntu`.
   ```
   sudo systemctl reload ssh
   sudo ufw allow 2222/tcp
   ```

2. **Enable Firewall (UFW)**  
   ```
   sudo ufw allow OpenSSH
   sudo ufw allow 80
   sudo ufw allow 443
   sudo ufw enable
   ```

3. **Disable Apache Directory Listing**  
   ```
   echo "Options -Indexes" | sudo tee -a /etc/apache2/apache2.conf
   sudo systemctl reload apache2
   ```

4. **Prevent Brute Force (Fail2ban)**
   ```
   sudo apt install fail2ban
   sudo systemctl enable --now fail2ban
   ```

5. **Automatic Security Updates**  
   ```
   sudo apt install unattended-upgrades
   sudo dpkg-reconfigure --priority=low unattended-upgrades
   ```

6. **Clean Up Unused Services/Packages**
   ```
   sudo apt autoremove
   sudo systemctl disable <unneeded_service>
   ```

7. **Run Web App As Dedicated Non-root User**  
   Already covered with `chatpsych_user`. Don’t use `root` for your app.

---

These steps can help secure your instance a bit more. Only do them after main deployment.