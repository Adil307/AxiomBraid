# Command-Line Interface

```powershell
py -m axiombraid --version
py -m axiombraid inspect data.csv --confidence --quality-profile
py -m axiombraid inspect data.csv --format console --format json --format html --output reports/data
py -m axiombraid evaluate clean.csv --missing-rate 0.05 --duplicate-rate 0.05 --random-state 42 --output reports/evaluation
py -m axiombraid benchmark data.csv --repeats 3 --output reports/benchmark.json
py -m axiombraid benchmark data.csv --sizes 100,1000,5000 --repeats 2 --output reports/scaling.json
py -m axiombraid batch datasets --output reports --workers 4 --format json --format html
py -m axiombraid stream large.csv --chunksize 100000 --sample-rows 50000
py -m axiombraid cache-inspect data.csv
py -m axiombraid validate data.csv contract.json
py -m axiombraid fingerprint data.csv
py -m axiombraid init-config axiombraid.yaml
py -m axiombraid themes
```
