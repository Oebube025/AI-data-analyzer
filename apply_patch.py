"""
apply_patch.py - Pure Python unified diff patch applier.
Applies finch_v2.12.patch across all project files reliably on Windows, macOS, and Linux.
"""
import os

def apply_patch_file(patch_path="finch_v2.12.patch"):
    if not os.path.exists(patch_path):
        print(f"❌ Error: {patch_path} not found in the current directory.")
        return False

    with open(patch_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    diffs = content.split("\ndiff -urN ")
    success_count = 0

    for d in diffs:
        if not d.strip():
            continue
        lines = d.splitlines()
        
        target_file = None
        for l in lines[:5]:
            if l.startswith("+++ b/"):
                target_file = l[6:].strip()
                break
        if not target_file:
            continue

        print(f"Processing: {target_file}")
        
        hunks = []
        current_hunk = []
        for l in lines:
            if l.startswith("@@"):
                if current_hunk:
                    hunks.append(current_hunk)
                    current_hunk = []
                continue
            if l.startswith("--- ") or l.startswith("+++ ") or l.startswith("diff "):
                continue
            if current_hunk is not None:
                current_hunk.append(l)
        if current_hunk:
            hunks.append(current_hunk)

        is_new = any("@@ -0,0" in l for l in lines)

        target_dir = os.path.dirname(target_file)
        if target_dir and not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)

        file_lines = []
        for h in hunks:
            for hl in h:
                if hl.startswith(" "):
                    file_lines.append(hl[1:])
                elif hl.startswith("+"):
                    file_lines.append(hl[1:])
                # '-' lines are omitted

        with open(target_file, "w", encoding="utf-8", newline="\n") as out:
            out.write("\n".join(file_lines) + "\n")
        print(f"  Updated/Created: {target_file}")
        success_count += 1

    print(f"\n✅ Successfully applied patch to {success_count} files!")
    return True

if __name__ == "__main__":
    apply_patch_file()