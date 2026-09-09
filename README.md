# DEEPCEL

Proyecto Arduino/FPGA para Arduino MKR Vidor 4000 con captura de temperatura, humedad y luz, y prediccion mediante red neuronal en FPGA.

## Estructura del repositorio

| Carpeta | Contenido |
|---|---|
| `hardware/quartus/projects/` | Proyectos Quartus separados, desde la base 25.1 funcional hasta la variante ultralow-power. |
| `hardware/quartus/constraints/` | Constraints originales de la MKR Vidor 4000. |
| `hardware/verilog_reference/common_rtl/` | RTL suelto historico/de referencia, no tratado como proyecto Quartus completo. |
| `software/arduino/` | Sketches Arduino completos. Cada sketch mantiene su carpeta propia para abrirlo desde Arduino IDE. |
| `software/python/base_model/` | Scripts y modelo Python principales. |
| `software/python/Temperature_and_Light_Q4.4_ANN/` | Paquete original de entrenamiento/template multisensor. |
| `docs/reports/` | Informes de Arduino, Quartus y estrategias de bajo consumo. |
| `docs/captures/quartus/` | Capturas usadas en informes de Quartus. |
| `docs/evidence/hardware_validation/` | Logs de compilacion, carga, serie y snapshots de reportes. |
| `tools/` | Scripts auxiliares para convertir bitstreams y capturar puerto serie. |

## Variante actual recomendada

| Parte | Ruta |
|---|---|
| Sketch Arduino | `software/arduino/Temperature_light_ultralowpower_seq_1mhz_samd_lowpower/` |
| Fichero `.ino` | `software/arduino/Temperature_light_ultralowpower_seq_1mhz_samd_lowpower/Temperature_light_ultralowpower_seq_1mhz_samd_lowpower.ino` |
| Proyecto Quartus | `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/` |
| Proyecto `.qpf` | `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/MKRVIDOR4000.qpf` |
| Bitstream Quartus | `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/output_files/MKRVIDOR4000.ttf` |
| Bitstream Arduino | `software/arduino/Temperature_light_ultralowpower_seq_1mhz_samd_lowpower/FPGA_Bitstream.h` |

Sensores:

- DHT20 por I2C para temperatura y humedad.
- Grove Light Sensor analogico en `A2`.

Modelo:

- Red Q4.4 con 8 entradas: 4 muestras de temperatura y 4 muestras de luz.
- 16 neuronas ocultas ReLU.
- 2 salidas: prediccion de temperatura y prediccion de luz.
- La humedad se mide y se imprime, pero no entra en la red neuronal actual.

## Bajo consumo actual

La variante recomendada combina:

- inferencia por rafaga solo al llegar un par completo temperatura/luz;
- red secuencial en FPGA a 1 MHz;
- puente JTAG mantenido a 120 MHz para conservar compatibilidad de carga;
- top FPGA reducido con perifericos no usados sin actividad util;
- `ArduinoLowPower` en el SAMD21 entre muestras.

Power Analyzer estima `201.78 mW` para la FPGA en la variante ultralow-power, frente a `234.21 mW` de la base 25.1. La confianza del analisis sigue siendo `Low` porque no se usa actividad real `.vcd`/`.saif`.

La carpeta `hardware/quartus/projects/ANeural_Network/` se conserva como historico/template. Para comparativas y trabajo activo, tomar como base funcional `hardware/quartus/projects/ANeural_Network_power25/`.

## Documentacion principal

- `docs/CONTEXTO_AGENTES_DEEPCEL.md`
- `docs/reports/INFORME_QUARTUS_POTENCIA_DEEPCEL.md`
- `docs/reports/INFORME_ARDUINO_DEEPCEL.md`
- `docs/reports/ESTRATEGIAS_BAJO_CONSUMO_DEEPCEL.md`

## Notas

Las carpetas generadas pesadas de Quartus (`db`, `incremental_db`, `simulation`, `work`) no se versionan. Los `output_files` se mantienen porque incluyen reportes, bitstreams y resultados de validacion utiles para revisar el estado actual.
