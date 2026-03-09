from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any


@dataclass
class JobListing:
    """Represents a single job listing."""
    title:           Optional[str]
    company:         Optional[str]
    location:        Optional[str]
    link:            Optional[str]
    source:          str
    description:     Optional[str] = ""
    salary_range:    Optional[str] = ""
    employment_type: Optional[str] = ""
    search_keyword:  Optional[str] = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def is_valid(self) -> bool:
        return bool(self.title and self.link)

    def __eq__(self, other) -> bool:
        if not isinstance(other, JobListing):
            return False
        return self.link == other.link

    def __hash__(self) -> int:
        return hash(self.link)


@dataclass
class ScraperState:
    """Tracks pagination progress."""
    current_scroll: int = 0
    total_scraped:  int = 0

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "ScraperState":
        return cls(
            current_scroll=data.get("current_scroll", 0),
            total_scraped=data.get("total_scraped", 0),
        )

    def increment_scroll(self) -> None:
        self.current_scroll += 1

    def add_scraped(self, count: int) -> None:
        self.total_scraped += count
