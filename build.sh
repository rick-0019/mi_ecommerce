#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# ONE-TIME: Flush existing data and load backup
# Remove these 2 lines after the first successful deploy
python manage.py flush --no-input
python manage.py loaddata data_backup.json

python create_admin.py

