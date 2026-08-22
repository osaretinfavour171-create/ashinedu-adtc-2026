"""Beautiful terminal UI for Ashinedu.

Uses Unicode box-drawing characters, ANSI colors, and visual hierarchy
to create a professional, aesthetically pleasing terminal experience.

Color scheme: Nigerian flag colors (Green + White) with accent colors.
"""

import sys
import os

# Force UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# ANSI Color codes
# ---------------------------------------------------------------------------

class C:
    """Color constants."""
    # Reset
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    # Standard colors
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Background
    BG_GREEN = "\033[42m"
    BG_DARK = "\033[40m"
    BG_BLUE = "\033[44m"

    # Nigerian flag colors
    NG_GREEN = "\033[38;2;0;128;0m"  # Deep green
    NG_GREEN_B = "\033[1;38;2;0;150;0m"  # Bright green


# ---------------------------------------------------------------------------
# Box drawing characters
# ---------------------------------------------------------------------------

class Box:
    """Unicode box-drawing characters."""
    # Single line
    H = "\u2500"   # ─
    V = "\u2502"   # │
    TL = "\u250c"  # ┌
    TR = "\u2510"  # ┐
    BL = "\u2514"  # └
    BR = "\u2518"  # ┘
    T = "\u252c"   # ┬
    B = "\u2534"   # ┴
    L = "\u251c"   # ├
    R = "\u2524"   # ┤
    X = "\u253c"   # ┼

    # Double line
    DH = "\u2550"  # ═
    DV = "\u2551"  # ║
    DTL = "\u2554" # ╔
    DTR = "\u2557" # ╗
    DBL = "\u255a" # ╚
    DBR = "\u255d" # ╝

    # Rounded
    RH = "\u2500"  # ─
    RTL = "\u256d" # ╭
    RTR = "\u256e" # ╮
    RBL = "\u2570" # ╰
    RBR = "\u256f" # ╯

    # Heavy
    HH = "\u2501"  # ━
    VH = "\u2503"  # ┃
    HTL = "\u250f" # ┏
    HTR = "\u2513" # ┓
    HBL = "\u2517" # ┗
    HBR = "\u251b" # ┛


# ---------------------------------------------------------------------------
# Icons
# ---------------------------------------------------------------------------

