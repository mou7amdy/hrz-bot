with open('hrz_bote.py', 'r') as f:
    lines = f.readlines()

main_line = next(i for i, l in enumerate(lines) if l.strip() == 'def main():')
cmd_line = next(i for i, l in enumerate(lines) if 'async def cmd_clearmemory' in l)
ifname_line = next(i for i, l in enumerate(lines) if l.startswith('if __name__'))

print(f"main={main_line+1} cmd={cmd_line+1} ifname={ifname_line+1}")

new_funcs = lines[cmd_line:ifname_line]
final = lines[:main_line] + new_funcs + lines[main_line:cmd_line] + lines[ifname_line:]

with open('hrz_bote.py', 'w') as f:
    f.writelines(final)
print("Done!")
