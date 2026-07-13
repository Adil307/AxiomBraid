import axiombraid as AB

result = AB.stream_csv("examples/students.csv", chunksize=3, sample_rows=5)
print(result["streaming"])
