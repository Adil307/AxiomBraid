import pandas as pd

from axiombraid import DataGuide

df = pd.DataFrame({
    "Feature": [1, 2, 3, 4],
    "Passed": [0, 0, 1, 1],
    "Passed_Copy": [0, 0, 1, 1],
})
print(DataGuide(df).check_target_leakage("Passed"))
