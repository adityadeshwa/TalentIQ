# TalentIQ – AI Recruitment Platform

🚀 **Live Demo:** https://talentiq-9t9r5kxpf4sjm8kmbgyc3e.streamlit.app/

TalentIQ is a Python-based AI resume screening platform that helps recruiters analyze resumes against job descriptions using NLP and semantic similarity.

## Features

- Resume upload and PDF text extraction
- Resume matching with job descriptions
- Candidate match scores and skill analysis
- Candidate database management
- Job management
- Candidate comparison
- Resume quality analysis
- Preliminary bias audit
- Role-based interview questions
- Candidate data export

## Technologies Used

- Python
- Streamlit
- MySQL (TiDB Cloud)
- Pandas
- NumPy
- Sentence Transformers
- NLP
- PyPDF

## Installation

Install the required packages:

```bash
pip install -r requirements.txt
```

## Database Setup

1. Create a MySQL-compatible database named `talentiq`.
2. Configure database credentials in `.streamlit/secrets.toml`.
3. Create the required database tables.

## Run the Application

```bash
python -m streamlit run app.py
```

## Important Note

Match scores are screening indicators, not hiring probabilities. Bias Audit is preliminary and does not guarantee fairness. Final recruitment decisions require human review.

## Project Screenshots

### Recruitment Dashboard
![Recruitment Dashboard](Screenshot%202026-11-24%20140631.png)

### Resume Matcher
![Resume Matcher](Screenshot%202026-11-24%20140712.png)

### Candidate Management
![Candidate Management](Screenshot%202026-11-24%20140737.png)
