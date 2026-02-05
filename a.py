#!/usr/bin/env python3
"""
gitit - Force push ALL files to GitHub (v5.0 - ABSOLUTE BULLETPROOF EDITION)

GUARANTEES:
- NEVER creates empty repos
- NEVER pushes with 0 files
- Verifies files EXIST in commit before push
- Fails hard if staging fails

Features:
- Removes ALL nested .git directories (prevents submodule issues)
- Removes Windows reserved filenames (nul, con, prn, aux, etc.)
- Removes git lock files before operations
- Uses Git LFS for files >100MB
- Multiple staging fallbacks
- HARD FAIL if 0 files staged
"""
import subprocess
import sys
import os
import time
import shutil
import re
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

# Configuration
GITHUB_FILE_LIMIT = 100 * 1024 * 1024  # 100 MB
GITHUB_USERNAME = "Michaelunkai"

# Windows reserved filenames (can't be used as regular files)
WINDOWS_RESERVED = {'con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 
                    'com5', 'com6', 'com7', 'com8', 'com9', 'lpt1', 'lpt2', 
                    'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'}


class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RED = "\033[91m"
    RESET = "\033[0m"


def run_cmd(cmd, cwd=None, capture=True, timeout=300):
    """Run command and return (success, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=capture, text=True,
            encoding='utf-8', errors='replace', cwd=cwd,
            env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'},
            timeout=timeout
        )
        return result.returncode == 0, result.stdout if capture else "", result.stderr if capture else ""
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def show_progress(step, total, message):
    """Show progress bar"""
    percent = int(100 * step / total)
    filled = int(40 * step / total)
    bar = "█" * filled + "░" * (40 - filled)
    print(f"\r{Colors.CYAN}[{bar}] {percent}% - {message}{Colors.RESET}", end="", flush=True)


def remove_nested_git_dirs(working_dir):
    """Remove ALL nested .git directories to prevent submodule issues"""
    count = 0
    for item in working_dir.rglob(".git"):
        if item.is_dir() and item.parent != working_dir:
            try:
                shutil.rmtree(item, ignore_errors=True)
                count += 1
            except:
                pass
    return count


def remove_windows_reserved_files(working_dir):
    """Remove files with Windows reserved names (nul, con, prn, etc.)"""
    count = 0
    for item in working_dir.rglob("*"):
        if item.is_file():
            name_lower = item.name.lower()
            base_name = name_lower.split('.')[0] if '.' in name_lower else name_lower
            if base_name in WINDOWS_RESERVED or name_lower in WINDOWS_RESERVED:
                try:
                    if sys.platform == "win32":
                        os.remove(f"\\\\?\\{item}")
                    else:
                        item.unlink()
                    count += 1
                except:
                    pass
    return count


def remove_git_locks(working_dir):
    """Remove any git lock files"""
    git_dir = working_dir / ".git"
    if git_dir.exists():
        for lock in git_dir.rglob("*.lock"):
            try:
                lock.unlink()
            except:
                pass
        index_lock = git_dir / "index.lock"
        if index_lock.exists():
            try:
                index_lock.unlink()
            except:
                pass


def count_local_files(directory):
    """Count all files in directory (excluding .git)"""
    count = 0
    for item in directory.rglob("*"):
        if ".git" in item.parts:
            continue
        if not item.is_file():
            continue
        name_lower = item.name.lower()
        base_name = name_lower.split('.')[0] if '.' in name_lower else name_lower
        if base_name in WINDOWS_RESERVED or name_lower in WINDOWS_RESERVED:
            continue
        count += 1
    return count


def get_all_files(directory):
    """Get all files excluding .git folder and reserved names"""
    files = []
    large_files = []
    
    for item in directory.rglob("*"):
        if ".git" in item.parts:
            continue
        if not item.is_file():
            continue
        
        name_lower = item.name.lower()
        base_name = name_lower.split('.')[0] if '.' in name_lower else name_lower
        if base_name in WINDOWS_RESERVED or name_lower in WINDOWS_RESERVED:
            continue
        
        try:
            size = item.stat().st_size
            rel_path = item.relative_to(directory)
            
            if size > GITHUB_FILE_LIMIT:
                large_files.append((str(rel_path), size))
            else:
                files.append((str(rel_path), size))
        except:
            pass
    
    return files, large_files


def setup_git_lfs(working_dir, large_files):
    """Setup Git LFS for large files"""
    if not large_files:
        return True
    
    ok, _, _ = run_cmd('git lfs install --local', working_dir)
    if not ok:
        return False
    
    extensions = set()
    for rel_path, _ in large_files:
        ext = Path(rel_path).suffix.lower()
        git_path = rel_path.replace("\\", "/")
        if ext:
            extensions.add(f"*{ext}")
        run_cmd(f'git lfs track "{git_path}"', working_dir)
    
    for ext in extensions:
        run_cmd(f'git lfs track "{ext}"', working_dir)
    
    return True


def is_already_synced(working_dir, repo_name):
    """Check if repo was recently pushed to GitHub (skip if no local changes)"""
    git_dir = working_dir / ".git"
    
    if git_dir.exists():
        ok, remote_out, _ = run_cmd('git remote get-url origin', working_dir)
        if ok and remote_out.strip():
            ok, status_out, _ = run_cmd('git status --porcelain', working_dir)
            if ok and not status_out.strip():
                ok, ahead, _ = run_cmd('git rev-list --count origin/main..HEAD 2>nul', working_dir)
                if ok and ahead.strip() == '0':
                    return True, "Already synced (no local changes)"
    
    return False, "Has changes or not synced"


def main():
    if len(sys.argv) < 2:
        print("Usage: gitit <folder_path>")
        sys.exit(1)

    working_dir = Path(sys.argv[1]).resolve()
    if not working_dir.exists():
        print(f"Error: {working_dir} does not exist")
        sys.exit(1)

    print(f"\n{Colors.CYAN}Processing: {working_dir}{Colors.RESET}\n")

    # Calculate repo name early
    repo_name = working_dir.name.replace(" ", "-").lower()
    repo_name = re.sub(r'[^a-z0-9\-_]', '', repo_name)
    repo_name = repo_name[:100] if len(repo_name) > 100 else repo_name
    
    if not repo_name:
        repo_name = "unnamed-repo"
    
    # =========================================
    # CRITICAL CHECK: Count local files FIRST
    # =========================================
    local_file_count = count_local_files(working_dir)
    print(f"{Colors.CYAN}📁 Local files found: {local_file_count}{Colors.RESET}")
    
    if local_file_count == 0:
        print(f"\n{Colors.RED}✗ ABORT: No files to push! Directory is empty.{Colors.RESET}")
        print(f"{Colors.YELLOW}Skipping: {repo_name}{Colors.RESET}")
        sys.exit(1)

    # Quick sync check
    synced, reason = is_already_synced(working_dir, repo_name)
    if synced:
        print(f"{Colors.GREEN}✓ SKIPPED: {repo_name} - {reason}{Colors.RESET}")
        print(f"{Colors.YELLOW}→ https://github.com/{GITHUB_USERNAME}/{repo_name}{Colors.RESET}")
        return

    start_time = time.time()
    total_steps = 12
    step = 0

    # =========================================
    # STEP 1: Remove Windows reserved files
    # =========================================
    step += 1
    show_progress(step, total_steps, "Removing Windows reserved files")
    reserved_count = remove_windows_reserved_files(working_dir)

    # =========================================
    # STEP 2: Remove nested .git directories
    # =========================================
    step += 1
    show_progress(step, total_steps, "Removing nested .git directories")
    nested_count = remove_nested_git_dirs(working_dir)

    # =========================================
    # STEP 3: Clean git environment
    # =========================================
    step += 1
    show_progress(step, total_steps, "Preparing git environment")
    git_dir = working_dir / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir, ignore_errors=True)

    # =========================================
    # STEP 4: Initialize fresh git repo
    # =========================================
    step += 1
    show_progress(step, total_steps, "Initializing fresh git repo")
    run_cmd(f'git init -b main "{working_dir}"')
    run_cmd(f'git config user.name "{GITHUB_USERNAME}"', working_dir)
    run_cmd(f'git config user.email "{GITHUB_USERNAME}@users.noreply.github.com"', working_dir)
    run_cmd('git config core.autocrlf false', working_dir)
    run_cmd('git config http.postBuffer 524288000', working_dir)
    run_cmd(f'git config --global --add safe.directory "{working_dir}"')

    # =========================================
    # STEP 5: Scan for files
    # =========================================
    step += 1
    show_progress(step, total_steps, "Scanning files")
    files, large_files = get_all_files(working_dir)
    total_files = len(files) + len(large_files)
    print(f" ({total_files} files)", end="", flush=True)

    # =========================================
    # STEP 6: Handle large files with Git LFS
    # =========================================
    step += 1
    show_progress(step, total_steps, "Processing large files")
    if large_files:
        print(f"\n{Colors.CYAN}📦 {len(large_files)} files exceed 100MB - using Git LFS{Colors.RESET}")
        setup_git_lfs(working_dir, large_files)

    # =========================================
    # STEP 7: Setup repository name
    # =========================================
    step += 1
    show_progress(step, total_steps, "Setting up repository")
    remote_url = f"https://github.com/{GITHUB_USERNAME}/{repo_name}.git"

    # =========================================
    # STEP 8: Stage all files (CRITICAL - VERIFY SUCCESS)
    # =========================================
    step += 1
    show_progress(step, total_steps, "Staging files")
    
    remove_git_locks(working_dir)
    
    # Try staging with multiple methods
    staged_files = []
    staging_methods = [
        'git add -A',
        'git add .',
        'git add --all',
        'git add -A --force',
    ]
    
    for add_cmd in staging_methods:
        remove_git_locks(working_dir)
        run_cmd(add_cmd, working_dir, timeout=600)
        
        ok, staged_output, _ = run_cmd("git diff --cached --name-only", working_dir)
        staged_files = [f for f in staged_output.strip().split('\n') if f.strip()]
        
        if staged_files:
            print(f" ({len(staged_files)} files staged with {add_cmd})", end="", flush=True)
            break
    
    # =========================================
    # CRITICAL VERIFICATION: Files must be staged
    # =========================================
    if len(staged_files) == 0:
        print(f"\n{Colors.RED}✗ CRITICAL FAILURE: 0 files staged out of {total_files}!{Colors.RESET}")
        print(f"{Colors.RED}ABORTING to prevent empty repo creation.{Colors.RESET}")
        
        # Debug info
        print(f"\n{Colors.YELLOW}Debug info:{Colors.RESET}")
        ok, status, _ = run_cmd("git status", working_dir)
        print(f"Git status:\n{status[:500]}")
        
        # Cleanup failed git init
        if git_dir.exists():
            shutil.rmtree(git_dir, ignore_errors=True)
        
        sys.exit(1)
    
    # Verify we staged at least 50% of files (sanity check)
    if len(staged_files) < total_files * 0.5 and total_files > 10:
        print(f"\n{Colors.YELLOW}⚠ WARNING: Only {len(staged_files)}/{total_files} files staged!{Colors.RESET}")

    # =========================================
    # STEP 9: Create commit (NO --allow-empty!)
    # =========================================
    step += 1
    show_progress(step, total_steps, "Creating commit")
    
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"Auto commit {timestamp} - {len(staged_files)} files"
    
    ok, _, commit_err = run_cmd(f'git commit -m "{commit_msg}"', working_dir)
    if not ok:
        print(f"\n{Colors.RED}✗ COMMIT FAILED: {commit_err}{Colors.RESET}")
        print(f"{Colors.RED}ABORTING to prevent empty repo.{Colors.RESET}")
        if git_dir.exists():
            shutil.rmtree(git_dir, ignore_errors=True)
        sys.exit(1)
    
    # =========================================
    # VERIFY: Commit contains files
    # =========================================
    ok, commit_files, _ = run_cmd("git log --stat --oneline -1", working_dir)
    if "files changed" not in commit_files.lower() and len(staged_files) > 0:
        # Additional check
        ok, tree_files, _ = run_cmd("git ls-tree --name-only -r HEAD", working_dir)
        committed_files = [f for f in tree_files.strip().split('\n') if f.strip()]
        
        if len(committed_files) == 0:
            print(f"\n{Colors.RED}✗ COMMIT VERIFICATION FAILED: No files in commit!{Colors.RESET}")
            print(f"{Colors.RED}ABORTING.{Colors.RESET}")
            if git_dir.exists():
                shutil.rmtree(git_dir, ignore_errors=True)
            sys.exit(1)
        
        print(f" ({len(committed_files)} files in commit)", end="", flush=True)

    # =========================================
    # STEP 10: Setup GitHub remote
    # =========================================
    step += 1
    show_progress(step, total_steps, "Configuring GitHub")
    
    run_cmd("git remote remove origin", working_dir)
    run_cmd(f"git remote add origin {remote_url}", working_dir)
    run_cmd("git branch -M main", working_dir)
    
    ok, _, _ = run_cmd(f"gh repo view {GITHUB_USERNAME}/{repo_name}")
    if not ok:
        run_cmd(f"gh repo create {GITHUB_USERNAME}/{repo_name} --public")
        print(f" (created new repo)", end="", flush=True)
        time.sleep(1)

    # =========================================
    # STEP 11: Push to GitHub
    # =========================================
    step += 1
    show_progress(step, total_steps, "Pushing to GitHub")
    
    push_ok = False
    for attempt in range(5):
        print(f" (attempt {attempt + 1})", end="", flush=True)
        
        ok, _, err = run_cmd("git push --set-upstream origin main --force", working_dir, timeout=600)
        if ok:
            push_ok = True
            break
        
        if "large file" in err.lower() or "lfs" in err.lower():
            run_cmd("git lfs push --all origin main", working_dir, timeout=300)
        
        time.sleep(2 * (attempt + 1))

    # =========================================
    # STEP 12: Final verification
    # =========================================
    step += 1
    show_progress(step, total_steps, "Verifying")

    elapsed = time.time() - start_time
    
    print("\n")
    print(f"{Colors.CYAN}=================================================={Colors.RESET}")
    print(f"{Colors.CYAN}SUMMARY{Colors.RESET}")
    print(f"{Colors.CYAN}=================================================={Colors.RESET}")
    print(f"Local files:      {total_files}")
    print(f"Files staged:     {len(staged_files)}")
    print(f"Large files:      {len(large_files)} (LFS)")
    print(f"Push success:     {'✓ Yes' if push_ok else '✗ No'}")
    print(f"Time elapsed:     {elapsed:.1f}s")
    print(f"{Colors.CYAN}=================================================={Colors.RESET}")
    
    if push_ok:
        print(f"\n{Colors.GREEN}✓ SUCCESS: {repo_name} ({len(staged_files)} files pushed){Colors.RESET}")
        print(f"{Colors.YELLOW}→ https://github.com/{GITHUB_USERNAME}/{repo_name}{Colors.RESET}")
    else:
        print(f"\n{Colors.RED}✗ PUSH FAILED: {repo_name}{Colors.RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
