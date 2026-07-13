import pandas as pd

from axiombraid import DataGuide


dataframe = pd.DataFrame({
    "Student_ID": [f"S{i:05d}" for i in range(1000)],
    "Marks": [i % 101 for i in range(1000)],
})

guide = DataGuide(dataframe)
sampled = guide.prepare_analysis(
    mode="sample",
    sample_rows=100,
    strategy="random",
    random_state=42,
)

result = sampled.inspect()
print(result["performance"])
print("Original rows:", len(guide.dataframe))
print("Analyzed rows:", len(sampled.dataframe))
