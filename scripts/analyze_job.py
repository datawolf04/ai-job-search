#!/usr/bin/env python3
"""
analyze_job.py — Analyze a job ad against candidate profile.
Extracts: sector, role_type, fit_score, and gap analysis.
"""

import re
import sys
from pathlib import Path

# Candidate profile (extracted from OPENCODE.md)
PROFILE = {
    "education": [
        "ph.d. physics",
        "m.s. physics",
        "b.s. physics and mathematics",
    ],
    "experience_years": 10,  # 2015-2025 assistant professor
    "skills": {
        "primary": ["python", "numpy", "pandas", "tensorflow", "scikit-learn",
                     "r", "statistical modeling", "numerical methods", "computational modeling"],
        "secondary": ["sql", "postgresql", "bash", "git", "html", "css", "javascript",
                      "etl pipelines", "cluster computing", "linux"],
        "domain": ["physics education research", "data analysis", "approximation techniques",
                   "complex problem solving", "nlp", "deep learning", "prompt engineering"],
        "software": ["git", "github", "latex", "airflow", "kafka", "fem", "fea", "dashboard creation"],
    },
    "certifications": [
        "supervised machine learning",
        "advanced learning algorithms",
        "unsupervised learning",
        "recommenders",
        "reinforcement learning",
        "linux commands",
        "shell scripting",
        "sql",
        "etl",
        "data pipelines",
        "airflow",
        "kafka",
        "data warehousing",
    ],
    "strengths": [
        "grant writing",
        "program management",
        "technical communication",
        "mentoring",
        "cross-functional leadership",
        "independent project delivery",
        "end-to-end development",
    ],
    "gaps": [
        "industry product delivery",
        "commercial metrics",
        "production deployment",
        "mlops",
        "model monitoring",
        "a/b testing",
    ],
}

# Sector mapping based on company description keywords
SECTOR_KEYWORDS = {
    "Tech": ["software", "technology", "cloud", "saas", "platform", "digital", "ai", "machine learning"],
    "Finance": ["bank", "financial", "fintech", "investment", "insurance", "payment"],
    "Healthcare": ["health", "medical", "pharma", "biotech", "clinical", "hospital"],
    "E-commerce": ["ecommerce", "e-commerce", "retail", "marketplace", "shopping"],
    "Manufacturing": ["manufacturing", "industrial", "automation", "supply chain", "logistics"],
    "Education": ["education", "learning", "university", "school", "edtech"],
    "Consulting": ["consulting", "advisory", "professional services"],
    "Media": ["media", "entertainment", "content", "streaming", "publishing"],
    "Telecommunications": ["telecom", "communications", "network", "carrier"],
    "Energy": ["energy", "oil", "gas", "renewable", "utilities"],
}


def extract_sector(job_text: str) -> str:
    """Extract sector from job ad text."""
    job_lower = job_text.lower()

    # Check "About [Company]" section for company description
    about_match = re.search(r'about\s+\w+.*?(?=\n#|\n\*\*|\Z)', job_text, re.DOTALL | re.IGNORECASE)
    if about_match:
        about_text = about_match.group(0).lower()
    else:
        about_text = job_lower

    scores = {}
    for sector, keywords in SECTOR_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in about_text)
        if score > 0:
            scores[sector] = score

    if scores:
        return max(scores, key=scores.get)
    return "Unknown"


def extract_role_type(job_text: str) -> str:
    """Extract role type from job ad."""
    job_lower = job_text.lower()

    # Check for explicit mentions first
    if re.search(r'\bfull[\s-]?time\b', job_lower):
        return "Full-time"
    if re.search(r'\bpart[\s-]?time\b', job_lower):
        return "Part-time"
    if re.search(r'\bcontract(?:or)?\b', job_lower):
        # Verify it's about the role, not just mentioning contractors
        if re.search(r'(?:position|role|job|hire).*contract', job_lower):
            return "Contract"
    if re.search(r'\btemporary\b', job_lower):
        return "Contract"
    if re.search(r'\bintern(?:ship)?\b', job_lower):
        return "Internship"

    # If salary range is mentioned, likely full-time
    if re.search(r'salary\s+range', job_lower):
        return "Full-time"

    return "Full-time"  # default assumption


def extract_requirements(job_text: str) -> dict:
    """Extract job requirements from posting."""
    requirements = {
        "skills": [],
        "education": [],
        "experience_years": None,
        "tools": [],
    }

    job_lower = job_text.lower()

    # Extract required skills
    skill_patterns = [
        (r'experience\s+(?:with\s+)?(.*?)(?:;|\.|$)', "skills"),
        (r'prof(?:iciency|icient)\s+(?:in\s+)?(.*?)(?:;|\.|$)', "skills"),
        (r'knowledge\s+of\s+(.*?)(?:;|\.|$)', "skills"),
        (r'familiar(?:ity)?\s+with\s+(.*?)(?:;|\.|$)', "skills"),
    ]

    for pattern, category in skill_patterns:
        matches = re.findall(pattern, job_lower)
        for match in matches:
            # Clean up the match
            cleaned = re.sub(r'\s+', ' ', match).strip()
            if len(cleaned) > 3 and len(cleaned) < 200:
                requirements[category].append(cleaned)

    # Extract years of experience
    exp_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience', job_lower)
    if exp_match:
        requirements["experience_years"] = int(exp_match.group(1))

    # Extract education requirements
    edu_patterns = [
        r"bachelor'?s?\s+degree",
        r"master'?s?\s+degree",
        r"ph\.?d\.?",
        r"mba",
    ]
    for pattern in edu_patterns:
        if re.search(pattern, job_lower):
            requirements["education"].append(re.search(pattern, job_lower).group(0))

    # Extract specific tools/technologies
    tech_keywords = [
        "python", "r", "sql", "java", "scala", "spark", "hadoop", "aws", "gcp", "azure",
        "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "tableau", "power bi",
        "airflow", "kafka", "docker", "kubernetes", "git", "ci/cd",
    ]
    for tech in tech_keywords:
        if tech in job_lower:
            requirements["tools"].append(tech)

    return requirements


