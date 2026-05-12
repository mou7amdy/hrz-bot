with open('hrz_bote.py', 'r') as f:
    lines = f.readlines()

def find(name):
    for i, l in enumerate(lines):
        if name in l:
            return i
    return None

def extract_func(start):
    """استخراج دالة كاملة من سطر البداية"""
    end = start + 1
    while end < len(lines):
        l = lines[end]
        if (l.startswith('def ') or l.startswith('async def ') or 
            l.startswith('if __name__') or l.startswith('class ')):
            break
        end += 1
    return lines[start:end], end

# استخراج الدوال بترتيبها الصحيح
targets = [
    'def ask_grok',
    'def ask_smart', 
    'def fetch_crypto_news',
    'async def cmd_clearmemory',
    'async def cmd_mylevel',
    'async def cmd_news',
    'async def cmd_marketing',
    'async def educational_post_v2',
]

extracted = {}
positions = {}
for t in targets:
    idx = find(t)
    if idx:
        func_lines, end = extract_func(idx)
        extracted[t] = func_lines
        positions[t] = (idx, end)

# حذف هذه الدوال من أماكنها الأصلية
remove_ranges = sorted(positions.values(), reverse=True)
new_lines = list(lines)
for start, end in remove_ranges:
    del new_lines[start:end]

# إيجاد موضع cmd_schedule للإدراج قبله
insert_at = find('async def cmd_schedule')
# إعادة الحساب بعد الحذف
insert_at = next(i for i, l in enumerate(new_lines) if 'async def cmd_schedule' in l)

# إدراج الدوال بالترتيب الصحيح
insert_block = []
for t in targets:
    if t in extracted:
        insert_block.extend(extracted[t])

new_lines = new_lines[:insert_at] + insert_block + new_lines[insert_at:]

with open('hrz_bote.py', 'w') as f:
    f.writelines(new_lines)
print("Done!")
