#!/bin/bash
echo "Activating virtual environment"
source ./venv/bin/activate

# Check if any process is running on port 80
if lsof -i :80; then
    echo "A process is already running on port 80."
    read -p "Do you want to kill it? (y/n): " confirm
    if [[ $confirm == "y" ]]; then
        # Get the PID of the process running on port 80
        pid=$(lsof -t -i :80)
        echo "Killing process with PID: $pid"
        sudo kill -9 $pid
    else
        echo "Exiting script."
        exit 1
    fi
fi

# Ask for the number of workers
read -p "Enter the number of workers (default is 4): " workers
workers=${workers:-4}  # Default to 4 if no input

# Ask for the port
read -p "Enter the port (default is 80): " port
port=${port:-80}  # Default to 80 if no input

echo "Starting Gunicorn on port $port with $workers workers"
echo "You may be prompted for your password to run the following command with sudo."
sudo gunicorn -w $workers -b 0.0.0.0:$port run:app &

# Print the process ID of Gunicorn
echo "Gunicorn started with PID: $!"