#!/bin/bash
# Exits immediately if a command exits with a non-zero status.
set -e

echo "--- Bootstrapping Project ---"

# Checks for Python 3
if ! command -v python3 &> /dev/null
then
    echo "Python 3 could not be found. Please install it."
    exit 1
fi

# Creates virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activates virtual environment and install dependencies
echo "Installing dependencies from requirements.txt..."
source .venv/bin/activate
pip install -r requirements.txt

# Creates .env file from example if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
fi

# Runs initial database migrations
echo "Running database migrations..."
python manage.py migrate

echo ""
echo "--- Bootstrap complete! ---"
echo "To start the server, run the following commands:"
echo "1. source .venv/bin/activate"
echo "2. python manage.py runserver"
