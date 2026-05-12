with open('hrz_bote.py', 'r') as f:
    content = f.read()

# نقل fetch_crypto_news قبل cmd_news
# إيجاد الدالتين
import re

# استخراج دالة fetch_crypto_news
match = re.search(r'\n(def fetch_crypto_news.*?)(?=\nasync def |\ndef |\nif __name__)', content, re.DOTALL)
if match:
    func_text = match.group(0)
    # حذفها من مكانها
    content = content.replace(func_text, '\n')
    # إدراجها قبل cmd_news
    content = content.replace('\nasync def cmd_news(', func_text + '\nasync def cmd_news(')
    with open('hrz_bote.py', 'w') as f:
        f.write(content)
    print("✅ Done!")
else:
    print("❌ fetch_crypto_news not found")
