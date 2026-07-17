import axiombraid as AB


df = AB.read_csv("students.csv")

result = AB.inspect(
    df,
    include_confidence=True,
)

print("AxiomBraid version:", AB.__version__)
print("Confidence summary:", result["confidence_summary"])

for issue in result["issues"]:
    confidence = issue["confidence"]
    print("\nIssue:", issue["code"])
    print("Severity:", issue["severity"])
    print("Confidence score:", confidence["score"])
    print("Confidence level:", confidence["level"])
    print("Method:", confidence["method"])
    print("Evidence:", confidence["evidence"])
