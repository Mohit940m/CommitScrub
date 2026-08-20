import os
import asyncio
import flet as ft
from git_cleaner import (
    remove_coauthor_from_commit,
    get_unpushed_commits,
    run_cmd
)

# Design palette inspired by design/8727651.jpg
THEMES = {
    "light": {
        "theme_mode": ft.ThemeMode.LIGHT,
        "bg": "#F8F9FD",
        "surface": "#FFFFFF",
        "surface_tint": "#F4EEFD",
        "primary": "#A27BFC",
        "primary_light": "#BFA5FC",
        "dark_button": "#1E1E2E",
        "dark_button_text": "#FFFFFF",
        "border": "#E4E6F0",
        "border_selected": "#A27BFC",
        "text_primary": "#1A1B27",
        "text_muted": "#71758A",
        "log_bg": "#F3F5FA",
        "log_text": "#2D3142",
        "progress_track": "#EFE8FD",
        "progress_fill": "#A27BFC",
        "card_bg": "#FFFFFF",
        "card_border": "#E4E6F0",
        "toggle_bg": "#FFFFFF",
        "toggle_text": "#1A1B27",
        "toggle_icon": ft.Icons.DARK_MODE_ROUNDED,
        "toggle_label": "Dark Mode",
    },
    "dark": {
        "theme_mode": ft.ThemeMode.DARK,
        "bg": "#0F1016",
        "surface": "#181924",
        "surface_tint": "#26233B",
        "primary": "#B497FF",
        "primary_light": "#C9B3FF",
        "dark_button": "#2A2D40",
        "dark_button_text": "#FFFFFF",
        "border": "#2B2D3F",
        "border_selected": "#B497FF",
        "text_primary": "#F4F5FA",
        "text_muted": "#9CA3AF",
        "log_bg": "#13141C",
        "log_text": "#E2E4F0",
        "progress_track": "#28253D",
        "progress_fill": "#B497FF",
        "card_bg": "#181924",
        "card_border": "#2B2D3F",
        "toggle_bg": "#1E1F2D",
        "toggle_text": "#F4F5FA",
        "toggle_icon": ft.Icons.LIGHT_MODE_ROUNDED,
        "toggle_label": "Light Mode",
    }
}

