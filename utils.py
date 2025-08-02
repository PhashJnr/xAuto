import random
import re
import os
from datetime import datetime

def spin_text(template):
    # Simple text spinner using {a|b|c} syntax
    def _spin(match):
        options = match.group(1).split('|')
        return random.choice(options)
    pattern = re.compile(r'\{([^{}]+)\}')
    while pattern.search(template):
        template = pattern.sub(_spin, template)
    return template

def log(message, acc=None):
    label = f"[{acc.label}] " if acc else ""
    print(label + message)

def log_to_file(panel_name, message):
    os.makedirs('logs', exist_ok=True)
    log_path = os.path.join('logs', f'{panel_name}.log')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f'[{timestamp}] {message}\n') 