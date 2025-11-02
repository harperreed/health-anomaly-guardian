# JSON Output Mode

The sleep anomaly detector now supports JSON output for programmatic consumption.

## Usage

Add the `--json` flag to output results in JSON format instead of rich console tables:

```bash
uv run main.py --json
```

## JSON Output Structure

The JSON output includes:

### Summary
- **device_id**: Device identifier
- **device_name**: Human-readable device name
- **date_range**: Start date, end date, and total days analyzed
- **statistics**: Mean, std, min, max for HR, RR, sleep_duration, and sleep_score

### Outliers
- **total_count**: Total number of anomalies detected
- **recent**: Array of the N most recent outliers (default 5), each containing:
  - date
  - anomaly_score
  - hr (heart rate)
  - rr (respiratory rate)
  - sleep_duration
  - sleep_score

### Latest Day
- **date**: Date of the most recent analysis
- **is_anomaly**: Boolean indicating if latest day is anomalous
- **anomaly_score**: IsolationForest decision function score
- **hr, rr, sleep_duration, sleep_score**: Metrics for the latest day
- **gpt_analysis** (optional): GPT analysis if anomaly detected and OpenAI configured

## Example JSON Output

```json
{
  "summary": {
    "device_id": "device_123",
    "device_name": "Main Sensor",
    "date_range": {
      "start": "2025-08-03",
      "end": "2025-11-01",
      "total_days": 90
    },
    "statistics": {
      "hr": {
        "mean": 58.5,
        "std": 3.2,
        "min": 52.0,
        "max": 68.0
      },
      "rr": {
        "mean": 14.2,
        "std": 1.5,
        "min": 11.5,
        "max": 17.8
      },
      "sleep_duration": {
        "mean": 420.5,
        "std": 45.2,
        "min": 320.0,
        "max": 540.0
      },
      "sleep_score": {
        "mean": 75.3,
        "std": 8.1,
        "min": 55.0,
        "max": 95.0
      }
    }
  },
  "outliers": {
    "total_count": 5,
    "recent": [
      {
        "date": "2025-10-28",
        "anomaly_score": -0.12,
        "hr": 65.0,
        "rr": 16.5,
        "sleep_duration": 350.0,
        "sleep_score": 62.0
      }
    ]
  },
  "latest_day": {
    "date": "2025-11-01",
    "is_anomaly": false,
    "anomaly_score": 0.08,
    "hr": 57.0,
    "rr": 14.0,
    "sleep_duration": 425.0,
    "sleep_score": 78.0
  }
}
```

## Use Cases

1. **Integration with other tools**: Pipe JSON output to `jq` or other JSON processors
2. **Automated monitoring**: Parse JSON in scripts for alerting systems
3. **Data visualization**: Feed JSON into dashboards or charting tools
4. **API integration**: Use as data source for web services

## Example with jq

```bash
# Get just the latest day's anomaly status
uv run main.py --json | jq '.latest_day.is_anomaly'

# Extract all outlier dates
uv run main.py --json | jq '.outliers.recent[].date'

# Get summary statistics for heart rate
uv run main.py --json | jq '.summary.statistics.hr'
```

## Notes

- In JSON mode, all rich console output is suppressed
- Errors are still output in JSON format
- Push notifications (if --alert is used) still work in JSON mode
- GPT analysis is included automatically if the latest day is an anomaly
