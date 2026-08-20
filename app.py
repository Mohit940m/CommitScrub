import os
import asyncio
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
    page.window.width = 820
    page.window.height = 800
    page.scroll = ft.ScrollMode.AUTO

    # UI Controls - Inputs
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
        expand=True,
        visible=False
    )

    def on_mode_change(e):
        hashes_input.visible = (mode_options.value == "specific")
        page.update()

    mode_options = ft.RadioGroup(
        content=ft.Column([
            ft.Radio(value="unpushed", label="Clean ALL Unpushed Local Commits"),
            ft.Radio(value="specific", label="Clean Specific Commit Hashes"),
            ft.Radio(value="head", label="Clean Latest Commit (HEAD) Only")
        ]), 
        value="unpushed",
        on_change=on_mode_change
    )

    # Progress & Status Controls
    loading_spinner = ft.ProgressRing(
        width=18,
        height=18,
        stroke_width=2.5,
        color=ft.Colors.BLUE_400,
        visible=False
    )

    status_text = ft.Text(
        value="Ready",
        size=13,
        weight=ft.FontWeight.W_500,
        color=ft.Colors.GREY_300
    )

    task_count_text = ft.Text(
        value="0 / 0 Tasks",
        size=13,
        weight=ft.FontWeight.W_500,
        color=ft.Colors.GREY_400
    )

    percentage_text = ft.Text(
        value="0%",
        size=13,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.BLUE_400
    )

    progress_bar = ft.ProgressBar(
        value=0.0,
        height=8,
        border_radius=4,
        color=ft.Colors.BLUE_400,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST
    )

    progress_card = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Row([
                    loading_spinner,
                    status_text,
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([
                    task_count_text,
                    percentage_text,
                ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            progress_bar,
        ], spacing=8),
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
        padding=14,
        border_radius=8,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        visible=False
    )

    log_output = ft.Text(
        value="Select repository directory to get started.", 
        color=ft.Colors.GREY_400, 
        selectable=True
    )

    async def select_folder(e):
        path = await file_picker.get_directory_path()
        if path:
            path_input.value = path
            log_output.value = f"Selected Repository: {path}"
            log_output.color = ft.Colors.GREEN_300
            page.update()

    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    run_button = ft.ElevatedButton(
        "Run Cleaner", 
        icon=ft.Icons.CLEANING_SERVICES, 
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.PRIMARY,
            color=ft.Colors.ON_PRIMARY,
        )
    )

    browse_button = ft.ElevatedButton(
        "Browse Path", 
        icon=ft.Icons.FOLDER_OPEN, 
        on_click=select_folder
    )

    async def process_cleaning(e):
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
            targets = await asyncio.to_thread(get_unpushed_commits, repo_path)
            if not targets:
                log_output.value = "[NOTICE] No unpushed commits found, or upstream tracking branch is missing."
                log_output.color = ft.Colors.ORANGE_400
                page.update()
                return
        elif mode == "head":
            head_hash, _ = await asyncio.to_thread(run_cmd, "git rev-parse HEAD", repo_path)
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

        total_tasks = len(targets)

        # Set UI to Running State
        run_button.disabled = True
        browse_button.disabled = True
        progress_card.visible = True
        loading_spinner.visible = True
        status_text.value = f"Starting cleanup of {total_tasks} commit(s)..."
        status_text.color = ft.Colors.GREY_200
        task_count_text.value = f"Task 0 of {total_tasks}"
        percentage_text.value = "0%"
        progress_bar.value = 0.0
        log_output.value = f"Processing {total_tasks} commit(s)...\n"
        log_output.color = ft.Colors.BLUE_200
        page.update()

        done_cnt, not_found_cnt, fail_cnt = 0, 0, 0
        logs = []

        try:
            for idx, c_hash in enumerate(targets, start=1):
                status_text.value = f"Processing commit {c_hash[:7]} ({idx}/{total_tasks})..."
                page.update()

                status, msg = await asyncio.to_thread(
                    remove_coauthor_from_commit, repo_path, c_hash, target_line
                )

                if status == "DONE":
                    done_cnt += 1
                    logs.append(f"[SUCCESS]   {msg}")
                elif status == "NOT_FOUND":
                    not_found_cnt += 1
                    logs.append(f"[NOT FOUND] {msg}")
                else:
                    fail_cnt += 1
                    logs.append(f"[FAILED]    {msg}")

                # Update progress per task
                progress = idx / total_tasks
                pct = int(progress * 100)
                progress_bar.value = progress
                percentage_text.value = f"{pct}%"
                task_count_text.value = f"Task {idx} of {total_tasks}"
                log_output.value = "\n".join(logs)
                page.update()

            # Final summary
            summary = (
                f"\n\n--- SUMMARY REPORT ---\n"
                f"Total Tasks: {total_tasks}\n"
                f"Done       : {done_cnt}\n"
                f"Not Found  : {not_found_cnt}\n"
                f"Failed     : {fail_cnt}"
            )

            log_output.value = "\n".join(logs) + summary
            log_output.color = ft.Colors.WHITE if fail_cnt == 0 else ft.Colors.ORANGE_200
            status_text.value = f"Finished! {done_cnt} scrubbed, {not_found_cnt} skipped, {fail_cnt} failed."
            status_text.color = ft.Colors.GREEN_400 if fail_cnt == 0 else ft.Colors.ORANGE_400

        except Exception as ex:
            logs.append(f"[EXCEPTION] An error occurred: {ex}")
            log_output.value = "\n".join(logs)
            log_output.color = ft.Colors.RED_400
            status_text.value = "Encountered an error during execution."
            status_text.color = ft.Colors.RED_400
        finally:
            loading_spinner.visible = False
            run_button.disabled = False
            browse_button.disabled = False
            page.update()

    run_button.on_click = process_cleaning

    # Layout Assembly
    page.add(
        ft.Column([
            ft.Text("CommitScrub", size=26, weight=ft.FontWeight.BOLD),
            ft.Text("Clean unwanted lines & co-authors from Git commit history", size=13, color=ft.Colors.GREY_400),
        ], spacing=2),
        ft.Row([
            path_input,
            browse_button
        ]),
        ft.Divider(),
        target_line_input,
        ft.Text("Select Target Scope:", weight=ft.FontWeight.W_600),
        mode_options,
        hashes_input,
        ft.Row([
            run_button,
        ]),
        progress_card,
        ft.Divider(),
        ft.Text("Execution Logs:", weight=ft.FontWeight.W_600),
        ft.Container(
            content=ft.Column([log_output], scroll=ft.ScrollMode.AUTO),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            padding=15,
            border_radius=8,
            height=220,
            expand=True
        )
    )

if __name__ == "__main__":
    ft.run(main)