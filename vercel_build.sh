#!/bin/bash

echo "Creating instance folder..."
mkdir -p instance

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Applying database migrations..."
flask db upgrade

echo "Seeding database..."
python seed_dummy_data.py

echo "Build completed successfully" 