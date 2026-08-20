# CommitScrub

**CommitScrub** is a desktop application built with Python and Flet that allows you to easily remove unwanted lines—such as accidental co-author tags, internal notes, or metadata—from your Git commit history without breaking your repository.

---

## 🚀 Features

- 📁 **External JSON Profiles & Auto-Loading**:
  - Save project paths, target scrub lines, and scope preferences into named profiles.
  - Automatically remembers and reloads the last selected profile on app launch—no need to re-enter configurations!
  - Profiles are saved in an external `profiles.json` file for easy backup and editing.
- 🎯 **Targeted Line Removal**: Remove any specific line or text pattern from commit messages.
- 🔍 **Flexible Target Scopes**:
  - **Clean ALL Unpushed Local Commits**: Automatically detects and scrubs all local commits that haven't been pushed to the remote tracking branch.
  - **Clean Specific Commit Hashes**: Target individual commit hashes (separated by space or comma).
  - **Clean Latest Commit (HEAD) Only**: Instantly scrub the message of your most recent commit.
- ⚡ **Safe & Automated**: Automates `git rebase` and `git commit --amend` safely with automatic rollback if a rebase encounters an unexpected error.
- 📊 **Real-time Progress & Indicators**: Live loading animation, progress bar, task counter (`Task X of Y`), and percentage indicators during execution.
- 🎨 **Modern Design UI**: Minimalist aesthetic with Montserrat typography, category-style scope cards, and soft lavender accents.
- 🌓 **Theme Toggle**: Default light mode with seamless one-click Dark Mode toggle.

---

## 🛠️ Prerequisites

Before using CommitScrub, ensure you have:

- **Python**: Version 3.8 or higher installed on your system.
- **Git**: Installed and available in your system `PATH`.

---

## 📥 Installation

1. Clone or download this repository:
   ```bash
   git clone https://github.com/your-username/CommitScrub.git
   cd CommitScrub
   ```

2. Install the required dependencies:
   ```bash
   pip install flet
   ```

---

## 🎮 How to Run & Use

### 1. Launch the Application
Run the main script using Python:
```bash
python app.py
```

### 2. Manage Configuration Profiles (Productivity Booster)
- **Select / Switch Profile**: Pick an existing profile from the dropdown; your repository path, target scrub line, and target scope will load instantly.
- **Save Profile**: Click **Save** to update the active profile with your current inputs.
- **Create New Profile**: Click **New** to name and save your current configuration as a new profile.
- **Auto-Loading**: The app marks your active profile in `profiles.json` and will automatically load it the next time you start CommitScrub!

### 3. Select Repository
Click **Browse Path** to select the local directory of the Git repository you want to clean.

### 4. Enter Target Line to Remove
Paste the exact line you wish to scrub from commit messages into the **Target Line to Remove** text box.

### 5. Choose Target Scope
Select one of the three available scope options:
- **Clean ALL Unpushed Local Commits**: Scrubs all commits between `@{u}` (upstream) and `HEAD`.
- **Clean Specific Commit Hashes**: Enter commit hashes (e.g. `7afc84a e2fa9ce`) into the text field.
- **Clean Latest Commit (HEAD) Only**: Scrubs only the latest commit.

### 6. Run Cleaner
Click **Run Cleaner**. Real-time progress and summary execution logs will display in the **Execution Logs** panel.

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

```
Copyright (c) 2026 CommitScrub
```
