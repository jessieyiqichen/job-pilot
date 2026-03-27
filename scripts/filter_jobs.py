"""Filter jobs to find investable positions matching user criteria."""
import sqlite3

conn = sqlite3.connect("data/jobpilot.db")

big_companies = [
    "腾讯", "字节跳动", "百度", "华为", "快手", "美团", "拼多多", "阿里巴巴",
    "滴滴", "Shopee", "OPPO", "爱奇艺", "中软国际", "软通动力", "博彦科技",
    "中电金信", "拓维云创", "中科软", "中电信", "西门子", "TCL", "美的", "比心",
    "上海华为", "华为云", "华为技术", "亿达信息", "水滴公司", "圣戈班",
    "同花顺", "新东方", "西南证券", "Anker",
]

tech_keywords = [
    "Python开发", "python开发", "Python 开发", "后端开发", "前端开发",
    "算法工程师", "算法实习", "iOS开发", "Android开发", "Flutter开发",
    "U3D开发", "3D主美", "web开发", "AIGC设计", "嵌入式", "架构师",
    "Trading Operation", "量化研究", "量化研究员", "数据分析师", "数据科学",
    "数据工程", "后端工程师", "移动端开发", "情感交互设计", "招聘专员",
    "内容策划", "数据标注", "视频生成", "Agent实习", "agent 开发",
    "研发工程师", "Python web", "python 大模型", "NLP工程师",
    "情感对话专家", "系统策划", "后端", "数据分析工程师",
    "AI大数据工程师", "高级数据分析", "AI解决方案",
    "穿透式监管", "审计师", "多模态理解算法", "评测算法",
]

skip_companies = ["示例科技", "创新互联网", "未来数据"]

rows = conn.execute("""
    SELECT j.id, j.job_id, j.title, j.company, j.city, j.platform,
           js.overall_score, js.profile_id, j.jd_text
    FROM jobs j
    LEFT JOIN job_scores js ON j.job_id = js.job_id
    ORDER BY j.id
""").fetchall()

print("=== Investable Positions (non-大厂, non-pure-tech) ===\n")
candidates = []
for r in rows:
    db_id, job_id, title, company, city, platform, score, pid, jd = r
    company = company or ""
    title = title or ""

    if any(bc in company for bc in big_companies):
        continue
    if any(tk in title for tk in tech_keywords):
        continue
    if any(x in company for x in skip_companies):
        continue

    score_str = f"score={score} (p{pid})" if score else "UNSCORED"
    needs_rescore = pid is not None and pid != 11
    flag = " [RESCORE]" if needs_rescore else (" [NEW]" if not score else "")

    print(f"[{db_id}] {company} - {title} | {city} | {score_str}{flag}")
    candidates.append((db_id, job_id, title, company, city, score, pid))

print(f"\nTotal candidates: {len(candidates)}")
conn.close()