def detect_seniority(job_text: str) -> str:
    """Detect the seniority level of the role."""
    job_lower = job_text.lower()

    if re.search(r'\b(principal|staff|distinguished|fellow)\b', job_lower):
        return "principal"
    if re.search(r'\b(senior|sr\.?)\b', job_lower):
        return "senior"
    if re.search(r'\b(lead|head|director)\b', job_lower):
        return "lead"
    if re.search(r'\b(junior|jr\.?|entry[\s-]level|associate)\b', job_lower):
        return "junior"
    return "mid"


def compute_fit_score(job_text: str, profile: PROFILE) -> tuple[int, dict]:
    """Compute fit score and detailed analysis."""
    requirements = extract_requirements(job_text)
    seniority = detect_seniority(job_text)
    job_lower = job_text.lower()

    total_points = 0
    earned_points = 0
    gaps = []
    matches = []

    # Check skills (35% weight)
    skill_weight = 35
    if requirements["skills"]:
        for req_skill in requirements["skills"]:
            total_points += 1
            profile_all_skills = (
                profile["skills"]["primary"] +
                profile["skills"]["secondary"] +
                profile["skills"]["domain"]
            )
            skill_match = any(
                p_skill in req_skill or req_skill in p_skill
                for p_skill in profile_all_skills
            )
            if skill_match:
                earned_points += 1
                matches.append(f"Skill: {req_skill[:50]}")
            else:
                gaps.append(f"Skill gap: {req_skill[:50]}")

    skill_score = (earned_points / max(total_points, 1)) * skill_weight

    # Check tools (20% weight)
    tool_weight = 20
    if requirements["tools"]:
        tool_matches = sum(
            1 for tool in requirements["tools"]
            if tool in profile["skills"]["primary"] or tool in profile["skills"]["secondary"]
        )
        tool_score = (tool_matches / len(requirements["tools"])) * tool_weight
        for tool in requirements["tools"]:
            if tool not in profile["skills"]["primary"] and tool not in profile["skills"]["secondary"]:
                gaps.append(f"Tool gap: {tool}")
            else:
                matches.append(f"Tool match: {tool}")
    else:
        tool_score = tool_weight * 0.8

    # Check experience (25% weight) - heavily weighted for senior roles
    exp_weight = 25
    if requirements["experience_years"]:
        if profile["experience_years"] >= requirements["experience_years"]:
            # Bonus for exceeding significantly
            exp_ratio = min(profile["experience_years"] / requirements["experience_years"], 2.0)
            exp_score = exp_weight * min(exp_ratio, 1.2)
            matches.append(f"Experience: {profile['experience_years']} yrs (req: {requirements['experience_years']})")
        else:
            exp_score = (profile["experience_years"] / requirements["experience_years"]) * exp_weight
            gaps.append(f"Experience gap: {profile['experience_years']} vs {requirements['experience_years']} yrs")
    else:
        exp_score = exp_weight * 0.9

    # Check education (10% weight)
    edu_weight = 10
    edu_score = edu_weight
    if requirements["education"]:
        matches.append("Education: Ph.D. exceeds requirements")

    # Seniority penalty - academic to industry transition is harder at senior levels
    seniority_penalty = 0
    if seniority in ("principal", "staff", "senior"):
        # Check for production-related requirements
        production_keywords = [
            "production", "deploy", "mlops", "operationalize", "monitoring",
            "scale", "enterprise", "production-grade",
        ]
        production_requirements = sum(1 for kw in production_keywords if kw in job_lower)
        if production_requirements >= 2:
            seniority_penalty = 8  # penalty for senior roles requiring production experience
            gaps.append(f"Seniority gap: {seniority} level requires production/industry experience")

    # Profile gap penalty
    gap_keywords = profile["gaps"]
    gap_penalty = 0
    for gap in gap_keywords:
        if gap in job_lower:
            gap_penalty += 4  # increased penalty for relevant profile gaps
            gaps.append(f"Profile gap relevant: {gap}")

    # Calculate final score
    raw_score = skill_score + tool_score + exp_score + edu_score
    final_score = max(0, min(100, int(raw_score - gap_penalty - seniority_penalty)))

    analysis = {
        "matches": matches[:10],
        "gaps": gaps[:10],
        "requirements": requirements,
        "seniority": seniority,
    }

    return final_score, analysis


def main():
    if len(sys.argv) < 2:
        print("Usage: analyze_job.py <job_ad_file> [--profile profile.md]")
        sys.exit(1)

    job_file = Path(sys.argv[1])
    if not job_file.exists():
        print(f"Error: File not found: {job_file}")
        sys.exit(1)

    job_text = job_file.read_text()

    # Extract fields
    sector = extract_sector(job_text)
    role_type = extract_role_type(job_text)
    fit_score, analysis = compute_fit_score(job_text, PROFILE)

    # Output as key-value pairs for bash script to parse
    print(f"SECTOR={sector}")
    print(f"ROLE_TYPE={role_type}")
    print(f"FIT_SCORE={fit_score}")
    print(f"GAPS={'; '.join(analysis['gaps'][:5])}")
    print(f"MATCHES={'; '.join(analysis['matches'][:5])}")


if __name__ == "__main__":
    main()
