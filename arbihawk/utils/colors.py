"""
Colored output utilities for TUI.
"""

from colorama import init, Fore, Style

# Initialize colorama for Windows
init(autoreset=True)


class Colors:
    """Color constants for TUI."""
    HEADER = Fore.CYAN + Style.BRIGHT
    SUCCESS = Fore.GREEN + Style.BRIGHT
    WARNING = Fore.YELLOW + Style.BRIGHT
    ERROR = Fore.RED + Style.BRIGHT
    INFO = Fore.BLUE
    RESET = Style.RESET_ALL
    BOLD = Style.BRIGHT


def print_header(text: str):
    """Print header text."""
    print(f"\n{Colors.HEADER}{'=' * 60}")
    print(f"{text}")
    print(f"{'=' * 60}{Colors.RESET}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.SUCCESS}[OK] {text}{Colors.RESET}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.ERROR}[ERROR] {text}{Colors.RESET}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.WARNING}[WARN] {text}{Colors.RESET}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.INFO}[INFO] {text}{Colors.RESET}")


def print_step(text: str):
    """Print step message."""
    print(f"{Colors.INFO}-> {text}{Colors.RESET}")

