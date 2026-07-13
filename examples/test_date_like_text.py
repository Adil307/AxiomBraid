import pandas as pd

from axiombraid import DataGuide


dataframe = pd.DataFrame({
    "Enrollment_Date": [
        "2024-01-10",
        "2024/02/15",
        "15 March 2024",
        "2024-04-20",
    ],
    "Department": ["CS", "Math", "CS", "Math"],
})

result = DataGuide(dataframe).inspect()
print(result["date_like_text_columns"])
