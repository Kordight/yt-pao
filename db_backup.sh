#!/bin/bash

# Configuration
PROJECT_DIR="/home/sebastian/yt-pao" # Replace with your path
ENV_FILE="$PROJECT_DIR/.env"

# Check dependencies
command -v mysqldump >/dev/null 2>&1 || { echo "mysqldump not found. Install it first."; exit 1; }

# Function to read configuration from environment / .env file
read_config() {
    if [ -f "$ENV_FILE" ]; then
        set -a
        source "$ENV_FILE"
        set +a
    fi

    DB_HOST=${DB_HOST:-localhost}
    DB_USER=${DB_USER:-yt-pao}
    DB_PASSWORD=${DB_PASSWORD:-password}
    DB_NAME=${DB_NAME:-yt_pao_db}
    DB_PORT=${DB_PORT:-3306}

    if [[ -z "$DB_HOST" || -z "$DB_USER" || -z "$DB_PASSWORD" || -z "$DB_NAME" ]]; then
        echo "Error: One or more required database configuration values are missing in environment variables."
        exit 1
    fi
}


# Function to create a backup
create_backup() {
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_DIR="$PROJECT_DIR/backups"
    BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_backup_$TIMESTAMP.sql"
    mkdir -p "$BACKUP_DIR"

    if mysqldump -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" --no-tablespaces "$DB_NAME" > "$BACKUP_FILE"; then
        echo "Backup successful: $BACKUP_FILE"
    else
        echo "Backup failed!"
        exit 1
    fi
}

# Run functions
read_config
create_backup
