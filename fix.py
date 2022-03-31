import os

for mod in os.scandir("."):
    if not mod.path.endswith(".py") or mod.path.endswith("fix.py"):
        continue

    with open(mod.path, "r") as f:
        code = f.read()

    FIX = """
    def get(self, *args) -> dict:
        return self._db.get(self.strings["name"], *args)

    def set(self, *args) -> None:
        return self._db.set(self.strings["name"], *args)
"""
    if FIX not in code:
        continue

    code = code.replace(FIX, "")

    # print(code)
    # input()

    with open(mod.path, "w") as f:
        f.write(code)

    print(f"Fixed {mod.path}")
