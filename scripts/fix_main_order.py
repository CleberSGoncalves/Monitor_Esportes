import os

main_gui_path = r"e:\desenvolvimento\Monitor_Esportes\gui\main_gui.py"
with open(main_gui_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
main_idx = None
if_main_idx = None
for i, l in enumerate(lines):
    s = l.strip()
    if s == "def main() -> None:":
        main_idx = i
    elif s == 'if __name__ == "__main__":':
        if_main_idx = i

print(f"main_idx: {main_idx + 1 if main_idx else None}")
print(f"if_main_idx: {if_main_idx + 1 if if_main_idx else None}")

# Find where the patch after if __name__ starts:
# It starts right after main() call
patch_start_idx = None
for i in range(if_main_idx, len(lines)):
    if "CLEAN ROI PATCH" in lines[i]:
        patch_start_idx = i
        # backtrack a bit to catch comments
        while patch_start_idx > if_main_idx and (lines[patch_start_idx-1].strip().startswith("#") or lines[patch_start_idx-1].strip() == ""):
            patch_start_idx -= 1
        break

print(f"patch_start_idx: {patch_start_idx + 1 if patch_start_idx else None}")

if patch_start_idx:
    patch_lines = lines[patch_start_idx:]
    print(f"Number of patch lines to move: {len(patch_lines)}")
    before_main = lines[:main_idx]
    main_and_if_name = lines[main_idx:patch_start_idx]
    
    # Reassemble:
    # 1. before_main (all class definitions)
    # 2. patch_lines (all patches and methods added to MonitorApp)
    # 3. main_and_if_name (def main() and if __name__ == '__main__': main())
    new_lines = before_main + ["\n\n"] + patch_lines + ["\n\n"] + main_and_if_name
    
    with open(main_gui_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    
    print("SUCCESS: File reassembled correctly!")
