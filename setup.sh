# setup.sh — one-click deployment script
#!/bin/bash

echo "🚀 Setting up Telegram Bot..."

# Install dependencies
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# Create project directory
mkdir -p ~/tg-bot
cd ~/tg-bot

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt

# Create systemd service
sudo cp tg-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tg-bot
sudo systemctl start tg-bot

# Setup cron for broadcasts
(crontab -l 2>/dev/null; echo "0 10 1,15 * * /home/$USER/tg-bot/venv/bin/python /home/$USER/tg-bot/broadcast_scheduler.py 'Скидка 20% на все абонементы до конца месяца!'") | crontab -

echo "✅ Bot deployed successfully!"
echo "📊 Status: sudo systemctl status tg-bot"