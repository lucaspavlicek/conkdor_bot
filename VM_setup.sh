sudo apt update

sudo apt install python3-pip -y

sudo apt install python3-venv -y

python3 -m venv venv

./venv/bin/pip install -e .

cp conkdor_bot.service /etc/systemd/system/conkdor_bot.service