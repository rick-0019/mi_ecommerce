#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
python create_admin.py

# ONE-TIME: Load local data backup into production DB
# Remove this line after the first successful deploy
python manage.py loaddata data_backup.json
