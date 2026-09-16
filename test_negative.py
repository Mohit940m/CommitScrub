import os
import shutil
import tempfile
import subprocess
import json
import pytest

import git_cleaner as gc
import profile_manager as pm

@pytest.fixture
def temp_dir():
    td = tempfile.mkdtemp()
    yield td
    shutil.rmtree(td, ignore_errors=True)

@pytest.fixture
def temp_git_repo(temp_dir):
    """Creates a valid git repository with 3 commits for testing."""
    repo = os.path.join(temp_dir, "repo")
    os.makedirs(repo, exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=repo, check=True, capture_output=True)
    
    # Commit 1 (Root commit)
    file1 = os.path.join(repo, "file1.txt")
    with open(file1, "w", encoding="utf-8") as f:
        f.write("Line 1\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Root commit message\n\nCo-authored-by: Claude <claude@anthropic.com>"],
        cwd=repo, check=True, capture_output=True
    )

    # Commit 2 (Middle commit)
    file2 = os.path.join(repo, "file2.txt")
    with open(file2, "w", encoding="utf-8") as f:
        f.write("Line 2\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Middle commit message\n\nCo-authored-by: Claude <claude@anthropic.com>"],
        cwd=repo, check=True, capture_output=True
    )

    # Commit 3 (HEAD commit)
    file3 = os.path.join(repo, "file3.txt")
    with open(file3, "w", encoding="utf-8") as f:
        f.write("Line 3\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "HEAD commit message\n\nCo-authored-by: Claude <claude@anthropic.com>"],
        cwd=repo, check=True, capture_output=True
    )

    return repo


# =====================================================================
# 1. Negative Tests for check_repo_status
# =====================================================================

def test_check_repo_status_none_or_empty():
    ok, err = gc.check_repo_status(None)
    assert not ok
    assert "does not exist" in err

    ok, err = gc.check_repo_status("")
    assert not ok
    assert "does not exist" in err

def test_check_repo_status_nonexistent_directory():
    ok, err = gc.check_repo_status(r"C:\NonExistentDirectory_123456789")
    assert not ok
    assert "does not exist" in err

def test_check_repo_status_file_instead_of_directory(temp_dir):
    file_path = os.path.join(temp_dir, "regular_file.txt")
    with open(file_path, "w") as f:
        f.write("Hello")
    ok, err = gc.check_repo_status(file_path)
    assert not ok
    assert "not a directory" in err

def test_check_repo_status_non_git_directory(temp_dir):
    non_git_dir = os.path.join(temp_dir, "plain_folder")
    os.makedirs(non_git_dir, exist_ok=True)
    ok, err = gc.check_repo_status(non_git_dir)
    assert not ok
    assert "not a valid Git repository" in err

def test_check_repo_status_dirty_working_tree(temp_git_repo):
    # Modify an existing tracked file without committing
    dirty_file = os.path.join(temp_git_repo, "file1.txt")
    with open(dirty_file, "a") as f:
        f.write("Uncommitted change\n")

    ok, err = gc.check_repo_status(temp_git_repo)
    assert not ok
    assert "uncommitted changes" in err

def test_check_repo_status_clean_repo(temp_git_repo):
    ok, err = gc.check_repo_status(temp_git_repo)
    assert ok
    assert err is None


# =====================================================================
# 2. Negative Tests for remove_coauthor_from_commit
# =====================================================================

def test_remove_coauthor_empty_target_line(temp_git_repo):
    head_hash, _ = gc.run_cmd("git rev-parse HEAD", temp_git_repo)
    status, msg = gc.remove_coauthor_from_commit(temp_git_repo, head_hash, "")
    assert status == "FAILED"
    assert "cannot be empty" in msg

    status, msg = gc.remove_coauthor_from_commit(temp_git_repo, head_hash, "   ")
    assert status == "FAILED"
    assert "cannot be empty" in msg

def test_remove_coauthor_invalid_commit_hash(temp_git_repo):
    status, msg = gc.remove_coauthor_from_commit(
        temp_git_repo, "invalid_hash_abc123", "Co-authored-by: Claude"
    )
    assert status == "FAILED"
    assert "Invalid commit hash" in msg

def test_remove_coauthor_target_line_not_found(temp_git_repo):
    head_hash, _ = gc.run_cmd("git rev-parse HEAD", temp_git_repo)
    status, msg = gc.remove_coauthor_from_commit(
        temp_git_repo, head_hash, "Non-existent line in commit message"
    )
    assert status == "NOT_FOUND"
    assert "Target line not found" in msg

def test_remove_coauthor_head_commit_success(temp_git_repo):
    head_hash, _ = gc.run_cmd("git rev-parse HEAD", temp_git_repo)
    target = "Co-authored-by: Claude <claude@anthropic.com>"
    status, msg = gc.remove_coauthor_from_commit(temp_git_repo, head_hash, target)
    assert status == "DONE"
    assert "Successfully cleaned HEAD commit" in msg

    # Verify message is updated and line is gone
    new_msg, _ = gc.run_cmd("git log -1 --format=%B HEAD", temp_git_repo)
    assert target not in new_msg
    assert "HEAD commit message" in new_msg

def test_remove_coauthor_middle_commit_success(temp_git_repo):
    middle_hash, _ = gc.run_cmd("git rev-parse HEAD~1", temp_git_repo)
    target = "Co-authored-by: Claude <claude@anthropic.com>"
    status, msg = gc.remove_coauthor_from_commit(temp_git_repo, middle_hash, target)
    assert status == "DONE"
    assert "Successfully cleaned older commit" in msg

    # Verify message is updated and line is gone
    msg_check, _ = gc.run_cmd("git log -1 --format=%B HEAD~1", temp_git_repo)
    assert target not in msg_check
    assert "Middle commit message" in msg_check

