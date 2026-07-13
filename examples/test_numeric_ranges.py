import pandas as pd

from axiombraid import DataGuide


dataframe = pd.DataFrame({
    "Age": [18, 20, -5, 22],
    "Attendance": [90, 85, 110, 70],
    "Probability": [0.2, 0.8, 1.4, 0.6],
})

result = DataGuide(dataframe).inspect()
print(result["numeric_range_issues"])
