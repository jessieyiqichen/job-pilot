"""
Boss直聘 adapter.

Calls boss-cli as a subprocess to search and retrieve job data.
Does NOT do any scraping — that's boss-cli's job.

If boss-cli is not installed, falls back to a mock mode for development.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from datetime import datetime

from jobpilot import config
from jobpilot.adapters.base import BaseAdapter, SearchFilters
from jobpilot.models import Job

logger = logging.getLogger(__name__)


def _parse_salary(salary_str: str) -> tuple[int, int]:
    """Parse salary string like '15-25K' or '15-25K·14薪' into (min, max) in yuan/month."""
    if not salary_str:
        return 0, 0
    # Match patterns like "15-25K", "15K-25K", "150-250元/天"
    m = re.match(r"(\d+)[_\-~](\d+)\s*[kK]", salary_str)
    if m:
        return int(m.group(1)) * 1000, int(m.group(2)) * 1000
    m = re.match(r"(\d+)[_\-~](\d+)", salary_str)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 0, 0


class BossAdapter(BaseAdapter):
    """Adapter that wraps boss-cli commands."""

    @property
    def platform_name(self) -> str:
        return "boss"

    def _refresh_credential(self) -> None:
        """Auto-refresh boss-cli credential from browser cookies.

        __zp_stoken__ expires in minutes, so we refresh before each search.
        """
        try:
            result = subprocess.run(
                [config.BOSS_CLI_PATH, "login", "--cookie-source", "chrome"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                logger.debug("Refreshed boss-cli credential from Chrome")
            else:
                logger.debug("boss-cli credential refresh failed: %s", result.stderr.strip())
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    def search(self, query: str, filters: SearchFilters | None = None) -> list[Job]:
        """Search jobs via boss-cli.

        Tries to call `boss search <query> --json` and parse the JSON output.
        Falls back to mock data if boss-cli is not available.
        """
        self._refresh_credential()
        filters = filters or SearchFilters()
        cmd = [config.BOSS_CLI_PATH, "search", query, "--json"]
        if filters.city:
            cmd.extend(["--city", filters.city])
        if filters.experience:
            cmd.extend(["--exp", filters.experience])
        if filters.salary_range:
            cmd.extend(["--salary", filters.salary_range])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.warning("boss-cli search failed: %s", result.stderr.strip())
                return []
            return self._parse_search_output(result.stdout)
        except FileNotFoundError:
            logger.warning(
                "boss-cli not found at '%s'. "
                "Install boss-cli or set BOSS_CLI_PATH env var.",
                config.BOSS_CLI_PATH,
            )
            return []
        except subprocess.TimeoutExpired:
            logger.error("boss-cli search timed out")
            return []

    def get_job_detail(self, job_id: str) -> Job | None:
        """Get job detail via boss-cli.

        Uses securityId to fetch details: `boss detail <securityId> --json`
        """
        cmd = [config.BOSS_CLI_PATH, "detail", job_id, "--json"]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.warning("boss-cli detail failed: %s", result.stderr.strip())
                return None
            return self._parse_detail_output(result.stdout, job_id)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("boss-cli not available for detail query")
            return None

    def _parse_search_output(self, output: str) -> list[Job]:
        """Parse boss-cli search output.

        Supports three formats:
        1. Envelope: {"ok": true, "data": {"jobList": [...]}}
        2. Plain JSON array: [...]
        3. JSON lines (one JSON object per line)
        """
        jobs: list[Job] = []
        try:
            data = json.loads(output)
            # Envelope format from boss-cli --json
            if isinstance(data, dict) and "data" in data:
                job_list = data["data"].get("jobList", [])
                for item in job_list:
                    jobs.append(self._item_to_job(item))
                return jobs
            # Plain JSON array
            if isinstance(data, list):
                for item in data:
                    jobs.append(self._item_to_job(item))
                return jobs
        except json.JSONDecodeError:
            pass

        # JSON lines fallback
        for line in output.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                jobs.append(self._item_to_job(item))
            except json.JSONDecodeError:
                continue
        return jobs

    def _parse_detail_output(self, output: str, job_id: str) -> Job | None:
        """Parse boss-cli detail output.

        Supports envelope format: {"ok": true, "data": {"jobInfo": {...}}}
        and plain JSON object.
        """
        try:
            data = json.loads(output)
            # Envelope format
            if isinstance(data, dict) and "data" in data:
                item = data["data"].get("jobInfo", data["data"])
                return self._item_to_job(item)
            # Plain object
            if isinstance(data, dict):
                return self._item_to_job(data)
            return None
        except json.JSONDecodeError:
            return None

    def _item_to_job(self, item: dict) -> Job:
        """Convert a boss-cli JSON item to a Job model.

        Priority order for field mapping (boss-cli envelope fields first):
        - job_id: securityId > encryptJobId > jobId > id
        - title: jobName > title
        - company: brandName > company
        - salary: salaryDesc > salary
        - city: cityName > city (+ areaDistrict if present)
        - experience: jobExperience > experience
        - education: jobDegree > education
        - skills: skills[] joined into jd_text prefix
        """
        salary_str = item.get("salaryDesc", item.get("salary", ""))
        sal_min, sal_max = _parse_salary(salary_str)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # securityId is the primary identifier in boss-cli envelope format
        job_id = str(
            item.get("securityId")
            or item.get("encryptJobId")
            or item.get("jobId")
            or item.get("id", "")
        )

        city = item.get("cityName", item.get("city", ""))
        area = item.get("areaDistrict", "")
        if area and area not in city:
            city = f"{city} {area}"

        # Build JD text: prepend skills list if available
        jd_text = item.get("jobDetail", item.get("jd", item.get("description", "")))
        skills = item.get("skills", [])
        if skills and isinstance(skills, list):
            skills_line = f"技能要求：{', '.join(skills)}\n\n"
            jd_text = skills_line + jd_text if jd_text else skills_line.strip()

        return Job(
            platform="boss",
            job_id=job_id,
            title=item.get("jobName", item.get("title", "")),
            company=item.get("brandName", item.get("company", "")),
            salary_min=sal_min,
            salary_max=sal_max,
            city=city,
            experience=item.get("jobExperience", item.get("experience", "")),
            education=item.get("jobDegree", item.get("education", "")),
            jd_text=jd_text,
            raw_data=item,
            discovered_at=now,
            status="new",
        )

    def _search_mock(self, query: str, filters: SearchFilters) -> list[Job]:
        """Return mock data for development when boss-cli is not available."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        city = filters.city or config.DEFAULT_CITY
        logger.info("Generating mock job data for development")
        mock_jobs = [
            Job(
                platform="boss",
                job_id="mock_001",
                title=f"高级{query}工程师",
                company="示例科技有限公司",
                salary_min=25000,
                salary_max=40000,
                city=city,
                experience="3-5年",
                education="本科",
                jd_text=(
                    f"岗位职责：\n"
                    f"1. 负责公司核心产品的{query}相关开发工作\n"
                    f"2. 参与系统架构设计和技术方案评审\n"
                    f"3. 主导技术难题攻关，提升系统性能和稳定性\n"
                    f"4. 指导初级工程师，进行代码审查\n\n"
                    f"任职要求：\n"
                    f"1. 本科及以上学历，计算机相关专业\n"
                    f"2. 3年以上{query}开发经验\n"
                    f"3. 扎实的编程基础，熟悉常用数据结构和算法\n"
                    f"4. 良好的沟通能力和团队协作精神\n"
                    f"5. 有大型项目经验者优先"
                ),
                raw_data={"source": "mock"},
                discovered_at=now,
            ),
            Job(
                platform="boss",
                job_id="mock_002",
                title=f"{query}技术负责人",
                company="未来数据科技",
                salary_min=35000,
                salary_max=55000,
                city=city,
                experience="5-10年",
                education="本科",
                jd_text=(
                    f"岗位职责：\n"
                    f"1. 负责{query}团队管理和技术方向把控\n"
                    f"2. 设计和优化系统架构\n"
                    f"3. 制定技术规范和开发流程\n"
                    f"4. 跨团队协作，推动技术项目落地\n\n"
                    f"任职要求：\n"
                    f"1. 本科及以上学历\n"
                    f"2. 5年以上{query}开发经验，2年以上团队管理经验\n"
                    f"3. 深入理解分布式系统设计\n"
                    f"4. 优秀的技术视野和学习能力"
                ),
                raw_data={"source": "mock"},
                discovered_at=now,
            ),
            Job(
                platform="boss",
                job_id="mock_003",
                title=f"{query}开发工程师",
                company="创新互联网公司",
                salary_min=15000,
                salary_max=25000,
                city=city,
                experience="1-3年",
                education="本科",
                jd_text=(
                    f"岗位职责：\n"
                    f"1. 参与公司产品的{query}功能开发\n"
                    f"2. 编写技术文档和单元测试\n"
                    f"3. 修复Bug，优化代码质量\n\n"
                    f"任职要求：\n"
                    f"1. 本科及以上学历，计算机相关专业\n"
                    f"2. 1年以上{query}开发经验\n"
                    f"3. 熟悉Git版本管理\n"
                    f"4. 学习能力强，有责任心"
                ),
                raw_data={"source": "mock"},
                discovered_at=now,
            ),
        ]
        return mock_jobs
