import ast
import os

BOT_FILE = "hrz_bote.py"

print("\n🔎 HRZ BOT CHECK\n")

# 1. Check file exists
if os.path.exists(BOT_FILE):
    print("✔ Bot file exists")
else:
    print("❌ Bot file missing")
    exit()

# 2. Syntax check
try:
    with open(BOT_FILE, "r", encoding="utf-8") as f:
        ast.parse(f.read())
    print("✔ Syntax OK")
except SyntaxError as e:
    print("❌ Syntax Error:")
    print(e)

# 3. JobQueue check
with open(BOT_FILE, "r", encoding="utf-8") as f:
    content = f.read()

if "job_queue.run_repeating" in content:
    print("✔ JobQueue detected")
else:
    print("⚠️ JobQueue missing")

# 4. Main check
if 'if __name__ == "__main__"' in content:
    print("✔ Main entry exists")
else:
    print("❌ Missing main entry")

print("\n🏁 DONE")
