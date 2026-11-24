import streamlit as st
import mysql.connector
import pandas as pd
import hashlib
import html
import json
from collections import Counter
from matcher import match_resumes

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="TalentIQ | AI Recruitment",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# MYSQL CONNECTION
# =========================================================

def get_db_connection():
    return mysql.connector.connect(
        host=st.secrets["mysql"].get("host", "localhost"),
        port=int(st.secrets["mysql"].get("port", 3306)),
        user=st.secrets["mysql"].get("user", "root"),
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"].get("database", "talentiq")
    )


def init_database():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            job_title VARCHAR(255) NOT NULL UNIQUE,
            job_description LONGTEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS candidate_screenings (
            candidate_id VARCHAR(64) PRIMARY KEY,
            candidate_name VARCHAR(255),
            resume_filename VARCHAR(255),
            match_score FLOAT DEFAULT 0,
            status VARCHAR(40) DEFAULT 'Under Review',
            payload LONGTEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


# =========================================================
# DATABASE FUNCTIONS
# =========================================================

def load_jobs():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT id, job_title, job_description
        FROM jobs ORDER BY id DESC
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "id": row["id"],
            "title": row["job_title"],
            "description": row["job_description"]
        }
        for row in rows
    ]


def save_job(title, description):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO jobs (job_title, job_description)
        VALUES (%s, %s)
    """, (title, description))

    conn.commit()
    cur.close()
    conn.close()


def delete_job(job_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM jobs WHERE id = %s",
        (job_id,)
    )

    conn.commit()
    cur.close()
    conn.close()


def safe_score(value):
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0


def get_candidate_id(candidate):
    resume_id = candidate.get("resume_id")

    if resume_id:
        return str(resume_id)

    raw = (
        str(candidate.get("filename", "")) +
        str(candidate.get("candidate", "")) +
        str(candidate.get("extracted_text", ""))
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def save_candidates(items):
    conn = get_db_connection()
    cur = conn.cursor()

    for item in items:
        cid = get_candidate_id(item)

        payload = json.dumps(
            item,
            ensure_ascii=False,
            default=str
        )

        cur.execute("""
            INSERT INTO candidate_screenings
            (
                candidate_id,
                candidate_name,
                resume_filename,
                match_score,
                status,
                payload
            )
            VALUES (%s, %s, %s, %s, 'Under Review', %s)

            ON DUPLICATE KEY UPDATE
                candidate_name = VALUES(candidate_name),
                resume_filename = VALUES(resume_filename),
                match_score = VALUES(match_score),
                payload = VALUES(payload),
                updated_at = CURRENT_TIMESTAMP
        """, (
            cid,
            str(item.get("candidate", "Unknown"))[:255],
            str(item.get("filename", ""))[:255],
            safe_score(item.get("match_score")),
            payload
        ))

    conn.commit()
    cur.close()
    conn.close()


def load_candidates():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT candidate_id, status, payload
        FROM candidate_screenings
        ORDER BY updated_at DESC
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    found = {}
    statuses = {}

    for row in rows:
        cid = row["candidate_id"]

        try:
            found[cid] = json.loads(row["payload"])
            statuses[cid] = row["status"]
        except (TypeError, json.JSONDecodeError):
            continue

    return list(found.values()), statuses


def update_candidate_status(candidate_id, status):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE candidate_screenings
        SET status = %s
        WHERE candidate_id = %s
    """, (status, candidate_id))

    conn.commit()
    cur.close()
    conn.close()


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

try:
    init_database()
    db_ready = True
    db_error = ""

except Exception as exc:
    db_ready = False
    db_error = str(exc)


# =========================================================
# SESSION STATE
# =========================================================

defaults = {
    "results": [],
    "jobs": [],
    "candidate_statuses": {},
    "analysis_job_title": "Manual Job",
    "job_description_input": "",
    "selected_job_option": "Manual Entry",
    "db_loaded": False
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


if db_ready and not st.session_state.db_loaded:
    try:
        st.session_state.jobs = load_jobs()

        saved_results, saved_statuses = load_candidates()

        st.session_state.results = saved_results
        st.session_state.candidate_statuses = saved_statuses
        st.session_state.db_loaded = True

    except Exception as exc:
        db_ready = False
        db_error = str(exc)


# =========================================================
# CSS
# =========================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: Inter, sans-serif;
}

