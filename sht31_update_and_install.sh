#!/bin/bash
# SHT31 server maintenance script: update code and install dependencies.
# Run this script manually before restarting the SHT31 server whenever
# you want to pull the latest develop branch or refresh Python dependencies.
# This is intentionally separate from the autostart desktop entry so that
# network or PyPI outages during updates do not prevent the server from
# starting on login.

set -e

cd /home/pi/github/ThermostatSupervisor

echo "Checking out develop branch and pulling latest changes..."
git checkout develop
git pull

echo "Updating autostart desktop entry..."
mkdir -p /home/pi/.config/autostart
cp sht31_autostart_desktop /home/pi/.config/autostart/lxterm-autostart.desktop

echo "Installing/updating Python dependencies..."
pip install -r requirements.txt -r requirements_sht31.txt

echo "Update complete. Restart the SHT31 server to apply changes."
