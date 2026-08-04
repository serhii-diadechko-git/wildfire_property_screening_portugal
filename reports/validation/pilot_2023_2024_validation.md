# Corrected precipitation validation

```json
{
  "metadata": "tp has GRIB units m and stepType avgad; interpreted as m/day",
  "formula": "1000 \u00d7 (Jun\u00d730 + Jul\u00d731 + Aug\u00d731 + Sep\u00d730)",
  "before": {
    "count": 89112.0,
    "mean": 2.305187702178955,
    "std": 1.3558685779571533,
    "min": 0.0,
    "25%": 1.2323325872421265,
    "50%": 1.9356635808944702,
    "75%": 3.078806161880493,
    "max": 6.243119716644287
  },
  "after": {
    "count": 87606.0,
    "mean": 70.43172152963018,
    "std": 40.12601000990015,
    "min": 14.602719993945357,
    "25%": 37.75931728887372,
    "50%": 58.59478685215436,
    "75%": 92.92490538427955,
    "max": 188.15511910361238
  },
  "coastal_missing_count": 1506
}
```