def main(page: ft.Page):
    page.title = "CommitScrub"
    page.fonts = {
        "Montserrat": "https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf"
    }
    page.theme = ft.Theme(font_family="Montserrat")
    page.dark_theme = ft.Theme(font_family="Montserrat")
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 24
    page.window.width = 860
    page.window.height = 880
    page.scroll = ft.ScrollMode.AUTO

    # Current state
    state = {
        "theme": "light",
        "mode": "unpushed"
    }

    t = THEMES[state["theme"]]
    page.bgcolor = t["bg"]

    # File Picker
    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    # ------------------ Header Controls ------------------
    app_icon = ft.Container(
        content=ft.Icon(ft.Icons.AUTO_FIX_HIGH_ROUNDED, color=t["primary"], size=22),
        bgcolor=t["surface_tint"],
        padding=10,
        border_radius=12,
    )

    app_title = ft.Text("CommitScrub", size=22, weight=ft.FontWeight.BOLD, color=t["text_primary"])
    app_subtitle = ft.Text("Clean unwanted lines & co-authors from Git commit history", size=12, color=t["text_muted"])

    theme_icon = ft.Icon(t["toggle_icon"], size=16, color=t["primary"])
    theme_text = ft.Text(t["toggle_label"], size=12, weight=ft.FontWeight.W_600, color=t["toggle_text"])

    theme_toggle_btn = ft.Container(
        content=ft.Row([theme_icon, theme_text], spacing=6, alignment=ft.MainAxisAlignment.CENTER),
        padding=ft.Padding(12, 8, 14, 8),
        border_radius=20,
        border=ft.Border.all(1, t["border"]),
        bgcolor=t["toggle_bg"],
        ink=True,
        tooltip="Toggle Light / Dark Mode"
    )

    header_row = ft.Row([
        ft.Row([
            app_icon,
            ft.Column([app_title, app_subtitle], spacing=1)
        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        theme_toggle_btn
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    # ------------------ Form Section Titles ------------------
    def create_section_title(text):
        return ft.Text(text, size=13, weight=ft.FontWeight.BOLD, color=t["text_primary"])

    lbl_repo = create_section_title("Repository Path")
    lbl_target = create_section_title("Target Line to Remove")
    lbl_scope = create_section_title("Target Scope")
    lbl_logs = create_section_title("Execution Logs")

    # ------------------ Input Controls ------------------
    path_input = ft.TextField(
        hint_text="Select local git repository directory...",
        expand=True,
        read_only=True,
        border_radius=12,
        border_color=t["border"],
        focused_border_color=t["primary"],
        bgcolor=t["surface"],
        color=t["text_primary"],
        prefix_icon=ft.Icons.FOLDER_OUTLINED,
        height=48
    )

    browse_button = ft.ElevatedButton(
        "Browse Path",
        icon=ft.Icons.FOLDER_OPEN_ROUNDED,
        height=48,
        style=ft.ButtonStyle(
            bgcolor=t["dark_button"],
            color=t["dark_button_text"],
            shape=ft.RoundedRectangleBorder(radius=12),
        )
    )

    target_line_input = ft.TextField(
        hint_text="e.g. Co-authored-by: Name <name@example.com>",
        expand=True,
        multiline=True,
        max_lines=2,
        border_radius=12,
        border_color=t["border"],
        focused_border_color=t["primary"],
        bgcolor=t["surface"],
        color=t["text_primary"],
        prefix_icon=ft.Icons.SUBDIRECTORY_ARROW_RIGHT_ROUNDED,
    )

    hashes_input = ft.TextField(
        label="Target Commit Hashes (Space or Comma Separated)",
        hint_text="e.g. 7afc84a e2fa9ce 3d1a88b",
        expand=True,
        border_radius=12,
        border_color=t["border"],
        focused_border_color=t["primary"],
        bgcolor=t["surface"],
        color=t["text_primary"],
        prefix_icon=ft.Icons.TAG_ROUNDED,
        visible=False,
        height=52
    )

    # ------------------ Scope Category Cards (Mockup Style) ------------------
    scope_cards_data = [
        {
            "id": "unpushed",
            "title": "Unpushed Commits",
            "subtitle": "Clean local @{u}..HEAD",
            "icon": ft.Icons.CLOUD_UPLOAD_ROUNDED,
        },
        {
            "id": "specific",
            "title": "Specific Hashes",
            "subtitle": "Target chosen commits",
            "icon": ft.Icons.TAG_ROUNDED,
        },
        {
            "id": "head",
            "title": "Latest (HEAD)",
            "subtitle": "Amend only HEAD commit",
            "icon": ft.Icons.COMMIT_ROUNDED,
        },
    ]

    scope_card_widgets = {}

    def build_scope_card(item):
        is_selected = (state["mode"] == item["id"])
        cur_t = THEMES[state["theme"]]

        bg = cur_t["surface_tint"] if is_selected else cur_t["surface"]
        b_color = cur_t["border_selected"] if is_selected else cur_t["border"]
        b_width = 2 if is_selected else 1
        icon_c = cur_t["primary"] if is_selected else cur_t["text_muted"]

        icon_ctrl = ft.Icon(item["icon"], color=icon_c, size=24)
        title_ctrl = ft.Text(item["title"], size=13, weight=ft.FontWeight.BOLD, color=cur_t["text_primary"])
        sub_ctrl = ft.Text(item["subtitle"], size=11, color=cur_t["text_muted"])

        container = ft.Container(
            content=ft.Column([
                ft.Row([
                    icon_ctrl,
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE_ROUNDED if is_selected else ft.Icons.RADIO_BUTTON_UNCHECKED_ROUNDED,
                        color=cur_t["primary"] if is_selected else cur_t["border"],
                        size=18
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(height=6),
                title_ctrl,
                sub_ctrl,
            ], spacing=2),
            bgcolor=bg,
            border=ft.Border.all(b_width, b_color),
            border_radius=14,
            padding=14,
            expand=True,
            ink=True,
            on_click=lambda e, m=item["id"]: on_select_scope(m)
        )
        return container

    def update_scope_cards():
        for item in scope_cards_data:
            m_id = item["id"]
            is_selected = (state["mode"] == m_id)
            cur_t = THEMES[state["theme"]]
            card = scope_card_widgets[m_id]

            card.bgcolor = cur_t["surface_tint"] if is_selected else cur_t["surface"]
            card.border = ft.Border.all(2 if is_selected else 1, cur_t["border_selected"] if is_selected else cur_t["border"])

            col = card.content
            # icon row
            col.controls[0].controls[0].color = cur_t["primary"] if is_selected else cur_t["text_muted"]
            col.controls[0].controls[1].name = ft.Icons.CHECK_CIRCLE_ROUNDED if is_selected else ft.Icons.RADIO_BUTTON_UNCHECKED_ROUNDED
            col.controls[0].controls[1].color = cur_t["primary"] if is_selected else cur_t["border"]
            # title & subtitle
            col.controls[2].color = cur_t["text_primary"]
            col.controls[3].color = cur_t["text_muted"]

    def on_select_scope(m_id):
        state["mode"] = m_id
        hashes_input.visible = (m_id == "specific")
        update_scope_cards()
        page.update()

    for item in scope_cards_data:
        scope_card_widgets[item["id"]] = build_scope_card(item)

    scope_cards_row = ft.Row([
        scope_card_widgets["unpushed"],
        scope_card_widgets["specific"],
        scope_card_widgets["head"],
    ], spacing=12)

    # ------------------ Action Button ------------------
    run_button = ft.ElevatedButton(
        "Run Cleaner",
        icon=ft.Icons.CLEANING_SERVICES_ROUNDED,
        height=50,
        style=ft.ButtonStyle(
            bgcolor=t["primary"],
            color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=12),
        )
    )

    # ------------------ Progress & Loading Section ------------------
    loading_spinner = ft.ProgressRing(
        width=18,
        height=18,
        stroke_width=2.6,
        color=t["primary"],
        visible=False
    )

    status_text = ft.Text(
        value="Ready to clean",
        size=13,
        weight=ft.FontWeight.W_500,
        color=t["text_primary"]
    )

    task_count_text = ft.Text(
        value="0 / 0 Tasks",
        size=13,
        weight=ft.FontWeight.W_500,
        color=t["text_muted"]
    )

    percentage_text = ft.Text(
        value="0%",
        size=13,
        weight=ft.FontWeight.BOLD,
        color=t["primary"]
    )

    progress_bar = ft.ProgressBar(
        value=0.0,
        height=9,
        border_radius=5,
        color=t["progress_fill"],
        bgcolor=t["progress_track"]
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
        ], spacing=10),
        bgcolor=t["surface_tint"],
        padding=16,
        border_radius=14,
        border=ft.Border.all(1, t["border_selected"]),
        visible=False
    )

    # ------------------ Execution Logs Section ------------------
    log_output = ft.Text(
        value="Select a repository directory and target line to get started.",
        color=t["text_muted"],
        selectable=True,
        size=12,
        font_family="monospace"
    )

    log_container = ft.Container(
        content=ft.Column([log_output], scroll=ft.ScrollMode.AUTO),
        bgcolor=t["log_bg"],
        padding=16,
        border_radius=14,
        border=ft.Border.all(1, t["border"]),
        height=220,
        expand=True
    )

    # ------------------ Theme Management ------------------
    def apply_theme():
        cur_t = THEMES[state["theme"]]
        page.theme_mode = cur_t["theme_mode"]
        page.bgcolor = cur_t["bg"]

        # Header
        app_icon.bgcolor = cur_t["surface_tint"]
        app_icon.content.color = cur_t["primary"]
        app_title.color = cur_t["text_primary"]
        app_subtitle.color = cur_t["text_muted"]

        theme_icon.name = cur_t["toggle_icon"]
        theme_icon.color = cur_t["primary"]
        theme_text.value = cur_t["toggle_label"]
        theme_text.color = cur_t["toggle_text"]
        theme_toggle_btn.bgcolor = cur_t["toggle_bg"]
        theme_toggle_btn.border = ft.Border.all(1, cur_t["border"])

        # Section Labels
        lbl_repo.color = cur_t["text_primary"]
        lbl_target.color = cur_t["text_primary"]
        lbl_scope.color = cur_t["text_primary"]
        lbl_logs.color = cur_t["text_primary"]

        # Inputs
        path_input.bgcolor = cur_t["surface"]
        path_input.border_color = cur_t["border"]
        path_input.focused_border_color = cur_t["primary"]
        path_input.color = cur_t["text_primary"]

        target_line_input.bgcolor = cur_t["surface"]
        target_line_input.border_color = cur_t["border"]
        target_line_input.focused_border_color = cur_t["primary"]
        target_line_input.color = cur_t["text_primary"]

        hashes_input.bgcolor = cur_t["surface"]
        hashes_input.border_color = cur_t["border"]
        hashes_input.focused_border_color = cur_t["primary"]
        hashes_input.color = cur_t["text_primary"]

        # Buttons
        browse_button.style.bgcolor = cur_t["dark_button"]
        browse_button.style.color = cur_t["dark_button_text"]
        run_button.style.bgcolor = cur_t["primary"]

        # Scope cards
        update_scope_cards()

        # Progress Card
        progress_card.bgcolor = cur_t["surface_tint"]
        progress_card.border = ft.Border.all(1, cur_t["border_selected"])
        loading_spinner.color = cur_t["primary"]
        status_text.color = cur_t["text_primary"]
        task_count_text.color = cur_t["text_muted"]
        percentage_text.color = cur_t["primary"]
        progress_bar.bgcolor = cur_t["progress_track"]
        progress_bar.color = cur_t["progress_fill"]

        # Logs
        log_container.bgcolor = cur_t["log_bg"]
        log_container.border = ft.Border.all(1, cur_t["border"])
        log_output.color = cur_t["log_text"]

    def toggle_theme(e):
        state["theme"] = "dark" if state["theme"] == "light" else "light"
        apply_theme()
        page.update()

    theme_toggle_btn.on_click = toggle_theme

    # ------------------ Folder Selection ------------------
    async def select_folder(e):
        cur_t = THEMES[state["theme"]]
        path = await file_picker.get_directory_path()
        if path:
            path_input.value = path
            log_output.value = f"Selected Repository: {path}\nReady to process commits."
            log_output.color = ft.Colors.GREEN_600 if state["theme"] == "light" else ft.Colors.GREEN_300
            page.update()

    browse_button.on_click = select_folder

    # ------------------ Process Cleaning ------------------
    async def process_cleaning(e):
        cur_t = THEMES[state["theme"]]
        repo_path = path_input.value
        target_line = target_line_input.value.strip()
        mode = state["mode"]

        if not repo_path or not os.path.exists(repo_path):
            log_output.value = "[ERROR] Please select a valid Git repository directory."
            log_output.color = ft.Colors.RED_500
            page.update()
            return

        if not target_line:
            log_output.value = "[ERROR] Target line to remove cannot be empty."
            log_output.color = ft.Colors.RED_500
            page.update()
            return

        targets = []
        if mode == "unpushed":
            targets = await asyncio.to_thread(get_unpushed_commits, repo_path)
            if not targets:
                log_output.value = "[NOTICE] No unpushed commits found, or upstream tracking branch is missing."
                log_output.color = ft.Colors.ORANGE_500
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
            log_output.color = ft.Colors.RED_500
            page.update()
            return

        total_tasks = len(targets)

        # Set UI to Active Running State
        run_button.disabled = True
        browse_button.disabled = True
        progress_card.visible = True
        loading_spinner.visible = True
        status_text.value = f"Starting cleanup of {total_tasks} commit(s)..."
        status_text.color = cur_t["text_primary"]
        task_count_text.value = f"Task 0 of {total_tasks}"
        percentage_text.value = "0%"
        progress_bar.value = 0.0
        log_output.value = f"Processing {total_tasks} commit(s)...\n"
        log_output.color = cur_t["primary"]
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

                # Update progress bar, percentage and task count live
                progress = idx / total_tasks
                pct = int(progress * 100)
                progress_bar.value = progress
                percentage_text.value = f"{pct}%"
                task_count_text.value = f"Task {idx} of {total_tasks}"
                log_output.value = "\n".join(logs)
                page.update()

            # Final summary report
            summary = (
                f"\n\n--- SUMMARY REPORT ---\n"
                f"Total Tasks: {total_tasks}\n"
                f"Done       : {done_cnt}\n"
                f"Not Found  : {not_found_cnt}\n"
                f"Failed     : {fail_cnt}"
            )

            log_output.value = "\n".join(logs) + summary
            log_output.color = cur_t["log_text"] if fail_cnt == 0 else ft.Colors.ORANGE_500
            status_text.value = f"Completed! {done_cnt} cleaned, {not_found_cnt} skipped, {fail_cnt} failed."
            status_text.color = ft.Colors.GREEN_600 if fail_cnt == 0 and state["theme"] == "light" else (ft.Colors.GREEN_400 if fail_cnt == 0 else ft.Colors.ORANGE_400)

        except Exception as ex:
            logs.append(f"[EXCEPTION] An error occurred: {ex}")
            log_output.value = "\n".join(logs)
            log_output.color = ft.Colors.RED_500
            status_text.value = "Encountered an error during execution."
            status_text.color = ft.Colors.RED_500
        finally:
            loading_spinner.visible = False
            run_button.disabled = False
            browse_button.disabled = False
            page.update()

    run_button.on_click = process_cleaning

    # ------------------ Layout Assembly ------------------
    page.add(
        header_row,
        ft.Divider(color=t["border"], height=20),
        lbl_repo,
        ft.Row([
            path_input,
            browse_button
        ], spacing=10),
        ft.Container(height=4),
        lbl_target,
        target_line_input,
        ft.Container(height=4),
        lbl_scope,
        scope_cards_row,
        hashes_input,
        ft.Container(height=8),
        ft.Row([run_button], alignment=ft.MainAxisAlignment.START),
        progress_card,
        ft.Container(height=4),
        lbl_logs,
        log_container
    )

if __name__ == "__main__":
    ft.run(main)