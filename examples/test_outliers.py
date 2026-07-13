import pandas as pd

from axiombraid import DataGuide


dataframe = pd.DataFrame({
    "Study_Hours": [2, 3, 3, 4, 4, 5, 5, 50],
    "Marks": [60, 65, 70, 75, 80, 85, 90, 95],
})

result = DataGuide(dataframe).inspect()
print(result["outliers"])
