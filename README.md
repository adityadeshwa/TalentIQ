
# TalentIQ – AI Resume Screening Platform

TalentIQ is a Python-based resume screening platform that helps recruiters analyze resumes against job descriptions using NLP and semantic similarity.

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
- MySQL
- Pandas
- NumPy
- Sentence Transformers
- NLP
- PyPDF

## Installation

Install the required packages:

```bash
pip install streamlit pandas numpy mysql-connector-python sentence-transformers pypdf
```

## Database Setup

1. Start MySQL Server.
2. Create a database named `talentiq`.
3. Configure database credentials in `.streamlit/secrets.toml`.

## Run the Application

```bash
python -m streamlit run app.py
```

## Project Structure

```text
resume matcher/
│
├── app.py
├── matcher.py
├── README.md
└── .streamlit/
    └── secrets.toml
```

## Important Note

Match scores are screening indicators, not hiring probabilities. Final recruitment decisions require human review.