class Icon:
    """Visual icons using Unicode symbols."""
    MEDICAL = "\U0001f3e5"     # 🏥
    PILL = "\U0001f48a"        # 💊
    SYMPTOM = "\U0001f912"     # 🤒
    DRUG = "\U0001f48a"        # 💊
    REFER = "\u26a0\ufe0f"     # ⚠️
    CHECK = "\u2705"           # ✅
    CROSS = "\u274c"           # ❌
    STAR = "\u2b50"            # ⭐
    LIGHTNING = "\u26a1"       # ⚡
    BRAIN = "\U0001f9e0"       # 🧠
    BOOK = "\U0001f4da"        # 📚
    CLOCK = "\u23f0"           # ⏰
    WATER = "\U0001f4a7"       # 💧
    REST = "\U0001f3cf"        # 🏏 (or use 🛋️)
    HEART = "\u2764\ufe0f"     # ❤️
    FIRE = "\U0001f525"        # 🔥
    SHIELD = "\U0001f6e1\ufe0f" # 🛡️
    INFO = "\u2139\ufe0f"      # ℹ️
    ARROW = "\u27a1\ufe0f"     # ➡️
    DIAMOND = "\U0001f48e"     # 💎
    GREEN_CIRCLE = "\U0001f7e2" # 🟢
    YELLOW_CIRCLE = "\U0001f7e1" # 🟡
    RED_CIRCLE = "\U0001f534"  # 🔴


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _center(text: str, width: int) -> str:
    """Center text within a given width."""
    visible_len = len(text.replace("\033[", "").replace("[0m", "").replace("[1m", "").replace("[2m", ""))
    padding = max(0, (width - visible_len) // 2)
    return " " * padding + text


def _repeat(char: str, count: int) -> str:
    """Repeat a character."""
    return char * count


def _color_box(lines: list[str], color: str, width: int = 60) -> str:
    """Wrap lines in a colored box."""
    result = []
    border = f"{color}{Box.HH * (width + 2)}{C.RESET}"
    result.append(f"  {color}{Box.HTL}{border}{Box.HTR}{C.RESET}")
    for line in lines:
        # Pad line to width
        visible_len = len(line.replace("\033[", "").replace("[0m", "").replace("[1m", ""))
        pad = max(0, width - visible_len)
        result.append(f"  {color}{Box.VH}{C.RESET} {line}{' ' * pad} {color}{Box.VH}{C.RESET}")
    result.append(f"  {color}{Box.HBL}{border}{Box.HBR}{C.RESET}")
    return "\n".join(result)


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

def render_banner() -> str:
    """Render the main Ashinedu banner."""
    W = 62  # Box width

    lines = []

    # Top border
    lines.append(f"  {C.NG_GREEN}{Box.HTL}{Box.HH * (W + 2)}{Box.HTR}{C.RESET}")

    # Empty line
    lines.append(f"  {C.NG_GREEN}{Box.VH}{C.RESET}{' ' * (W + 2)}{C.NG_GREEN}{Box.VH}{C.RESET}")

    # Title line 1
    title1 = f"{C.BRIGHT_WHITE}{C.BOLD}  A  S  H  I  N  E  D  U  {C.RESET}"
    vis1 = len("  A  S  H  I  N  E  D  U  ")
    pad1 = max(0, (W + 2 - vis1) // 2)
    pad1r = max(0, W + 2 - vis1 - pad1)
    lines.append(
        f"  {C.NG_GREEN}{Box.VH}{C.RESET}"
        f"{' ' * pad1}{title1}{' ' * pad1r}"
        f"{C.NG_GREEN}{Box.VH}{C.RESET}"
    )

    # Subtitle
    sub = f"{C.DIM}{C.BRIGHT_WHITE}Offline Clinical Decision Support{C.RESET}"
    vis_sub = len("Offline Clinical Decision Support")
    pad_s = max(0, (W + 2 - vis_sub) // 2)
    pad_sr = max(0, W + 2 - vis_sub - pad_s)
    lines.append(
        f"  {C.NG_GREEN}{Box.VH}{C.RESET}"
        f"{' ' * pad_s}{sub}{' ' * pad_sr}"
        f"{C.NG_GREEN}{Box.VH}{C.RESET}"
    )

    # Tagline
    tag = f"{C.DIM}{C.BRIGHT_GREEN}for Nigerian Health Workers{C.RESET}"
    vis_tag = len("for Nigerian Health Workers")
    pad_t = max(0, (W + 2 - vis_tag) // 2)
    pad_tr = max(0, W + 2 - vis_tag - pad_t)
    lines.append(
        f"  {C.NG_GREEN}{Box.VH}{C.RESET}"
        f"{' ' * pad_t}{tag}{' ' * pad_tr}"
        f"{C.NG_GREEN}{Box.VH}{C.RESET}"
    )

    # Empty line
    lines.append(f"  {C.NG_GREEN}{Box.VH}{C.RESET}{' ' * (W + 2)}{C.NG_GREEN}{Box.VH}{C.RESET}")

    # Separator
    sep = f"{C.DIM}{C.GREEN}{Box.H * (W + 2)}{C.RESET}"
    lines.append(f"  {C.NG_GREEN}{Box.L}{sep}{Box.R}{C.RESET}")

    # Data sources
    data_line1 = f"{C.DIM} Data: Nigeria EML 2020  {C.GREEN}{Box.V}{C.RESET}  {C.DIM}NSTG 2022{C.RESET}"
    vis_d1 = len(" Data: Nigeria EML 2020   NSTG 2022")
    pad_d1 = max(0, (W + 2 - vis_d1) // 2)
    pad_d1r = max(0, W + 2 - vis_d1 - pad_d1)
    lines.append(
        f"  {C.NG_GREEN}{Box.VH}{C.RESET}"
        f"{' ' * pad_d1}{data_line1}{' ' * pad_d1r}"
        f"{C.NG_GREEN}{Box.VH}{C.RESET}"
    )

    data_line2 = f"{C.DIM} + Local Drug-Interaction Database {C.GREEN}{Box.V}{C.RESET}  {C.DIM}Offline{C.RESET}"
    vis_d2 = len(" + Local Drug-Interaction Database   Offline")
    pad_d2 = max(0, (W + 2 - vis_d2) // 2)
    pad_d2r = max(0, W + 2 - vis_d2 - pad_d2)
    lines.append(
        f"  {C.NG_GREEN}{Box.VH}{C.RESET}"
        f"{' ' * pad_d2}{data_line2}{' ' * pad_d2r}"
        f"{C.NG_GREEN}{Box.VH}{C.RESET}"
    )

    # Empty line
    lines.append(f"  {C.NG_GREEN}{Box.VH}{C.RESET}{' ' * (W + 2)}{C.NG_GREEN}{Box.VH}{C.RESET}")

    # Bottom border
    lines.append(f"  {C.NG_GREEN}{Box.HBL}{Box.HH * (W + 2)}{Box.HBR}{C.RESET}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Help text
# ---------------------------------------------------------------------------

def render_help() -> str:
    """Render the help text with visual structure."""
    W = 58
    lines = []

    lines.append(f"  {C.BRIGHT_GREEN}{C.BOLD}QUICK START{C.RESET}")
    lines.append(f"  {C.DIM}Type your question in English or Pidgin:{C.RESET}")
    lines.append("")

    examples = [
        (f"{C.CYAN}\"my pikin get hot body\"{C.RESET}", "symptom", "will ask follow-up questions"),
        (f"{C.CYAN}\"metronidazole and warfarin\"{C.RESET}", "drug", "instant interaction check"),
        (f"{C.CYAN}\"treatment for malaria\"{C.RESET}", "info", "general health question"),
        (f"{C.CYAN}\"paracetamol dose for child\"{C.RESET}", "dose", "drug dosing calculation"),
    ]

    for example, tag, desc in examples:
        tag_color = {
            "symptom": C.YELLOW,
            "drug": C.BRIGHT_CYAN,
            "info": C.BRIGHT_GREEN,
            "dose": C.MAGENTA,
        }.get(tag, C.WHITE)
        lines.append(f"  {tag_color}{tag:>8}{C.RESET}  {example}")
        lines.append(f"  {'':>8}  {C.DIM}{desc}{C.RESET}")
        lines.append("")

    lines.append(f"  {C.BRIGHT_GREEN}{C.BOLD}COMMANDS{C.RESET}")
    cmds = [
        ("help", "Show this help"),
        ("status", "Check service status"),
        ("stats", "Session statistics"),
        ("lang", "Switch Pidgin / English"),
        ("follow-up", "Track previous patient"),
        ("exit", "Quit Ashinedu"),
    ]
    for cmd, desc in cmds:
        lines.append(f"  {C.CYAN}{cmd:>12}{C.RESET}  {C.DIM}{desc}{C.RESET}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Status display
# ---------------------------------------------------------------------------

def render_status(services: dict, lang: str = "pidgin",
                  intake: bool = True, cache_info: str = "") -> str:
    """Render a beautiful status display."""
    lines = []
    lines.append(f"  {C.BRIGHT_GREEN}{C.BOLD}SYSTEM STATUS{C.RESET}")
    lines.append("")

    for name, ready in services.items():
        icon = Icon.GREEN_CIRCLE if ready else Icon.RED_CIRCLE
        status_text = f"{C.BRIGHT_GREEN}READY{C.RESET}" if ready else f"{C.BRIGHT_RED}OFFLINE{C.RESET}"
        lines.append(f"  {icon}  {name:<16} {status_text}")

    lines.append("")
    lang_display = "Pidgin English" if lang == "pidgin" else "English"
    intake_display = f"{Icon.CHECK} ON" if intake else f"{Icon.CROSS} OFF"
    lines.append(f"  {C.CYAN}\U0001f310{C.RESET}  {'Language':<16} {C.BRIGHT_WHITE}{lang_display}{C.RESET}")
    lines.append(f"  {C.CYAN}\U0001f3e5{C.RESET}  {'Triage':<16} {C.BRIGHT_WHITE}{intake_display}{C.RESET}")
    if cache_info:
        lines.append(f"  {C.CYAN}\u26a1{C.RESET}  {'Cache':<16} {C.DIM}{cache_info}{C.RESET}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Loading spinner / messages
# ---------------------------------------------------------------------------

def render_loading(message: str) -> str:
    """Render a loading indicator with message."""
    return f"\n  {C.DIM}{C.CYAN}\u25f7{C.RESET} {C.DIM}{message}{C.RESET}\n"


def render_thinking() -> str:
    """Render a thinking indicator."""
    return f"\n  {C.DIM}{C.BRIGHT_GREEN}\u22ef{C.RESET} {C.DIM}Processing...{C.RESET}\n"


# ---------------------------------------------------------------------------
# Answer formatting
# ---------------------------------------------------------------------------

def render_answer(answer: str, source: str = "", source_label: str = "") -> str:
    """Render an answer with visual formatting."""
    lines = []

    # Source badge
    if source_label:
        lines.append(f"  {source_label}")
        lines.append("")

    # Answer content with subtle left border
    for line in answer.split("\n"):
        lines.append(f"  {C.DIM}{C.GREEN}{Box.V}{C.RESET} {line}")

    return "\n".join(lines)


def render_referral(reason: str = "") -> str:
    """Render a referral alert."""
    lines = []
    lines.append("")
    lines.append(f"  {C.BRIGHT_RED}{C.BOLD}{Box.HTL}{Box.HH * 56}{Box.HTR}{C.RESET}")
    lines.append(f"  {C.BRIGHT_RED}{Box.VH}{C.RESET} {C.BRIGHT_RED}{C.BOLD}  {Icon.REFER}  REFERRAL NEEDED{C.RESET}{' ' * 30}{C.BRIGHT_RED}{Box.VH}{C.RESET}")
    lines.append(f"  {C.BRIGHT_RED}{Box.VH}{C.RESET}{' ' * 58}{C.BRIGHT_RED}{Box.VH}{C.RESET}")
    if reason:
        for line in reason.split("\n"):
            vis = len(line)
            pad = max(0, 56 - vis)
            lines.append(f"  {C.BRIGHT_RED}{Box.VH}{C.RESET} {line}{' ' * pad} {C.BRIGHT_RED}{Box.VH}{C.RESET}")
    lines.append(f"  {C.BRIGHT_RED}{Box.HBL}{Box.HH * 56}{Box.HBR}{C.RESET}")
    lines.append("")
    return "\n".join(lines)


def render_triage_question(question: str, question_num: int, total: int) -> str:
    """Render a triage question with visual indicator."""
    progress = f"[{question_num}/{total}]"
    return f"\n  {C.CYAN}{progress}{C.RESET} {C.BRIGHT_WHITE}{question}{C.RESET}\n  {C.DIM}>{C.RESET} "


# ---------------------------------------------------------------------------
# Separator
# ---------------------------------------------------------------------------

def render_separator() -> str:
    """Render a visual separator line."""
    return f"\n  {C.DIM}{C.GREEN}{Box.H * 58}{C.RESET}\n"


# ---------------------------------------------------------------------------
# Version info
# ---------------------------------------------------------------------------

def render_version() -> str:
    """Render version info."""
    return (
        f"  {C.DIM}Ashinedu v1.0{C.RESET}\n"
        f"  {C.DIM}ADTC 2026 Hackathon Submission{C.RESET}\n"
        f"  {C.DIM}Africa Deep Tech Foundation{C.RESET}"
    )
