import subprocess
import os

def get_version_string(default='0.0.0'):
    # 1. Sprawdź, czy istnieje plik VERSION (dla pobranych ZIPów / wydań Docker)
    if os.path.exists('VERSION'):
        with open('VERSION', 'r', encoding='utf-8') as f:
            version = f.read().strip()
            if version:
                return version

    # 2. Jeśli nie ma pliku VERSION, spróbuj pobrać z narzędzia git
    commands = [
        ['git', 'describe', '--tags', '--dirty', '--always'],
        ['git', 'rev-parse', '--short', 'HEAD'],
    ]
    for command in commands:
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            version = result.stdout.strip()
            if version:
                return version
        except Exception:
            continue

    return default