
import pandas as pd


def run_bias_audit(results):

    if results.empty:
        return pd.DataFrame(), "No candidates available."

    audit = results[
        [
            "Resume_Name",
            "Match_Percentage",
            "Skill_Coverage (%)"
        ]
    ].copy()

    audit.rename(
        columns={
            "Resume_Name": "Candidate",
            "Match_Percentage": "Text Similarity (%)"
        },
        inplace=True
    )

    score_range = (
        audit["Text Similarity (%)"].max()
        - audit["Text Similarity (%)"].min()
    )

    message = (
        f"Score range: {score_range:.2f} percentage points. "
        "This is a descriptive ranking audit only. "
        "It does not measure demographic fairness "
        "or prove the absence of discrimination."
    )

    return audit, message
