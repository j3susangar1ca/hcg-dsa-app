from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class AppStyles:
    @staticmethod
    def load_main_window_style(qss_path: Path) -> str:
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    @staticmethod
    def get_button_style(color: str, hover: str) -> str:
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
            }}
            QPushButton:hover {{ background-color: {hover}; }}
        """
