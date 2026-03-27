"""Compile the final investable positions list."""
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

# Big companies to exclude
big_cos = [
    "腾讯", "字节跳动", "百度", "华为", "快手", "美团", "拼多多", "阿里巴巴",
    "滴滴", "Shopee", "OPPO", "爱奇艺", "中电信", "西门子", "TCL", "美的",
    "比心", "水滴公司", "同花顺", "新东方", "圣戈班", "BOSS直聘",
]
skip_cos = [
    "示例科技", "创新互联网", "未来数据", "中软国际", "软通动力",
    "博彦科技", "中电金信", "拓维云创", "中科软", "亿达信息",
    "中移联合", "潮生活", "Elys AI",
]

# Must contain one of these keywords to be relevant
product_kw = ["产品", "PM", "BD", "运营", "策划", "项目管理"]
ai_kw = ["AI", "ai", "AIGC", "大模型", "人工智能"]

# Pure tech titles to exclude
tech_titles = [
    "开发", "算法", "工程师", "研发", "标注", "设计师", "设计实习",
    "3D主美", "Trading", "招聘", "量化", "数据分析师",
]

# Exceptions: these specific titles ARE product roles despite containing "工程师" etc.
product_exceptions = [
    "AI产品", "ai产品", "产品经理", "产品实习", "产品策划", "项目管理",
    "BD", "运营", "内容运营",
]

results = []
for r in rows:
    db_id, title, company, city, platform, sal_min, sal_max, jd, score, pid, suggestion = r
    company = company or ""
    title = title or ""

    # Skip big companies
    if any(bc in company for bc in big_cos):
        continue
    if any(sc in company for sc in skip_cos):
        continue

    # Must be AI-related AND product-oriented
    has_product = any(kw in title for kw in product_kw)
    has_ai = any(kw in title for kw in ai_kw)
    if not (has_product or has_ai):
        continue

    # Check if it's a pure tech role (but allow product exceptions)
    is_exception = any(pe in title for pe in product_exceptions)
    if not is_exception:
        is_tech = any(tk in title for tk in tech_titles)
        if is_tech:
            continue

    # Format salary
    if sal_min and sal_max:
        salary = f"{sal_min}-{sal_max}K"
    elif sal_min:
        salary = f"{sal_min}K+"
    else:
        salary = "面议"

    results.append({
        "id": db_id, "title": title, "company": company,
        "city": city, "salary": salary,
        "score": score, "pid": pid,
        "suggestion": (suggestion or "")[:80],
        "jd_preview": (jd or "")[:120],
    })

# Sort: profile 11 scores first, then other profile scores, then unscored
def sort_key(x):
    if x["pid"] == 11 and x["score"]:
        return (0, -x["score"])
    elif x["score"]:
        return (1, -x["score"])
    else:
        return (2, 0)

results.sort(key=sort_key)

print("=" * 80)
print("  可投递岗位清单 — AI产品/PM/BD/运营 @ 非大厂创业公司/研究院")
print("=" * 80)

# Category A: scored with profile 11
cat_a = [r for r in results if r["pid"] == 11]
cat_b = [r for r in results if r["pid"] and r["pid"] != 11]
cat_c = [r for r in results if not r["pid"]]

if cat_a:
    print("\n--- A. Profile 11 已评分 ---\n")
    for r in cat_a:
        print(f"  [{r['id']}] {r['company']} — {r['title']}")
        print(f"       {r['city']} | {r['salary']} | 评分: {r['score']}")
        print()

if cat_b:
    print("\n--- B. 旧Profile评分（待用Profile 11重评）---\n")
    for r in cat_b:
        print(f"  [{r['id']}] {r['company']} — {r['title']}")
        print(f"       {r['city']} | {r['salary']} | 评分: {r['score']} (p{r['pid']})")
        print()

if cat_c:
    print("\n--- C. 未评分 ---\n")
    for r in cat_c:
        print(f"  [{r['id']}] {r['company']} — {r['title']}")
        print(f"       {r['city']} | {r['salary']}")
        print()

print(f"共 {len(results)} 个可投递岗位 (A={len(cat_a)}, B={len(cat_b)}, C={len(cat_c)})")
conn.close()
