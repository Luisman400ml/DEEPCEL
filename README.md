# DEEPCEL

Proyecto Arduino/FPGA para Arduino MKR Vidor 4000 con captura de temperatura, humedad y luz, y prediccion mediante red neuronal en FPGA.

## Variante actual recomendada

- Sketch Arduino: `Temperature_light_lowpower_hwtest_lowfreq/`
- Proyecto Quartus: `QuartusProject/ANeural_Network_power25_lowpower_light_q4_4_lowfreq_6mhz/`
- Sensor DHT20: temperatura y humedad por I2C
- Grove Light Sensor: entrada analogica `A2`
- Red neuronal: Q4.4, 8 entradas, 16 neuronas ocultas, 2 salidas
- Bajo consumo: modo rafaga y reloj de red neuronal a 6 MHz

## Documentacion

- `ESTRATEGIAS_BAJO_CONSUMO_DEEPCEL.md`
- `INFORME_QUARTUS_POTENCIA_DEEPCEL.md`
- `INFORME_ARDUINO_DEEPCEL.md`

## Notas

Las carpetas generadas pesadas de Quartus (`db`, `incremental_db`, `simulation`, `work`) no se versionan. Los `output_files` se mantienen porque incluyen reportes, bitstreams y resultados de validacion utiles para revisar el estado actual.
