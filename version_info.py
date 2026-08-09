import subprocess


def get_version_string(default='0.0.0'):
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