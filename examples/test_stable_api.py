import axiombraid as AB

data = AB.read_csv("examples/students.csv")
result = AB.inspect(data)

print(AB.BRAND_NAME, AB.__version__, AB.API_STATUS)
print(result["data_quality"])
print(AB.self_check())
