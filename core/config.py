from typing import Dict, Any, List


class ScraperConfig:
    """Configuration for Simplify.jobs scraper."""

    # Limits
    MAX_JOBS:   int = 400
    BATCH_SIZE: int = 100

    # Orders for Browser 
    HEADLESS: bool = False
    REQUEST_TIMEOUT: int = 30_000   # 30 ms

    # Defaults and changing these gives different jobs
    DEFAULT_KEYWORDS: List[str] = ["Data Science", "Data Analyst", "Machine Learning"]
    DEFAULT_LOCATION:  str= "North America"
    DEFAULT_LOCATIONS: List[str] = ["North America", "India", "Canada", "UK", "Australia"]
    DEFAULT_EMPLOYMENT_TYPES: List[str] = ["Full-Time", "Internship"]
    DEFAULT_EXPERIENCE: List[str] = ["Entry Level/New Grad", "Internship"]
    DEFAULT_REMOTE: List[str] = ["Remote", "Hybrid", "In Person"]

    @classmethod
    def get_headers(cls) -> Dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }

    @classmethod
    def validate_input(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "keywords":         data.get("keywords", cls.DEFAULT_KEYWORDS),
            "location":         data.get("location", cls.DEFAULT_LOCATION),
            "employment_type":  data.get("employment_type", cls.DEFAULT_EMPLOYMENT_TYPES),
            "experience_level": data.get("experience_level", cls.DEFAULT_EXPERIENCE),
            "remote_option":    data.get("remote_option", cls.DEFAULT_REMOTE),
            "category":         data.get("category", []),
            "max_jobs":      data.get("max_jobs", cls.MAX_JOBS),
        }

    @classmethod
    def get_initial_state(cls) -> Dict[str, int]:
        return {"current_scroll": 0, "total_scraped": 0}
