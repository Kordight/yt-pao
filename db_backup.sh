#!/bin/bash

# Configuration
PROJECT_DIR="/home/sebastian/yt-pao" # Replace with your path
CONFIG_YAML="$PROJECT_DIR/config.yaml"

# Check if config exists
if [ ! -f "$CONFIG_YAML" ]; then
    echo "Config file $CONFIG_YAML not found!"
    exit 1
fi

# Check dependencies
command -v yq >/dev/null 2>&1 || { echo "yq not found. Install it first."; exit 1; }
command -v mysqldump >/dev/null 2>&1 || { echo "mysqldump not found. Install it first."; exit 1; }

# Function to read configuration from YAML file
read_config() {
    DB_HOST=$(yq '.database.host' "$CONFIG_YAML")
    DB_USER=$(yq '.database.user' "$CONFIG_YAML")
    DB_PASSWORD=$(yq '.database.password' "$CONFIG_YAML")
    DB_NAME=$(yq '.database.database' "$CONFIG_YAML")
    DB_PORT=$(yq '.database.port' "$CONFIG_YAML")
    DB_PORT=${DB_PORT:-3306}

    # Check for missing configuration values
    if [[ -z "$DB_HOST" || -z "$DB_USER" || -z "$DB_PASSWORD" || -z "$DB_NAME" || -z "$DB_PORT" ]]; then
        echo "Error: One or more required database configuration values are missing in $CONFIG_YAML."
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
