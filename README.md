# DEEPCEL

Proyecto Arduino/FPGA para Arduino MKR Vidor 4000 con captura de temperatura, humedad y luz, prediccion mediante red neuronal en FPGA y dashboard Python por puerto serie.

## Estructura del repositorio

| Carpeta | Contenido |
|---|---|
| `hardware/quartus/projects/ANeural_Network_power25_lowpower/` | Proyecto Quartus estable de temperatura. |
| `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/` | Proyecto Quartus multisensor Q4.4 temperatura+luz. |
| `hardware/quartus/constraints/` | Constraints originales de la MKR Vidor 4000. |
| `hardware/verilog_reference/common_rtl/` | RTL suelto historico/de referencia, no tratado como proyecto Quartus completo. |
| `software/arduino/Temperature_real_lowpower_hwtest/` | Sketch estable de temperatura/humedad. |
| `software/arduino/Temperature_light_i2c_q4_4_hwtest/` | Sketch multisensor I2C con prediccion de temperatura y luz. |
| `software/python/base_model/` | Scripts y modelo Python principales. |
| `software/python/Temperature_and_Light_Q4.4_ANN/` | Paquete original de entrenamiento multisensor; las plantillas Arduino/Quartus historicas se retiraron del arbol activo. |
| `serial_dashboard/` | App Python/web offline y puente opcional hacia ThingsBoard. |
| `docs/reports/` | Informes de Arduino, Quartus y estrategias de bajo consumo. |
| `docs/captures/quartus/` | Capturas usadas en informes de Quartus. |
| `docs/evidence/hardware_validation/` | Logs de compilacion, carga, serie y snapshots de reportes. |
| `tools/` | Scripts auxiliares y sketches de diagnostico, incluido un scanner I2C. |

## Variante actual recomendada

| Parte | Ruta |
|---|---|
| Sketch Arduino | `software/arduino/Temperature_light_i2c_q4_4_hwtest/` |
| Fichero `.ino` | `software/arduino/Temperature_light_i2c_q4_4_hwtest/Temperature_light_i2c_q4_4_hwtest.ino` |
| Proyecto Quartus | `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/` |
| Proyecto `.qpf` | `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/MKRVIDOR4000.qpf` |
| Bitstream Quartus | `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/output_files/MKRVIDOR4000.ttf` |
| Bitstream Arduino | `software/arduino/Temperature_light_i2c_q4_4_hwtest/FPGA_Bitstream.h` |

Sensores:

- DHT20 por I2C para temperatura y humedad.
- Sensor de luz digital I2C compatible en SDA/SCL. El firmware detecta TSL2561, BH1750 y VEML7700.
- Si el modulo fisico es `Grove - Light Sensor` a secas, Seeed lo documenta como analogico: debe ir a un pin analogico o a un ADC I2C externo. En SDA/SCL no aparece como dispositivo I2C.

Modelo:

- Red Q4.4 con 8 entradas: 4 muestras de temperatura y 4 muestras de luz.
- 8 neuronas ocultas ReLU.
- 2 salidas: prediccion de temperatura y prediccion de luz.
- La humedad se mide y se imprime, pero no entra en la red neuronal actual.

Variante de respaldo:

| Parte | Ruta |
|---|---|
| Sketch temperatura/humedad estable | `software/arduino/Temperature_real_lowpower_hwtest/` |
| Proyecto Quartus temperatura estable | `hardware/quartus/projects/ANeural_Network_power25_lowpower/` |

## Bajo consumo actual

La variante recomendada combina:

- red neuronal secuencial activa por rafaga cuando llega una muestra nueva;
- reloj de modelo a 1 MHz;
- top FPGA reducido con perifericos no usados sin actividad util;
- salida serie texto/CSV para el dashboard Python.

El sketch multisensor usa `FPGA.begin(32, 4)`: registros 0/1 para muestras Q4.4 de temperatura/luz y registros 2/3 como pulsos `ready`.

Power Analyzer estima `201.78 mW` para la FPGA en la variante ultralow multisensor. La confianza del analisis sigue siendo `Low` porque no se usa actividad real `.vcd`/`.saif`.

No se usa `ArduinoLowPower` en el sketch definitivo porque dio problemas de estabilidad con monitor serie. Las variantes anteriores quedan en el historial Git, no como proyectos activos dentro del arbol.

## Monitorizacion

La opcion principal es la app local en `http://localhost:8501`, que no necesita WiFi ni internet si se usa desde la propia Raspberry.

ThingsBoard queda como espejo opcional para demos con red: `serial_dashboard/deepcel_thingsboard_bridge.py` lee los eventos de la app local y publica telemetria en ThingsBoard sin abrir de nuevo el puerto serie.

## Documentacion principal

- `docs/CONTEXTO_AGENTES_DEEPCEL.md`
- `serial_dashboard/THINGSBOARD.md`
- `docs/reports/INFORME_QUARTUS_POTENCIA_DEEPCEL.md`
- `docs/reports/INFORME_ARDUINO_DEEPCEL.md`
- `docs/reports/ESTRATEGIAS_BAJO_CONSUMO_DEEPCEL.md`

## Notas

Las carpetas generadas pesadas de Quartus (`db`, `incremental_db`, `simulation`, `work`) no se versionan. Los `output_files` se mantienen porque incluyen reportes, bitstreams y resultados de validacion utiles para revisar el estado actual.
