# Extended T=2010-2021 train/validation panel validation

**Extended train/validation panel validated; refit may use T=2010-2019 only.**

The canonical T=2022-2024 final-test row groups were inspected only as Parquet metadata and were never read. T=2010-2014 were newly derived in bounded spatial tiles; T=2015-2021 were copied exactly from the validated canonical panel.

- Grid cells: 89,112.
- Rows: 1,069,344.
- Newly derived years: [2010, 2011, 2012, 2013, 2014].
- Canonical regression rows: 623,784, all exact.
- Final-test rows read: 0.
- All five climate fields are complete after the accepted static nearest-valid-land fallback; no value was set to zero.
- ICNF uses the established derived-only `make_valid` policy and annual geometry unions before share intersection.

## Target by predictor year

| T | Outcome | Positive rows | Zero proportion | Mean burned share | Maximum |
|---:|---:|---:|---:|---:|---:|
| 2010 | 2011 | 5,743 | 0.935553 | 0.00902376 | 1.000000 |
| 2011 | 2012 | 5,715 | 0.935867 | 0.01274579 | 1.000000 |
| 2012 | 2013 | 5,916 | 0.933612 | 0.01668660 | 1.000000 |
| 2013 | 2014 | 1,721 | 0.980687 | 0.00205555 | 1.000000 |
| 2014 | 2015 | 3,146 | 0.964696 | 0.00629183 | 1.000000 |
| 2015 | 2016 | 5,773 | 0.935216 | 0.01753729 | 1.000000 |
| 2016 | 2017 | 12,122 | 0.863969 | 0.06286468 | 1.000000 |
| 2017 | 2018 | 1,447 | 0.983762 | 0.00448297 | 1.000000 |
| 2018 | 2019 | 3,004 | 0.966290 | 0.00450926 | 1.000000 |
| 2019 | 2020 | 3,294 | 0.963035 | 0.00743708 | 1.000000 |
| 2020 | 2021 | 1,919 | 0.978465 | 0.00307435 | 1.000000 |
| 2021 | 2022 | 4,318 | 0.951544 | 0.01217758 | 1.000000 |