def test_remove_coauthor_root_commit_success(temp_git_repo):
    root_hash, _ = gc.run_cmd("git rev-list --max-parents=0 HEAD", temp_git_repo)
    target = "Co-authored-by: Claude <claude@anthropic.com>"
    status, msg = gc.remove_coauthor_from_commit(temp_git_repo, root_hash, target)
    assert status == "DONE"
    assert "Successfully cleaned older commit" in msg

    # Verify line is gone from root commit
    new_root_hash, _ = gc.run_cmd("git rev-list --max-parents=0 HEAD", temp_git_repo)
    msg_check, _ = gc.run_cmd(f"git log -1 --format=%B {new_root_hash}", temp_git_repo)
    assert target not in msg_check
    assert "Root commit message" in msg_check

def test_remove_coauthor_only_target_line_fallback(temp_dir):
    """If the commit message contains ONLY the target line, it should not fail with empty message."""
    repo = os.path.join(temp_dir, "single_line_repo")
    os.makedirs(repo, exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=repo, check=True, capture_output=True)
    fpath = os.path.join(repo, "file.txt")
    with open(fpath, "w") as f:
        f.write("test")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    target = "Co-authored-by: Only Line <only@example.com>"
    subprocess.run(["git", "commit", "-m", target], cwd=repo, check=True, capture_output=True)

    head_hash, _ = gc.run_cmd("git rev-parse HEAD", repo)
    status, msg = gc.remove_coauthor_from_commit(repo, head_hash, target)
    assert status == "DONE"

    new_msg, _ = gc.run_cmd("git log -1 --format=%B HEAD", repo)
    assert "Commit message cleaned by CommitScrub" in new_msg


# =====================================================================
# 3. Negative Tests for Profile Manager
# =====================================================================

@pytest.fixture
def mock_profiles_file(monkeypatch, temp_dir):
    fake_file = os.path.join(temp_dir, "test_profiles.json")
    monkeypatch.setattr(pm, "PROFILES_FILE", fake_file)
    return fake_file

def test_profile_empty_name_rejected(mock_profiles_file):
    ok, msg = pm.save_profile("", "C:/repo", "Target line")
    assert not ok
    assert "cannot be empty" in msg

    ok, msg = pm.save_profile("   ", "C:/repo", "Target line")
    assert not ok
    assert "cannot be empty" in msg

def test_profile_invalid_mode_sanitization(mock_profiles_file):
    ok, msg = pm.save_profile("TestProf", "C:/repo", "Target line", mode="bogus_mode")
    assert ok
    prof = pm.get_profile("TestProf")
    assert prof["mode"] == "unpushed"

def test_profile_delete_nonexistent(mock_profiles_file):
    ok, msg = pm.delete_profile("Does_Not_Exist")
    assert not ok
    assert "not found" in msg

def test_profile_corrupted_json_recovery(mock_profiles_file):
    with open(mock_profiles_file, "w", encoding="utf-8") as f:
        f.write("{ invalid json corrupted content [[[")

    data = pm.load_profiles_data()
    assert isinstance(data, dict)
    assert "profiles" in data
    assert "last_selected" in data
    # Corrupted file should have triggered a .bak backup
    assert os.path.exists(mock_profiles_file + ".bak")

def test_profile_empty_file_recovery(mock_profiles_file):
    with open(mock_profiles_file, "w", encoding="utf-8") as f:
        f.write("   ")

    data = pm.load_profiles_data()
    assert isinstance(data, dict)
    assert data["profiles"] == {}
    assert data["last_selected"] is None

def test_profile_non_dict_recovery(mock_profiles_file):
    with open(mock_profiles_file, "w", encoding="utf-8") as f:
        json.dump(["not", "a", "dict"], f)

    data = pm.load_profiles_data()
    assert isinstance(data, dict)
    assert data["profiles"] == {}

def test_profile_malformed_profile_entries_cleaned(mock_profiles_file):
    with open(mock_profiles_file, "w", encoding="utf-8") as f:
        json.dump({
            "last_selected": "valid_one",
            "profiles": {
                "corrupted_one": "this is a string not a dict",
                "valid_one": {
                    "repo_path": "C:/path",
                    "target_line": "target",
                    "mode": "head",
                    "hashes": ""
                }
            }
        }, f)

    data = pm.load_profiles_data()
    assert "corrupted_one" not in data["profiles"]
    assert "valid_one" in data["profiles"]
    last_name, last_p = pm.get_last_selected_profile()
    assert last_name == "valid_one"
    assert last_p["mode"] == "head"


# =====================================================================
# 4. Tests for Option Selection Persistence & State Synchronization
# =====================================================================

def test_option_selection_persists_and_syncs_modes(mock_profiles_file):
    """
    Verifies that choosing each mode ('unpushed', 'specific', 'head')
    persists into the profile and loads back cleanly as last_selected.
    """
    for test_mode in ["unpushed", "specific", "head"]:
        p_name = f"Profile_{test_mode}"
        pm.save_profile(
            name=p_name,
            repo_path=f"C:/{test_mode}_repo",
            target_line="Co-authored-by: Test",
            mode=test_mode,
            hashes="abc1234" if test_mode == "specific" else ""
        )
        pm.set_last_selected(p_name)

        loaded_name, loaded_profile = pm.get_last_selected_profile()
        assert loaded_name == p_name
        assert loaded_profile["mode"] == test_mode
        assert loaded_profile["repo_path"] == f"C:/{test_mode}_repo"
