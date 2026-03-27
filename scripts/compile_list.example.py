"""
Compile the final investable positions list.

Customize the filters below to match your job search criteria.
Copy this file to compile_list.py and edit.
"""
import sqlite3

conn = sqlite3.connect("data/jobpilot.db")

rows = conn.execute("""
    SELECT j.id, j.title, j.company, j.city, j.platform,
           j.salary_min, j.salary_max, j.jd_text,
           js.overall_score, js.profile_id, js.suggestion
    FROM jobs j
    LEFT JOIN job_scores js ON j.job_id = js.job_id
    ORDER BY j.id
""").fetchall()

# ============================================================
# CUSTOMIZE THESE FILTERS
# ============================================================

# Companies to exclude (e.g. too large, outsourcing, etc.)
exclude_companies = [
    # "Company A",
    # "Company B",
]

# Companies to skip (fake listings, irrelevant)
skip_companies = [
    # "Fake Corp",
]

# Keywords that indicate a relevant role for you
relevant_keywords = [
    # "data analyst",
    # "product manager",
    # "business analyst",
]

# Title keywords that indicate roles to exclude
exclude_title_keywords = [
    # "frontend",
    # "backend",
    # "devops",
]

# Exceptions: titles that match exclude keywords but ARE relevant
title_exceptions = [
    # "AI product manager",
]

# ============================================================
# FILTER & DISPLAY
# ============================================================
results = []
for r in rows:
    db_id, title, company, city, platform, sal_min, sal_max, jd, score, pid, suggestion = r
    company = company or ""
    title = title or ""

    if any(ec in company for ec in exclude_companies):
        continue
    if any(sc in company for sc in skip_companies):
        continue

    # Add your own filtering logic here
    # ...

    if sal_min and sal_max:
        salary = f"{sal_min}-{sal_max}K"
    elif sal_min:
        salary = f"{sal_min}K+"
    else:
        salary = "N/A"

    results.append({
        "id": db_id, "title": title, "company": company,
        "city": city, "salary": salary, "score": score,
    })

results.sort(key=lambda x: -(x["score"] or 0))

print(f"Found {len(results)} matching positions:\n")
for r in results:
    score_str = f"score={r['score']}" if r["score"] else "unscored"
    print(f"  [{r['id']}] {r['company']} — {r['title']}")
    print(f"       {r['city']} | {r['salary']} | {score_str}")
    print()

conn.close()
