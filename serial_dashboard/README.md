# DEEPCEL Serial Dashboard

Lightweight Python app for live visualization of telemetry sent by the MKR Vidor 4000.

The supported project is `software/arduino/Temperature_light_i2c_q4_4_hwtest`.

The app opens the serial port, sends the `C` command to the sketch to enable CSV output, plots measured temperature, FPGA temperature prediction, humidity, measured light, FPGA light prediction, and stores a local CSV capture.

ThingsBoard support is optional and runs as a separate bridge so the offline dashboard can keep owning the serial port.

## Run On The Raspberry

Local window on the Raspberry display:

```bash
cd /home/raspberrypi/Downloads/DEEPCEL
python3 serial_dashboard/deepcel_tk_plotter.py --serial-port /dev/ttyACM0
```

Local web dashboard:

```bash
cd /home/raspberrypi/Downloads/DEEPCEL
python3 serial_dashboard/deepcel_serial_dashboard.py --serial-port /dev/ttyACM0
```

Then open:

```text
http://localhost:8501
```

From another device on the same network, use the Raspberry Pi IP address and port `8501`.

If the board changes port after a USB reset, the app waits and scans the available serial ports again.

Use the `Reset Serial` button if the MKR is unplugged, reconnects on a new USB device, or stops streaming. The button closes the current serial handle, scans/opens the port again, and sends `C` to restore CSV mode.

## Dependencies

```bash
python3 -m pip install -r serial_dashboard/requirements.txt
```

On the Raspberry Pi used for this project, `pyserial` was already installed.

## Data Read

- `temperature_c`
- `humidity_pct`
- `light_adc`
- `prediction_temperature_c`
- `prediction_light_model`
- `temperature_history_c`
- `light_history_adc`
- `light_status`
- `light_sensor`

The definitive sketch emits:

```text
record,time_ms,temperature_history_c,humidity_rh_pct,light_history_value,prediction_temperature_c,prediction_light_model,temperature_q4_4,light_q4_4,prediction_temperature_q4_4,prediction_light_q4_4,light_status,light_sensor
DATA,12345,"[25.1200,25.1300,25.1400,25.1500]",53.5000,"[742.00,750.00,755.00,760.00]",24.7500,380.0000,2,11,0,4,OK,TSL2561
```

Logs are stored in `serial_dashboard/logs/`.

## Optional ThingsBoard Mirror

Keep the local dashboard running, then start the bridge from a second terminal:

```bash
export DEEPCEL_TB_HOST="https://thingsboard.cloud"
export DEEPCEL_TB_TOKEN="PASTE_DEVICE_ACCESS_TOKEN_HERE"
python3 serial_dashboard/deepcel_thingsboard_bridge.py
```

The bridge reads live samples from `http://127.0.0.1:8501/events` and publishes temperature, humidity, measured light, FPGA predictions, Q4.4 values, `device_time_ms`, and `sequence` to ThingsBoard.

See `serial_dashboard/THINGSBOARD.md` for the ThingsBoard dashboard layout and dry-run commands.
