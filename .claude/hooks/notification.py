#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Claude Code Notification Hook
Plays cached MP3 alerts and sends desktop notifications when Claude needs attention.
Used as a Stop (post-response) and Notification hook.
"""

import json
import os
import platform
import random
import shutil
import subprocess
import sys
from pathlib import Path

CACHE_DIR = Path(__file__).parent / "cache"
IS_WINDOWS = platform.system() == "Windows"

# Volume level: 0 (silent) to 1000 (max). Default 500 = 50%.
VOLUME = 400

# Messages — correspond to cache files in .claude/hooks/cache/
MESSAGES = {
    "ready": "The AI Agent has finished its work. Awaiting your instructions.",
    "permission": "Your attention is required.",
    "idle": "Awaiting your instructions.",
}

# Random completion phrases — must match cached MP3 filenames
COMPLETION_PHRASES = [
    "Work complete! Awaiting your instructions.",
    "All done! Awaiting your instructions.",
    "Task finished! Awaiting your instructions.",
    "Job complete! The AI Agent has finished its work.",
    "The AI Agent has finished its work. Ready for next task!",
    "All clear! Standing by.",
    "Mission accomplished! What's next.",
    "That's a wrap! Ready for more.",
    "All systems go! What's the next move.",
    "Another one down! Standing by.",
    "Wrapped up! Your move.",
]

# Desktop notification titles
NOTIFICATION_TITLES = {
    "ready": "Claude Code — Complete",
    "permission": "Claude Code — Attention",
    "idle": "Claude Code",
}


# =============================================================================
# Desktop Notifications (cross-platform)
# =============================================================================


def send_desktop_notification(title: str, message: str) -> bool:
    system = platform.system()
    try:
        if system == "Linux":
            return _notify_linux(title, message)
        elif system == "Darwin":
            return _notify_macos(title, message)
        elif system == "Windows":
            return _notify_windows(title, message)
    except Exception:
        pass
    return False


def _notify_linux(title: str, message: str) -> bool:
    if not shutil.which("notify-send"):
        return False
    try:
        subprocess.run(
            [
                "notify-send",
                "-a", "Claude Code",
                "-h", "string:x-canonical-private-synchronous:claude-code",
                "-h", "string:x-dunst-stack-tag:claude-code",
                title,
                message,
            ],
            check=True,
            capture_output=True,
            timeout=5,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def _notify_macos(title: str, message: str) -> bool:
    if shutil.which("terminal-notifier"):
        try:
            # Detect current terminal app for click-to-focus
            result = subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to get name of first process whose frontmost is true'],
                capture_output=True, text=True, timeout=2,
            )
            front_app = result.stdout.strip() if result.returncode == 0 else "Terminal"

            # Map common terminal names to bundle IDs
            bundle_ids = {
                "Terminal": "com.apple.Terminal",
                "iTerm2": "com.googlecode.iterm2",
                "Alacritty": "io.alacritty",
                "kitty": "net.kovidgoyal.kitty",
                "WezTerm": "com.github.wez.wezterm",
                "Hyper": "co.zeit.hyper",
            }
            activate_id = bundle_ids.get(front_app, f"com.apple.{front_app.lower().replace(' ', '')}")

            subprocess.run(
                [
                    "terminal-notifier",
                    "-title", title,
                    "-message", message,
                    "-group", "claude-code",
                    "-activate", activate_id,
                ],
                check=True, capture_output=True, timeout=5,
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

    title_esc = title.replace("\\", "\\\\").replace('"', '\\"')
    message_esc = message.replace("\\", "\\\\").replace('"', '\\"')
    try:
        subprocess.run(
            ["osascript", "-e", f'display notification "{message_esc}" with title "{title_esc}"'],
            check=True, capture_output=True, timeout=5,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _notify_windows(title: str, message: str) -> bool:
    title_esc = title.replace("'", "''")
    message_esc = message.replace("'", "''")

    toast_script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
$nodes = $xml.GetElementsByTagName('text')
$nodes.Item(0).AppendChild($xml.CreateTextNode('{title_esc}')) | Out-Null
$nodes.Item(1).AppendChild($xml.CreateTextNode('{message_esc}')) | Out-Null
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
$toast.Tag = 'claude-code'
$toast.Group = 'claude-code'
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Claude Code')
$notifier.Show($toast)
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", toast_script],
            capture_output=True, timeout=10,
        )
        if result.returncode == 0:
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    balloon_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.SystemIcons]::Information
$notify.Visible = $true
$notify.BalloonTipTitle = '{title_esc}'
$notify.BalloonTipText = '{message_esc}'
$notify.ShowBalloonTip(5000)
Start-Sleep -Milliseconds 200
$notify.Dispose()
"""
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", balloon_script],
            check=True, capture_output=True, timeout=10,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False


# =============================================================================
# Audio Playback (cached MP3 only)
# =============================================================================


def play_cached(text: str) -> bool:
    safe_name = text.replace("/", "-").replace("\x00", "")
    cache_path = CACHE_DIR / f"{safe_name}.mp3"
    if not cache_path.exists():
        return False

    # Windows: use winmm MCI (no external deps, supports MP3)
    if IS_WINDOWS:
        try:
            import ctypes
            winmm = ctypes.windll.winmm
            buf = ctypes.create_unicode_buffer(256)
            rc = winmm.mciSendStringW(
                f'open "{cache_path}" type mpegvideo alias claude_snd', buf, 256, None
            )
            if rc == 0:
                winmm.mciSendStringW(f'setaudio claude_snd volume to {VOLUME}', buf, 256, None)
                winmm.mciSendStringW('play claude_snd wait', buf, 256, None)
                winmm.mciSendStringW('close claude_snd', buf, 256, None)
                return True
            # MCI refused the file — fall through to ffplay/mpv
        except Exception:
            pass

    vol_pct = max(0, min(VOLUME, 1000)) / 10  # 0-100 for mpv/ffplay
    players = [
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-volume", str(int(vol_pct))],
        ["mpv", "--no-video", "--really-quiet", f"--volume={int(vol_pct)}"],
    ]
    for cmd in players:
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd + [str(cache_path)], check=True, capture_output=True)
                return True
            except subprocess.CalledProcessError:
                continue
    return False


# =============================================================================
# Main
# =============================================================================


def announce(message: str, notification_type: str) -> None:
    title = NOTIFICATION_TITLES.get(notification_type, NOTIFICATION_TITLES["ready"])
    send_desktop_notification(title, message)
    play_cached(message)


def main():
    notify = "--notify" in sys.argv
    permission = "--permission" in sys.argv

    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        input_data = {}

    if permission:
        notif_type = input_data.get("notification_type", "")
        if notif_type == "idle_prompt":
            announce(MESSAGES["idle"], "idle")
        else:
            announce(MESSAGES["permission"], "permission")
        sys.exit(0)

    if notify:
        if input_data.get("hook_event_name") == "Stop":
            message = random.choice(COMPLETION_PHRASES)
            announce(message, "ready")

    sys.exit(0)


if __name__ == "__main__":
    main()
