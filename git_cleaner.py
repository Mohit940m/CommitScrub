import sys
import subprocess
import os

def run_cmd(command, repo_path, env=None):
    try:
        result = subprocess.run(
            command,
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=True,
            env=env
        )
        if result.returncode != 0:
            return None, result.stderr.strip()
        return result.stdout.strip(), None
    except Exception as e:
        return None, str(e)

def check_repo_status(repo_path):
    """
    Validates that repo_path exists, is a valid git worktree,
    has no dirty uncommitted working tree changes, and has no rebase in progress.
    Returns (True, None) if clean and ready, or (False, error_message) if not.
    """
    if not repo_path or not os.path.exists(repo_path):
        return False, "Directory path does not exist."
    if not os.path.isdir(repo_path):
        return False, "Specified path is not a directory."

    # Check if it is a git repository
    is_git, err = run_cmd("git rev-parse --is-inside-work-tree", repo_path)
    if err or is_git != "true":
        return False, "Specified directory is not a valid Git repository."

    # Check if rebase is already in progress
    git_dir, _ = run_cmd("git rev-parse --git-dir", repo_path)
    if git_dir:
        rebase_merge = os.path.join(repo_path, git_dir, "rebase-merge")
        rebase_apply = os.path.join(repo_path, git_dir, "rebase-apply")
        if os.path.exists(rebase_merge) or os.path.exists(rebase_apply):
            return False, "A Git rebase is already in progress. Please resolve or abort it first."

    # Check for uncommitted working tree changes
    status_out, err = run_cmd("git status --porcelain", repo_path)
    if err is not None:
        return False, f"Could not check git status: {err}"
    if status_out and status_out.strip():
        return False, "Working tree has uncommitted changes. Please commit or stash them before running."

    return True, None

def remove_coauthor_from_commit(repo_path, commit_hash, target_line):
    if not target_line or not target_line.strip():
        return "FAILED", "Target line to remove cannot be empty."

    # Resolve full commit hash
    full_hash, err = run_cmd(f"git rev-parse {commit_hash}", repo_path)
    if err or not full_hash:
        return "FAILED", f"Invalid commit hash: '{commit_hash}'"

    # Fetch raw message directly from Git
    raw_msg, err = run_cmd(f'git log -1 --format="%B" {full_hash}', repo_path)
    if err or not raw_msg:
        return "FAILED", f"Could not read commit {commit_hash[:7]}: {err}"

    # Strict check: Skip if target line is not present
    if target_line not in raw_msg:
        return "NOT_FOUND", f"Target line not found in commit {full_hash[:7]}"

    cleaned_lines = [line for line in raw_msg.splitlines() if target_line not in line]
    cleaned_msg = "\n".join(cleaned_lines).strip()
    if not cleaned_msg:
        cleaned_msg = "Commit message cleaned by CommitScrub"

    head_hash, _ = run_cmd("git rev-parse HEAD", repo_path)

    # Temporary file for the cleaned commit message
    msg_file = os.path.abspath(os.path.join(repo_path, ".git_clean_msg_tmp.txt")).replace("\\", "/")
    seq_script = os.path.abspath(os.path.join(repo_path, ".git_seq_editor.py")).replace("\\", "/")
    editor_script = os.path.abspath(os.path.join(repo_path, ".git_msg_editor.py")).replace("\\", "/")

    with open(msg_file, "w", encoding="utf-8") as f:
        f.write(cleaned_msg)

    try:
        if head_hash == full_hash:
            # Amend HEAD
            _, err = run_cmd(f'git commit --amend -F "{msg_file}" --no-edit', repo_path)
            if err:
                return "FAILED", f"Failed amending HEAD ({commit_hash[:7]}): {err}"
            return "DONE", f"Successfully cleaned HEAD commit ({commit_hash[:7]})"
        else:
            # Check if commit has a parent or is root commit
            parent_hash, _ = run_cmd(f"git rev-parse --verify {full_hash}~1", repo_path)
            is_root = (parent_hash is None)
            rebase_target = "--root" if is_root else f"{full_hash}~1"

            # Create helper scripts with forward slashes for Windows safety
            with open(seq_script, "w", encoding="utf-8") as f:
                f.write(
                    f'import sys\n'
                    f'path = sys.argv[1]\n'
                    f'with open(path, "r", encoding="utf-8") as f: lines = f.readlines()\n'
                    f'new_lines = []\n'
                    f'for line in lines:\n'
                    f'    parts = line.split()\n'
                    f'    if len(parts) >= 2 and parts[0] == "pick" and "{full_hash}".startswith(parts[1]):\n'
                    f'        parts[0] = "reword"\n'
                    f'        new_lines.append(" ".join(parts) + "\\n")\n'
                    f'    else:\n'
                    f'        new_lines.append(line)\n'
                    f'with open(path, "w", encoding="utf-8") as f: f.writelines(new_lines)\n'
                )

            with open(editor_script, "w", encoding="utf-8") as f:
                f.write(
                    f'import sys\n'
                    f'target_file = r"{msg_file}"\n'
                    f'with open(target_file, "r", encoding="utf-8") as tf:\n'
                    f'    msg = tf.read()\n'
                    f'with open(sys.argv[1], "w", encoding="utf-8") as f:\n'
                    f'    f.write(msg)\n'
                )

            custom_env = os.environ.copy()
            custom_env["GIT_SEQUENCE_EDITOR"] = f'python "{seq_script}"'
            custom_env["GIT_EDITOR"] = f'python "{editor_script}"'

            _, err = run_cmd(f'git rebase -i {rebase_target}', repo_path, env=custom_env)

            if err and "Successfully rebased" not in err and err != "":
                run_cmd("git rebase --abort", repo_path)
                return "FAILED", f"Rebase failed for commit {commit_hash[:7]}: {err}"

            return "DONE", f"Successfully cleaned older commit ({commit_hash[:7]})"

    finally:
        for temp_p in [seq_script, editor_script, msg_file]:
            if os.path.exists(temp_p):
                try:
                    os.remove(temp_p)
                except Exception:
                    pass

def get_unpushed_commits(repo_path):
    """Returns list of unpushed local commit hashes."""
    unpushed_str, err = run_cmd('git log "@{u}..HEAD" --format="%H"', repo_path)
    if err or not unpushed_str:
        return []
    return unpushed_str.split()