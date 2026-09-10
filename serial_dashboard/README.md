# DEEPCEL Serial Dashboard

Lightweight Python app for live visualization of telemetry sent by the MKR Vidor 4000.

The supported project is `software/arduino/Temperature_real_lowpower_hwtest`.

The app opens the serial port, sends the `C` command to the sketch to enable CSV output, plots measured temperature, FPGA temperature prediction, humidity, Grove light ADC, and stores a local CSV capture.

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

The definitive sketch emits:

```text
record,time_ms,temperature_c,humidity_rh_pct,light_adc,prediction_temperature_c
DATA,12345,25.1250,53.5000,742,24.7500
```

Logs are stored in `serial_dashboard/logs/`.
