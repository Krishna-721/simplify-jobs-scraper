from core.models import ScraperState
from core.config import ScraperConfig


class StateManager:
    """Manages in-memory scraper state (scroll position + totals)."""

    def __init__(self):
        self.config = ScraperConfig
        self._state = ScraperState(**self.config.get_initial_state())

    def load_state(self) -> ScraperState:
        return self._state

    def save_state(self, state: ScraperState) -> None:
        self._state = state

    def reset_state(self) -> None:
        self._state = ScraperState(**self.config.get_initial_state())
