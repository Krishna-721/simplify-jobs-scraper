class SimplifyConstants:
    # Parameters that will always remain the same

    BASE_URL:   str = "https://simplify.jobs"
    JOBS_URL:   str = "https://simplify.jobs/jobs"
    API_HOST:   str = "js-ha.simplify.jobs"
    API_DETAIL: str = "https://api.simplify.jobs/v2/job-posting"
    SOURCE_NAME: str = "Simplify.jobs"

    # Typesense multi_search endpoint keyword
    SEARCH_ENDPOINT: str = "multi_search"

    # Output
    OUTPUT_CSV_PREFIX: str = "jobs"
