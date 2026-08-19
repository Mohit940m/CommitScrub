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

def remove_coauthor_from_commit(repo_path, commit_hash, target_line):
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

    head_hash, _ = run_cmd("git rev-parse HEAD", repo_path)

    # Temporary file for the cleaned commit message
    msg_file = os.path.abspath(os.path.join(repo_path, ".git_clean_msg_tmp.txt")).replace("\\", "/")
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
            # Create helper scripts with forward slashes for Windows safety
            seq_script = os.path.abspath(os.path.join(repo_path, ".git_seq_editor.py")).replace("\\", "/")
            editor_script = os.path.abspath(os.path.join(repo_path, ".git_msg_editor.py")).replace("\\", "/")

            with open(seq_script, "w", encoding="utf-8") as f:
                f.write(
                    f'import sys\n'
                    f'path = sys.argv[1]\n'
                    f'with open(path, "r", encoding="utf-8") as f: content = f.read()\n'
                    f'content = content.replace("pick {full_hash[:7]}", "reword {full_hash[:7]}")\n'
                    f'with open(path, "w", encoding="utf-8") as f: f.write(content)\n'
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

            _, err = run_cmd(f'git rebase -i {full_hash}~1', repo_path, env=custom_env)

            # Cleanup helper scripts
            for temp_p in [seq_script, editor_script]:
                if os.path.exists(temp_p):
                    os.remove(temp_p)

            if err and "Successfully rebased" not in err and err != "":
                run_cmd("git rebase --abort", repo_path)
                return "FAILED", f"Rebase failed for commit {commit_hash[:7]}: {err}"

            return "DONE", f"Successfully cleaned older commit ({commit_hash[:7]})"

    finally:
        if os.path.exists(msg_file):
            os.remove(msg_file)

def get_unpushed_commits(repo_path):
    """Returns list of unpushed local commit hashes."""
    unpushed_str, err = run_cmd('git log "@{u}..HEAD" --format="%H"', repo_path)
    if err or not unpushed_str:
        return []
    return unpushed_str.split()