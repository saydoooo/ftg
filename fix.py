import os
from copy import deepcopy

for mod in os.scandir("."):
    if not mod.path.endswith(".py") or mod.path.endswith("fix.py"):
        continue

    with open(mod.path, "r") as f:
        code = f.read()

    old_code = deepcopy(code)

    code = code.replace(
        '''"""
    █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
    █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█

    © Copyright 2022 t.me/hikariatama
    Licensed under CC BY-NC-ND 4.0

    🌐 https://creativecommons.org/licenses/by-nc-nd/4.0
"""''',
        """# █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
# █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█
#
#              © Copyright 2022
#
#          https://t.me/hikariatama
#
# 🔒 Licensed under the GNU GPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html""",
    )

    if old_code == code:
        print(f"Not replaced in {mod.path}")
        continue

    print(f"Replaced in {mod.path}")

    with open(mod.path, "w") as f:
        f.write(code)
