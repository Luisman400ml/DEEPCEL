# DEEPCEL Agent Context

Use `docs/CONTEXTO_AGENTES_DEEPCEL.md` as the main project context before making changes.

Current operative target:

- Board: Arduino MKR Vidor 4000.
- Stable firmware to use now: `software/arduino/Temperature_real_lowpower_hwtest/`.
- Stable hardware project: `hardware/quartus/projects/ANeural_Network_power25_lowpower/`.
- Sensors in the working setup: DHT20 on I2C SDA/SCL for temperature and humidity.
- Serial output: 9600 baud, CSV with `record,time_ms,temperature_c,humidity_rh_pct,prediction_c`.

Do not continue the light-sensor integration unless explicitly requested. The `Temperature_light_i2c_q4_4_hwtest` project is kept as multisensor work in progress, not as the current stable deployment. Do not use A2: the user's intended wiring is I2C on SDA/SCL.

Do not reintroduce `ArduinoLowPower` in the stable sketch unless the user asks for a new low-power experiment; it caused stability problems with serial monitoring and DHT20 recovery.