.stApp {
    background: #f4f7fc;
    color: #17233c;
}

[data-testid="stSidebar"] {
    background: #101d35;
}

[data-testid="stSidebar"] * {
    color: white !important;
}

.main-title {
    font-size: 34px;
    font-weight: 800;
    color: #17233c;
    margin-bottom: 4px;
}

.sub-title {
    color: #75829a;
    font-size: 14px;
    margin-bottom: 24px;
}

.hero {
    background: linear-gradient(115deg, #132849, #2458a6);
    padding: 28px;
    border-radius: 16px;
    color: white;
    margin-bottom: 24px;
}

.hero h2 {
    color: white;
    font-size: 28px;
    margin: 0;
}

.hero p {
    color: #dce8fa;
    margin-bottom: 0;
}

.metric-card {
    background: white;
    padding: 20px;
    border-radius: 13px;
    border: 1px solid #e6ebf3;
    min-height: 112px;
}

.metric-label {
    color: #75829a;
    font-size: 13px;
    font-weight: 600;
}

.metric-value {
    color: #17233c;
    font-size: 27px;
    font-weight: 800;
    margin-top: 8px;
}

.section-title {
    font-size: 20px;
    font-weight: 750;
    color: #17233c;
    margin: 16px 0 12px;
}

.stButton > button {
    border-radius: 8px;
    font-weight: 600;
}

div[data-testid="stMetric"] {
    background: white;
    padding: 15px;
    border-radius: 12px;
    border: 1px solid #e6ebf3;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# HELPERS
# =========================================================

def page_heading(title, subtitle=""):
    st.markdown(
        f'<div class="main-title">{html.escape(title)}</div>',
        unsafe_allow_html=True
    )

    if subtitle:
        st.markdown(
            f'<div class="sub-title">{html.escape(subtitle)}</div>',
            unsafe_allow_html=True
        )


def metric_card(label, value):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{html.escape(str(label))}</div>
            <div class="metric-value">{html.escape(str(value))}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def get_status(candidate_id):
    return st.session_state.candidate_statuses.get(
        candidate_id,
        "Under Review"
    )


def get_candidate_dataframe(items):
    rows = []

    for item in items:
        cid = get_candidate_id(item)

        rows.append({
            "Candidate": item.get("candidate", "Unknown"),
            "Filename": item.get("filename", ""),
            "Match Score": safe_score(item.get("match_score")),
            "Semantic Score": safe_score(item.get("semantic_score")),
            "Skill Score": safe_score(item.get("skill_score")),
            "Projects": (
                "Detected"
                if item.get("project_detected")
                else "Not detected"
            ),
            "Experience": (
                "Detected"
                if item.get("experience_detected")
                else "Not detected"
            ),
            "Status": get_status(cid)
        })

    return pd.DataFrame(rows)


def create_csv(items):
    df = get_candidate_dataframe(items)

    if not df.empty:
        df["Matched Skills"] = [
            ", ".join(x.get("matched_skills", []))
            for x in items
        ]

        df["Missing Skills"] = [
            ", ".join(x.get("missing_skills", []))
            for x in items
        ]

    return df.to_csv(index=False).encode("utf-8-sig")


def create_text_report(items):
    lines = [
        "TALENTIQ - RESUME SCREENING REPORT",
        "=" * 45,
        f"Job: {st.session_state.analysis_job_title}",
        f"Candidates analyzed: {len(items)}",
        ""
    ]

    for item in items:
        cid = get_candidate_id(item)

        lines.extend([
            f"Candidate: {item.get('candidate', 'Unknown')}",
            f"Filename: {item.get('filename', '')}",
            f"Match Score: {safe_score(item.get('match_score'))}%",
            f"Semantic Score: {safe_score(item.get('semantic_score'))}%",
            f"Skill Score: {safe_score(item.get('skill_score'))}%",
            f"Status: {get_status(cid)}",
            f"Matched Skills: {', '.join(item.get('matched_skills', []))}",
            f"Missing Skills: {', '.join(item.get('missing_skills', []))}",
            "-" * 45
        ])

    return "\n".join(lines)


def get_unique_skills(items):
    skills = []

    for item in items:
        skills.extend(item.get("extracted_skills", []))

    return Counter(skills)


def get_skill_list(item, key):
    value = item.get(key, [])

    if isinstance(value, str):
        return [value]

    if isinstance(value, list):
        return value

    return []


# =========================================================
# INTERVIEW QUESTION BANK
# =========================================================

QUESTION_BANK = {
    "Python Developer": [
        "What are Python lists and tuples?",
        "Explain decorators in Python.",
        "What is the difference between a list and a dictionary?",
        "Explain exception handling.",
        "What are Python generators?",
        "What is object-oriented programming?"
    ],
    "Data Analyst": [
        "Difference between SQL WHERE and HAVING?",
        "Explain INNER JOIN and LEFT JOIN.",
        "How do you handle missing data?",
        "What is data normalization?",
        "Explain descriptive statistics.",
        "How would you identify outliers?"
    ],
    "Data Scientist": [
        "Explain supervised and unsupervised learning.",
        "What is overfitting?",
        "Explain the bias-variance tradeoff.",
        "What is cross-validation?",
        "Explain precision, recall and F1-score."
    ],
    "Machine Learning Engineer": [
        "Explain the machine learning pipeline.",
        "What is feature engineering?",
        "What is gradient descent?",
        "Explain regularization.",
        "How would you deploy a model?"
    ],
    "AI Engineer": [
        "Difference between AI, ML and Deep Learning?",
        "What are embeddings?",
        "What is a transformer model?",
        "Explain Retrieval Augmented Generation.",
        "What is prompt engineering?"
    ],
    "Java Developer": [
        "Explain JVM, JRE and JDK.",
        "Interface vs abstract class?",
        "Explain inheritance.",
        "What is multithreading?"
    ],
    "Full Stack Developer": [
        "Explain frontend and backend.",
        "What is REST API?",
        "Authentication vs authorization?",
        "What is database indexing?"
    ],
    "Web Developer": [
        "Explain HTML semantic elements.",
        "What is the CSS box model?",
        "What is the DOM?",
        "Explain HTTP and HTTPS."
    ],
    "Cloud and DevOps": [
        "What is cloud computing?",
        "Explain IaaS, PaaS and SaaS.",
        "What is Docker?",
        "What is CI/CD?"
    ],
    "Cybersecurity": [
        "What is encryption?",
        "What is a firewall?",
        "What is SQL injection?",
        "Explain authentication and authorization."
    ],
    "QA Tester": [
        "What is software testing?",
        "Manual vs automation testing?",
        "What is regression testing?",
        "Explain bug life cycle."
    ],
    "Business Analyst": [
        "What is requirement gathering?",
        "Explain SWOT analysis.",
        "What is a business requirement document?",
        "What is process mapping?"
    ],
    "HR": [
        "What is talent acquisition?",
        "What is performance management?",
        "How would you manage onboarding?",
        "How do you handle workplace conflict?"
    ],
    "Finance": [
        "Explain balance sheets.",
        "What is cash flow?",
        "Explain assets and liabilities.",
        "What is working capital?"
    ],
    "Digital Marketing": [
        "What is SEO?",
        "Organic vs paid marketing?",
        "What is conversion rate?",
        "How do you measure campaign performance?"
    ],
    "UI/UX Designer": [
        "Explain UI and UX.",
        "What is wireframing?",
        "What is a user journey?",
        "What is usability testing?"
    ]
}


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:
    st.markdown("## 🎯 TalentIQ")
    st.caption("AI Recruitment Intelligence")
    st.divider()

    page = st.radio(
        "NAVIGATION",
        [
            "Dashboard",
            "Resume Matcher",
            "Candidates",
            "Job Management",
            "Candidate Comparison",
            "Skill Analysis",
            "Resume Quality",
            "Bias Audit",
            "Interview Questions"
        ]
    )

    st.divider()

    if db_ready:
        st.success("MySQL Connected")
    else:
        st.error("MySQL Not Connected")

    st.caption("TalentIQ | Version 4.0")


if not db_ready:
    st.error(
        "MySQL connection failed. Check .streamlit/secrets.toml "
        "and ensure MySQL Server is running."
    )
    st.code(db_error)
    st.stop()


results = st.session_state.results
jobs = st.session_state.jobs


# =========================================================
# 1. DASHBOARD
# =========================================================

if page == "Dashboard":

    page_heading(
        "Recruitment Dashboard",
        "Overview of resume screening and candidate pipeline."
    )

    st.markdown("""
    <div class="hero">
        <h2>Welcome to TalentIQ</h2>
        <p>AI-powered resume screening and candidate intelligence platform.</p>
    </div>
    """, unsafe_allow_html=True)

    total = len(results)

    average = (
        sum(safe_score(x.get("match_score")) for x in results) / total
        if total else 0
    )

    statuses = [
        get_status(get_candidate_id(x))
        for x in results
    ]

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        metric_card("Resumes Analyzed", total)

    with c2:
        metric_card("Average Match", f"{average:.1f}%")

    with c3:
        metric_card("Shortlisted", statuses.count("Shortlisted"))

    with c4:
        metric_card("Saved Jobs", len(jobs))

    st.markdown(
        '<div class="section-title">Candidate Pipeline</div>',
        unsafe_allow_html=True
    )

    p1, p2, p3 = st.columns(3)

    with p1:
        metric_card("Under Review", statuses.count("Under Review"))

    with p2:
        metric_card("Shortlisted", statuses.count("Shortlisted"))

    with p3:
        metric_card("Rejected", statuses.count("Rejected"))

    if results:
        best = max(
            results,
            key=lambda x: safe_score(x.get("match_score"))
        )

        st.markdown("### Top Candidate")

        st.write(
            f"**{best.get('candidate', 'Unknown')}** — "
            f"{safe_score(best.get('match_score')):.2f}%"
        )

        st.write(
            "Matched Skills: " +
            (", ".join(get_skill_list(best, "matched_skills")) or "None detected")
        )

        st.markdown("### Candidate Ranking")

        ranking = get_candidate_dataframe(results)

        st.bar_chart(
            ranking.head(10).set_index("Candidate")[["Match Score"]],
            horizontal=True
        )

        st.dataframe(
            ranking,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No candidates analyzed yet. Open Resume Matcher to begin.")

    st.caption(
        "Scores are screening indicators, not final hiring decisions."
    )


# =========================================================
# 2. RESUME MATCHER
# =========================================================

elif page == "Resume Matcher":

    page_heading(
        "Resume Matcher",
        "Compare candidate resumes against a job description."
    )

    if jobs:
        options = ["Manual Entry"] + [j["title"] for j in jobs]

        selected_job = st.selectbox(
            "Select saved job",
            options,
            key="selected_job_option"
        )

        if selected_job != "Manual Entry":
            selected = next(
                j for j in jobs if j["title"] == selected_job
            )

            if st.session_state.job_description_input != selected["description"]:
                st.session_state.job_description_input = selected["description"]

            st.session_state.analysis_job_title = selected["title"]

        else:
            st.session_state.analysis_job_title = "Manual Job"

    job_description = st.text_area(
        "Job Description",
        key="job_description_input",
        height=220
    )

    uploaded_files = st.file_uploader(
        "Upload Candidate Resumes (PDF)",
        type=["pdf"],
        accept_multiple_files=True
    )

    st.caption("Duplicate readable resumes are automatically skipped.")

    if st.button(
        "Analyze Resumes",
        type="primary",
        use_container_width=True
    ):

        if not job_description.strip():
            st.error("Please enter a job description.")

        elif not uploaded_files:
            st.error("Please upload at least one PDF resume.")

        else:
            try:
                with st.spinner("Analyzing resumes. Please wait..."):
                    analyzed = match_resumes(
                        job_description,
                        uploaded_files
                    )

                if not analyzed:
                    st.warning("No usable resume data was extracted.")

                else:
                    save_candidates(analyzed)

                    st.session_state.results = analyzed

                    st.success(
                        f"Analysis completed and {len(analyzed)} "
                        "candidate(s) saved to MySQL."
                    )

                    st.rerun()

            except Exception as exc:
                st.error(f"Analysis failed: {exc}")

    if results:
        st.divider()
        st.markdown("### Latest Analysis Results")

        st.dataframe(
            get_candidate_dataframe(results),
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "Download CSV Report",
            create_csv(results),
            "talentiq_candidate_report.csv",
            "text/csv"
        )

        st.download_button(
            "Download Text Report",
            create_text_report(results),
            "talentiq_report.txt",
            "text/plain"
        )


# =========================================================
# 3. CANDIDATES
# =========================================================

elif page == "Candidates":
    
    page_heading(
        "Candidate Management",
        "View and manage all screened candidates."
    )
 
    if not results:
        st.info("No candidates available. Analyze resumes first.")

    else:
        df = get_candidate_dataframe(results)

        search = st.text_input("Search candidate by name or filename")

        if search:
            df = df[
                df["Candidate"].str.contains(search, case=False, na=False) |
                df["Filename"].str.contains(search, case=False, na=False)
            ]

        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Under Review", "Shortlisted", "Rejected"]
        )

        if status_filter != "All":
            df = df[df["Status"] == status_filter]

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        st.markdown("### Update Candidate Status")

        candidate_options = {
            f"{x.get('candidate', 'Unknown')} ({x.get('filename', '')})":
            get_candidate_id(x)
            for x in results
        }

        selected_name = st.selectbox(
            "Select Candidate",
            list(candidate_options.keys())
        )

        selected_id = candidate_options[selected_name]

        current_status = get_status(selected_id)

        new_status = st.selectbox(
            "New Status",
            ["Under Review", "Shortlisted", "Rejected"],
            index=["Under Review", "Shortlisted", "Rejected"].index(current_status)
        )

        if st.button("Update Status", type="primary"):
            try:
                update_candidate_status(selected_id, new_status)

                st.session_state.candidate_statuses[selected_id] = new_status

                st.success("Candidate status updated.")
                st.rerun()

            except Exception as exc:
                st.error(f"Update failed: {exc}")


# =========================================================
# 4. JOB MANAGEMENT
# =========================================================

elif page == "Job Management":

    page_heading(
        "Job Management",
        "Create and manage job descriptions."
    )

    st.markdown("### Add New Job")

    with st.form("add_job_form"):
        title = st.text_input("Job Title")

        description = st.text_area(
            "Job Description",
            height=200
        )

        submitted = st.form_submit_button(
            "Save Job",
            use_container_width=True
        )

        if submitted:
            if not title.strip() or not description.strip():
                st.error("Enter both job title and description.")

            else:
                try:
                    save_job(title.strip(), description.strip())

                    st.session_state.jobs = load_jobs()

                    st.success("Job saved successfully.")
                    st.rerun()

                except mysql.connector.IntegrityError:
                    st.error("This job title already exists.")

                except Exception as exc:
                    st.error(f"Could not save job: {exc}")

    st.divider()
    st.markdown("### Saved Jobs")

    jobs = st.session_state.jobs

    if not jobs:
        st.info("No jobs saved yet.")

    else:
        for job in jobs:
            with st.expander(job["title"]):
                st.write(job["description"])

                if st.button(
                    "Delete Job",
                    key=f"delete_job_{job['id']}"
                ):
                    try:
                        delete_job(job["id"])
                        st.session_state.jobs = load_jobs()

                        st.success("Job deleted.")
                        st.rerun()

                    except Exception as exc:
                        st.error(f"Delete failed: {exc}")


# =========================================================
# 5. CANDIDATE COMPARISON
# =========================================================

elif page == "Candidate Comparison":

    page_heading(
        "Candidate Comparison",
        "Compare candidate screening results side by side."
    )

    if len(results) < 2:
        st.info("At least two candidates are required for comparison.")

    else:
        candidate_names = [
            f"{x.get('candidate', 'Unknown')} ({x.get('filename', '')})"
            for x in results
        ]

        selected_names = st.multiselect(
            "Select candidates",
            candidate_names,
            default=candidate_names[:2],
            max_selections=4
        )

        selected_items = [
            x for x, name in zip(results, candidate_names)
            if name in selected_names
        ]

        if len(selected_items) >= 2:
            comparison_rows = []

            for item in selected_items:
                comparison_rows.append({
                    "Candidate": item.get("candidate", "Unknown"),
                    "Match Score": safe_score(item.get("match_score")),
                    "Semantic Score": safe_score(item.get("semantic_score")),
                    "Skill Score": safe_score(item.get("skill_score")),
                    "Matched Skills": ", ".join(
                        get_skill_list(item, "matched_skills")
                    ),
                    "Missing Skills": ", ".join(
                        get_skill_list(item, "missing_skills")
                    ),
                    "Status": get_status(get_candidate_id(item))
                })

            comparison_df = pd.DataFrame(comparison_rows)

            st.dataframe(
                comparison_df,
                use_container_width=True,
                hide_index=True
            )

            st.markdown("### Match Score Comparison")

            chart_df = comparison_df[
                ["Candidate", "Match Score", "Semantic Score", "Skill Score"]
            ].set_index("Candidate")

            st.bar_chart(chart_df)

            st.caption(
                "Comparison is based on extracted resume information and "
                "screening scores."
            )


# =========================================================
# 6. SKILL ANALYSIS
# =========================================================

elif page == "Skill Analysis":

    page_heading(
        "Skill Analysis",
        "Analyze candidate skills and identify skill gaps."
    )

    if not results:
        st.info("Analyze resumes first to see skill analytics.")

    else:
        skill_counts = get_unique_skills(results)

        if skill_counts:
            skill_df = pd.DataFrame(
                skill_counts.items(),
                columns=["Skill", "Count"]
            ).sort_values("Count", ascending=False)

            c1, c2 = st.columns(2)

            with c1:
                metric_card("Unique Skills", len(skill_counts))

            with c2:
                metric_card(
                    "Total Skill Mentions",
                    sum(skill_counts.values())
                )

            st.markdown("### Most Common Skills")

            st.bar_chart(
                skill_df.head(15).set_index("Skill")
            )

            st.dataframe(
                skill_df,
                use_container_width=True,
                hide_index=True
            )

        else:
            st.warning("No extracted skills were found.")

        st.markdown("### Candidate Skill Gaps")

        for item in results:
            with st.expander(item.get("candidate", "Unknown")):
                matched = get_skill_list(item, "matched_skills")
                missing = get_skill_list(item, "missing_skills")

                st.write("**Matched Skills**")
                st.write(", ".join(matched) if matched else "None detected")

                st.write("**Missing Skills**")
                st.write(", ".join(missing) if missing else "None detected")


# =========================================================
# 7. RESUME QUALITY
# =========================================================

elif page == "Resume Quality":

    page_heading(
        "Resume Quality",
        "Review extracted resume information and completeness."
    )

    if not results:
        st.info("Analyze resumes first.")

    else:
        quality_rows = []

        for item in results:
            text_content = str(item.get("extracted_text", ""))

            skills = get_skill_list(item, "extracted_skills")

            project_detected = bool(item.get("project_detected"))
            experience_detected = bool(item.get("experience_detected"))

            checks = {
                "Text Extracted": bool(text_content.strip()),
                "Skills Found": bool(skills),
                "Projects Found": project_detected,
                "Experience Found": experience_detected
            }

            completed = sum(checks.values())
            quality_score = completed / len(checks) * 100

            quality_rows.append({
                "Candidate": item.get("candidate", "Unknown"),
                "Text Characters": len(text_content),
                "Skills Found": len(skills),
                "Project Section": (
                    "Detected" if project_detected else "Not detected"
                ),
                "Experience Section": (
                    "Detected" if experience_detected else "Not detected"
                ),
                "Completeness Indicator": f"{quality_score:.0f}%"
            })

        quality_df = pd.DataFrame(quality_rows)

        st.dataframe(
            quality_df,
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            "Completeness indicator checks extracted information only. "
            "It is not a measure of a person's ability or resume quality."
        )

        st.markdown("### Individual Resume Review")

        for item in results:
            with st.expander(item.get("candidate", "Unknown")):
                st.write("**Filename:**", item.get("filename", "Unknown"))

                st.write(
                    "**Extracted Skills:**",
                    ", ".join(get_skill_list(item, "extracted_skills"))
                    or "None detected"
                )

                st.write(
                    "**Projects:**",
                    "Detected" if item.get("project_detected") else "Not detected"
                )

                st.write(
                    "**Experience:**",
                    "Detected" if item.get("experience_detected") else "Not detected"
                )


# =========================================================
# 8. BIAS AUDIT
# =========================================================

elif page == "Bias Audit":

    page_heading(
        "Bias Audit",
        "Review screening data for potential inconsistencies."
    )

    st.warning(
        "This is a preliminary data-quality review, not a validated "
        "fairness or discrimination audit."
    )

    if not results:
        st.info("Analyze resumes first.")

    else:
        audit_rows = []

        for item in results:
            score = safe_score(item.get("match_score"))

            missing_skills = get_skill_list(item, "missing_skills")
            matched_skills = get_skill_list(item, "matched_skills")

            flags = []

            if not item.get("extracted_text"):
                flags.append("No extracted text")

            if score < 0 or score > 100:
                flags.append("Score outside expected range")

            if not matched_skills and not missing_skills:
                flags.append("No skill comparison data")

            audit_rows.append({
                "Candidate": item.get("candidate", "Unknown"),
                "Match Score": score,
                "Matched Skills": len(matched_skills),
                "Missing Skills": len(missing_skills),
                "Review Flags": ", ".join(flags) if flags else "No basic flags"
            })

        audit_df = pd.DataFrame(audit_rows)

        st.dataframe(
            audit_df,
            use_container_width=True,
            hide_index=True
        )

        st.markdown("### Screening Score Distribution")

        st.bar_chart(
            audit_df.set_index("Candidate")[["Match Score"]]
        )

        st.markdown("### Audit Notes")

        st.write(
            "- Review resumes with missing extracted text."
        )
        st.write(
            "- Check whether the job description contains unnecessary requirements."
        )
        st.write(
            "- Review low and high scores manually before making decisions."
        )
        st.write(
            "- Do not use protected personal characteristics to rank candidates."
        )


# =========================================================
# 9. INTERVIEW QUESTIONS
# =========================================================

elif page == "Interview Questions":

    page_heading(
        "Interview Questions",
        "Generate role-based interview question sets."
    )

    selected_role = st.selectbox(
        "Select Job Role",
        list(QUESTION_BANK.keys())
    )

    number_of_questions = st.slider(
        "Number of Questions",
        min_value=1,
        max_value=len(QUESTION_BANK[selected_role]),
        value=min(5, len(QUESTION_BANK[selected_role]))
    )

    questions = QUESTION_BANK[selected_role][:number_of_questions]

    st.markdown("### Interview Question Set")

    for index, question in enumerate(questions, 1):
        st.markdown(f"**{index}. {question}**")

    st.download_button(
        "Download Questions",
        "\n".join(
            f"{i}. {question}"
            for i, question in enumerate(questions, 1)
        ),
        f"{selected_role.replace(' ', '_')}_interview_questions.txt",
        "text/plain"
    )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "TalentIQ | AI Resume Screening Platform | "
    "Built with Python, Streamlit, NLP and MySQL"
)