import os
import json
import logging

PROFILES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles.json")

DEFAULT_DATA = {
    "last_selected": None,
    "profiles": {}
}

def get_profiles_path():
    """Returns the absolute path to profiles.json."""
    return PROFILES_FILE

def ensure_profiles_file():
    """
    Ensures that profiles.json exists on disk.
    If not, creates it with DEFAULT_DATA.
    """
    if not os.path.exists(PROFILES_FILE):
        save_profiles_data(DEFAULT_DATA.copy())

def load_profiles_data():
    """
    Loads profiles from profiles.json safely.
    Ensures file is created on disk if it does not exist.
    Returns a dictionary with 'last_selected' and 'profiles'.
    """
    if not os.path.exists(PROFILES_FILE):
        ensure_profiles_file()
        return DEFAULT_DATA.copy()
    try:
        with open(PROFILES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                ensure_profiles_file()
                return DEFAULT_DATA.copy()
            if "profiles" not in data or not isinstance(data["profiles"], dict):
                data["profiles"] = {}
            if "last_selected" not in data:
                data["last_selected"] = None
            return data
    except Exception as e:
        logging.error(f"Error loading profiles.json: {e}")
        ensure_profiles_file()
        return DEFAULT_DATA.copy()

def save_profiles_data(data):
    """
    Saves profiles data dictionary to profiles.json.
    """
    try:
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"Error saving profiles.json: {e}")
        return False

def get_profile(name):
    """
    Retrieves a single profile by name.
    """
    if not name:
        return None
    data = load_profiles_data()
    return data.get("profiles", {}).get(name)

def get_last_selected_profile():
    """
    Returns (profile_name, profile_dict) of the last selected profile, or (None, None).
    """
    data = load_profiles_data()
    last = data.get("last_selected")
    if last and last in data.get("profiles", {}):
        return last, data["profiles"][last]
    # Fallback to the first profile if available
    profiles = data.get("profiles", {})
    if profiles:
        first_name = next(iter(profiles))
        return first_name, profiles[first_name]
    return None, None

def save_profile(name, repo_path, target_line, mode="unpushed", hashes=""):
    """
    Creates or updates a profile, sets it as last_selected, and persists.
    """
    name = (name or "").strip()
    if not name:
        return False, "Profile name cannot be empty."

    data = load_profiles_data()
    data["profiles"][name] = {
        "repo_path": repo_path or "",
        "target_line": target_line or "",
        "mode": mode or "unpushed",
        "hashes": hashes or ""
    }
    data["last_selected"] = name
    if save_profiles_data(data):
        return True, f"Profile '{name}' saved successfully."
    return False, "Failed to write profiles to file."

def set_last_selected(name):
    """
    Updates last_selected profile in JSON.
    """
    data = load_profiles_data()
    if name in data.get("profiles", {}) or name is None:
        data["last_selected"] = name
        save_profiles_data(data)
        return True
    return False

def delete_profile(name):
    """
    Deletes a profile by name from profiles.json.
    """
    data = load_profiles_data()
    if name in data.get("profiles", {}):
        del data["profiles"][name]
        if data.get("last_selected") == name:
            profiles = data.get("profiles", {})
            data["last_selected"] = next(iter(profiles)) if profiles else None
        save_profiles_data(data)
        return True, f"Profile '{name}' deleted."
    return False, f"Profile '{name}' not found."

def list_profiles():
    """
    Returns a list of profile names.
    """
    data = load_profiles_data()
    return list(data.get("profiles", {}).keys())
