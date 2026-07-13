import axiombraid as AB

result = AB.inspect("examples/students.csv")
print("Quality score:", result["data_quality"]["score"])
cleaned = AB.clean("examples/students.csv")
print("Cleaned rows:", len(cleaned))
