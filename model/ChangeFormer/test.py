with open("app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines[:85]):
    print(f"{i+1:02d}: {line}", end="")