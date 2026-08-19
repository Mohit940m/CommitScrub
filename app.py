import os
import flet as ft
from git_cleaner import (
    remove_coauthor_from_commit,
    get_unpushed_commits,
    run_cmd
)

def main(page: ft.Page):
    page.title = "CommitScrub"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 25
    page.window.width = 780
    page.window.height = 750

    # UI Controls
    path_input = ft.TextField(
        label="Repository Path", 
        expand=True, 
        read_only=True,
        hint_text="Select local git repository directory..."
    )
    
    target_line_input = ft.TextField(
        label="Target Line to Remove", 
        hint_text="Paste your message here to remove...", 
        expand=True,
        multiline=True,
        max_lines=2
    )
    
    hashes_input = ft.TextField(
        label="Commit Hashes (Space or Comma Separated)", 
        hint_text="e.g. 7afc84a e2fa9ce", 
        expand=True
    )

    mode_options = ft.RadioGroup(
        content=ft.Column([
            ft.Radio(value="unpushed", label="Clean ALL Unpushed Local Commits"),
            ft.Radio(value="specific", label="Clean Specific Commit Hashes"),
            ft.Radio(value="head", label="Clean Latest Commit (HEAD) Only")
        ]), 
        value="unpushed"
    )

    log_output = ft.Text(value="Select repository directory to get started.", color=ft.Colors.GREY_400, selectable=True)

    async def select_folder(e):
        path = await file_picker.get_directory_path()
        if path:
            path_input.value = path
            log_output.value = f"Selected Repository: {path}"
            log_output.color = ft.Colors.GREEN_300
            page.update()

    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    def process_cleaning(e):
        repo_path = path_input.value
        target_line = target_line_input.value.strip()
        mode = mode_options.value

        if not repo_path or not os.path.exists(repo_path):
            log_output.value = "[ERROR] Please select a valid Git repository directory."
            log_output.color = ft.Colors.RED_400
            page.update()
            return

        if not target_line:
            log_output.value = "[ERROR] Target line cannot be empty."
            log_output.color = ft.Colors.RED_400
            page.update()
            return

        targets = []
        if mode == "unpushed":
            targets = get_unpushed_commits(repo_path)
            if not targets:
                log_output.value = "[NOTICE] No unpushed commits found, or upstream tracking branch is missing."
                log_output.color = ft.Colors.ORANGE_400
                page.update()
                return
        elif mode == "head":
            head_hash, _ = run_cmd("git rev-parse HEAD", repo_path)
            if head_hash:
                targets = [head_hash]
        elif mode == "specific":
            raw = hashes_input.value.replace(",", " ").split()
            targets = [h.strip() for h in raw if h.strip()]

        if not targets:
            log_output.value = "[ERROR] No valid target commit hashes provided."
            log_output.color = ft.Colors.RED_400
            page.update()
            return

        log_output.value = f"Processing {len(targets)} commit(s)...\n"
        log_output.color = ft.Colors.BLUE_200
        page.update()

        done_cnt, not_found_cnt, fail_cnt = 0, 0, 0
        logs = []

        for c_hash in targets:
            status, msg = remove_coauthor_from_commit(repo_path, c_hash, target_line)
            if status == "DONE":
                done_cnt += 1
                logs.append(f"[SUCCESS]   {msg}")
            elif status == "NOT_FOUND":
                not_found_cnt += 1
                logs.append(f"[NOT FOUND] {msg}")
            else:
                fail_cnt += 1
                logs.append(f"[FAILED]    {msg}")

        summary = (
            f"\n\n--- SUMMARY REPORT ---\n"
            f"Processed : {len(targets)}\n"
            f"Done      : {done_cnt}\n"
            f"Not Found : {not_found_cnt}\n"
            f"Failed    : {fail_cnt}"
        )

        log_output.value = "\n".join(logs) + summary
        log_output.color = ft.Colors.WHITE
        page.update()

    # Layout Assembly
    page.add(
        ft.Text("CommitScrub", size=26, weight=ft.FontWeight.BOLD),
        ft.Row([
            path_input,
            ft.ElevatedButton(
                "Browse Path", 
                icon=ft.Icons.FOLDER_OPEN, 
                on_click=select_folder
            )
        ]),
        ft.Divider(),
        target_line_input,
        ft.Text("Select Target Scope:", weight=ft.FontWeight.W_600),
        mode_options,
        hashes_input,
        ft.ElevatedButton(
            "Run Cleaner", 
            icon=ft.Icons.CLEANING_SERVICES, 
            on_click=process_cleaning,
            style=ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY)
        ),
        ft.Divider(),
        ft.Text("Execution Logs:", weight=ft.FontWeight.W_600),
        ft.Container(
            content=log_output,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            padding=15,
            border_radius=8,
            expand=True
        )
    )

if __name__ == "__main__":
    ft.run(main)