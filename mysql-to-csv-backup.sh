#!/bin/bash

# Activate the virtual environment
source .venv/bin/activate

# Run the backup_tables function from backup_tools.py
python -c "from backup_tools import backup_tables; backup_tables()"

# Deactivate the virtual environment
deactivate