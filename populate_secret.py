import secrets
import re

def populate_secret_key(config_file="config.py"):
    with open(config_file, "r") as f:
        content = f.read()
    new_key = secrets.token_hex(32)
    updated = re.sub(r'SECRET_KEY\s*=.*', f'SECRET_KEY = "{new_key}"', content)
    with open(config_file, "w") as f:
        f.write(updated)

if __name__ == "__main__":
    populate_secret_key()
