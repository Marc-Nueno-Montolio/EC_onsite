#!/bin/bash

# Ask for the port number
read -p "Enter the port number to kill processes running on: " port

# Check if any process is running on the specified port
if lsof -i :$port; then
    echo "Processes running on port $port:"
    lsof -i :$port

    # Ask for confirmation to kill the processes
    read -p "Do you want to kill these processes? (y/n): " confirm
    if [[ $confirm == "y" ]]; then
        # Get the PIDs of the processes running on the specified port
        pids=$(lsof -t -i :$port)
        echo "Killing processes with PIDs: $pids"
        sudo kill -9 $pids
        echo "Processes killed."
    else
        echo "No processes were killed."
    fi
else
    echo "No processes are running on port $port."
fi
