#!/bin/bash
set -e

cd backend

if [ ! -d "myenv" ]; then
    echo "Creating virtual environment..."
    /opt/homebrew/bin/python3.11 -m venv myenv
fi

echo "Activating virtual environment..."
source myenv/bin/activate

echo "Installing/Updating dependencies..."
pip install -r requirements.txt

echo "Starting server..."
uvicorn main:app --reload --port 8000
