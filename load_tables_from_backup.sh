#!/bin/bash

# Activate the virtual environment
source .venv/bin/activate

# The time_stamp is the first argument passed to the script (choose from static/backups/)
time_stamp=$1

# Run the backup_tables function from backup_tools.py
python -c "from backup_tools import load_tables_from_backup; load_tables_from_backup('$time_stamp')"

# Deactivate the virtual environment
deactivate