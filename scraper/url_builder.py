from urllib.parse import quote
from typing import Dict, Any, List

from core.constants import SimplifyConstants


class URLBuilder:
    """Builds Simplify.jobs search URLs from filter config."""

    def __init__(self):
        self.constants = SimplifyConstants

    def build_search_url(self, filters: Dict[str, Any], page: int = 1) -> str:
        """Construct the Simplify.jobs /jobs URL with all filters encoded."""
        params = []

        keyword = filters.get("keyword", "")
        if keyword:
            params.append(f"query={quote(str(keyword))}")

        location = filters.get("location", "")
        if location:
            params.append(f"state={quote(str(location))}")
            params.append("points=83%3B-170%3B7%3B-52")

        exp = self._to_list(filters.get("experience_level", []))
        if exp:
            params.append("experience=" + quote(";".join(exp)))

        emp = self._to_list(filters.get("employment_type", []))
        if emp:
            params.append("jobType=" + quote(";".join(emp)))

        remote = self._to_list(filters.get("remote_option", []))
        if remote:
            params.append("workArrangement=" + quote(";".join(remote)))

        category = self._to_list(filters.get("category", []))
        if category:
            params.append("category=" + quote(";".join(category)))

        url = self.constants.JOBS_URL
        if params:
            url += "?" + "&".join(params)
        return url

    @staticmethod
    def _to_list(value) -> List[str]:
        if isinstance(value, str):
            return [value] if value else []
        return list(value) if value else []
