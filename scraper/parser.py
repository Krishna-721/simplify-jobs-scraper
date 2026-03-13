from typing import Optional, List, Dict, Any

from core.models import JobListing
from core.constants import SimplifyConstants


class SimplifyParser:
    """Parses raw Typesense API documents into JobListing objects."""

    def __init__(self):
        self.constants = SimplifyConstants

    def parse_jobs_from_response(
        self, body: Dict[str, Any], keyword: str
    ) -> List[JobListing]:
        """Extract all job listings from a multi_search API response body."""
        jobs = []
        for result in body.get("results", []):
            for hit in result.get("hits", []):
                doc = hit.get("document", {})
                if doc:
                    job = self.parse_single_doc(doc, keyword)
                    if job and job.is_valid():
                        jobs.append(job)
        return jobs

    def parse_single_doc(self, doc: Dict[str, Any], keyword: str) -> Optional[JobListing]:
        """Map one Typesense document → JobListing."""
        # if not hasattr(self, '_printed_keys'):
        #     self._printed_keys = True
        #     print(f"  [DEBUG] doc keys: {list(doc.keys())}")
        slug = (
            doc.get("slug")
            or doc.get("id")
            or doc.get("posting_id")
            or ""
        )
        link = f"{self.constants.JOBS_URL}/{slug}" if slug else ""

        locations = doc.get("locations", [])
        location = (
            ", ".join(locations) if isinstance(locations, list) else str(locations)
        )

        salary = doc.get("salary") or doc.get("salary_range") or ""
        if not salary:
            lo = doc.get("salary_min", "")
            hi = doc.get("salary_max", "")
            if lo or hi:
                salary = f"${lo} - ${hi}"

        emp_type = doc.get("type") or doc.get("employment_type") or ""
        if isinstance(emp_type, list):
            emp_type = ", ".join(emp_type)

        return JobListing(
            title=doc.get("title", ""),
            company=doc.get("company_name", "") or doc.get("company", ""),
            location=location,
            link=link,
            source=self.constants.SOURCE_NAME,
            description=doc.get("description", "") or doc.get("summary", ""),
            salary_range=str(salary),
            employment_type=emp_type,
            search_keyword=keyword,
        )
