# DEEPCEL ThingsBoard Bridge

The local web dashboard remains the primary offline monitor. ThingsBoard is an
optional mirror for networked demos and longer-term dashboards.

Data path:

```text
MKR Vidor -> USB serial -> local dashboard (:8501) -> ThingsBoard bridge -> ThingsBoard
```

The bridge uses the official ThingsBoard HTTP telemetry endpoint:

```text
POST http(s)://THINGSBOARD_HOST/api/v1/$ACCESS_TOKEN/telemetry
```

## Telemetry Keys

The bridge publishes only values produced by the definitive sketch:

| Key | Meaning |
|---|---|
| `temperature_c` | DHT20 measured temperature |
| `humidity_pct` | DHT20 measured relative humidity |
| `prediction_temperature_c` | FPGA temperature prediction |
| `device_time_ms` | MKR timestamp |
| `sequence` | Local sample counter |

Power keys such as `power_mw`, `current_ma`, or `voltage_v` are intentionally
not sent yet because the current hardware does not measure consumption.

## Run

First keep the local dashboard running:

```bash
cd /home/raspberrypi/Downloads/DEEPCEL
python3 serial_dashboard/deepcel_serial_dashboard.py --serial-port /dev/ttyACM0
```

Create a ThingsBoard device, copy its access token, and run the bridge in a
second terminal:

```bash
cd /home/raspberrypi/Downloads/DEEPCEL
export DEEPCEL_TB_HOST="https://thingsboard.cloud"
export DEEPCEL_TB_TOKEN="PASTE_DEVICE_ACCESS_TOKEN_HERE"
python3 serial_dashboard/deepcel_thingsboard_bridge.py
```

For a local ThingsBoard server, use:

```bash
export DEEPCEL_TB_HOST="http://localhost:8080"
```

Do not commit real access tokens. Prefer environment variables over command-line
tokens so they do not appear in shell history.

## Dry Run

Use dry-run mode to verify the payloads without sending anything:

```bash
python3 serial_dashboard/deepcel_thingsboard_bridge.py --dry-run --max-samples 3
```

Replay an existing local CSV log:

```bash
python3 serial_dashboard/deepcel_thingsboard_bridge.py --dry-run \
  --replay-csv serial_dashboard/logs/deepcel_YYYYMMDD_HHMMSS.csv \
  --max-samples 3
```

## Dashboard Layout In ThingsBoard

Suggested dashboard name:

```text
DEEPCEL Monitoring
```

Recommended widgets:

| Widget | Data keys |
|---|---|
| Time-series line chart | `temperature_c`, `prediction_temperature_c` |
| Time-series line chart or gauge | `humidity_pct` |
| Latest values card/table | `temperature_c`, `prediction_temperature_c`, `humidity_pct`, `device_time_ms` |

Use a live time window such as last 10 or 30 minutes during lab demos.
