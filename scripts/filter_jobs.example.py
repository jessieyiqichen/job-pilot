"""
Filter jobs to find investable positions matching your criteria.

Copy this file to filter_jobs.py and customize the filters.
"""
import sqlite3

conn = sqlite3.connect("data/jobpilot.db")

# ============================================================
# CUSTOMIZE THESE FILTERS
# ============================================================

# Large companies to exclude
big_companies = [
    # "Google", "Meta", "Amazon",
]

# Title keywords to exclude (pure tech roles you don't want)
exclude_title_keywords = [
    # "backend developer", "frontend engineer", "devops",
]

# Companies to skip entirely
skip_companies = [
    # "Fake Corp",
]

# ============================================================
# QUERY & FILTER
# ============================================================
rows = conn.execute("""
    SELECT j.id, j.job_id, j.title, j.company, j.city, j.platform,
           js.overall_score, js.profile_id, j.jd_text
    FROM jobs j
    LEFT JOIN job_scores js ON j.job_id = js.job_id
    ORDER BY j.id
""").fetchall()

print("=== Matching Positions ===\n")
candidates = []
for r in rows:
    db_id, job_id, title, company, city, platform, score, pid, jd = r
    company = company or ""
    title = title or ""

    if any(bc in company for bc in big_companies):
        continue
    if any(tk in title for tk in exclude_title_keywords):
        continue
    if any(x in company for x in skip_companies):
        continue

    score_str = f"score={score}" if score else "UNSCORED"
    print(f"[{db_id}] {company} - {title} | {city} | {score_str}")
    candidates.append((db_id, job_id, title, company, city, score, pid))

print(f"\nTotal candidates: {len(candidates)}")
conn.close()
