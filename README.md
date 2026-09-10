# DEEPCEL

Proyecto Arduino/FPGA para Arduino MKR Vidor 4000 con captura de temperatura y humedad, prediccion de temperatura mediante red neuronal en FPGA y dashboard Python por puerto serie.

## Estructura del repositorio

| Carpeta | Contenido |
|---|---|
| `hardware/quartus/projects/ANeural_Network_power25_lowpower/` | Unico proyecto Quartus activo. |
| `hardware/quartus/constraints/` | Constraints originales de la MKR Vidor 4000. |
| `hardware/verilog_reference/common_rtl/` | RTL suelto historico/de referencia, no tratado como proyecto Quartus completo. |
| `software/arduino/Temperature_real_lowpower_hwtest/` | Unico sketch Arduino activo, listo para Arduino IDE/CLI. |
| `software/python/base_model/` | Scripts y modelo Python principales. |
| `software/python/Temperature_and_Light_Q4.4_ANN/` | Paquete original de entrenamiento multisensor; las plantillas Arduino/Quartus historicas se retiraron del arbol activo. |
| `serial_dashboard/` | App Python/web para visualizar los datos recibidos por serie. |
| `docs/reports/` | Informes de Arduino, Quartus y estrategias de bajo consumo. |
| `docs/captures/quartus/` | Capturas usadas en informes de Quartus. |
| `docs/evidence/hardware_validation/` | Logs de compilacion, carga, serie y snapshots de reportes. |
| `tools/` | Scripts auxiliares para convertir bitstreams y capturar puerto serie. |

## Variante actual recomendada

| Parte | Ruta |
|---|---|
| Sketch Arduino | `software/arduino/Temperature_real_lowpower_hwtest/` |
| Fichero `.ino` | `software/arduino/Temperature_real_lowpower_hwtest/Temperature_real_lowpower_hwtest.ino` |
| Proyecto Quartus | `hardware/quartus/projects/ANeural_Network_power25_lowpower/` |
| Proyecto `.qpf` | `hardware/quartus/projects/ANeural_Network_power25_lowpower/MKRVIDOR4000.qpf` |
| Bitstream Quartus | `hardware/quartus/projects/ANeural_Network_power25_lowpower/output_files/MKRVIDOR4000.ttf` |
| Bitstream Arduino | `software/arduino/Temperature_real_lowpower_hwtest/FPGA_Bitstream.h` |

Sensores:

- DHT20 por I2C para temperatura y humedad.

Modelo:

- Red Q8.8 con 4 entradas: historial temporal de temperatura.
- 8 neuronas ocultas ReLU.
- 1 salida: prediccion de temperatura.
- La humedad se mide y se imprime, pero no entra en la red neuronal actual.

## Bajo consumo actual

La variante recomendada combina:

- inferencia solo cuando llega una nueva lectura de temperatura;
- proyecto Quartus lowpower a 24 MHz;
- top FPGA reducido con perifericos no usados sin actividad util;
- salida serie texto/CSV para el dashboard Python.

Power Analyzer estima `212.53 mW` para la FPGA en la variante activa. La confianza del analisis sigue siendo `Low` porque no se usa actividad real `.vcd`/`.saif`.

No se usa `ArduinoLowPower` en el sketch definitivo porque dio problemas de estabilidad con monitor serie. Las variantes anteriores quedan en el historial Git, no como proyectos activos dentro del arbol.

## Documentacion principal

- `docs/CONTEXTO_AGENTES_DEEPCEL.md`
- `docs/reports/INFORME_QUARTUS_POTENCIA_DEEPCEL.md`
- `docs/reports/INFORME_ARDUINO_DEEPCEL.md`
- `docs/reports/ESTRATEGIAS_BAJO_CONSUMO_DEEPCEL.md`

## Notas

Las carpetas generadas pesadas de Quartus (`db`, `incremental_db`, `simulation`, `work`) no se versionan. Los `output_files` se mantienen porque incluyen reportes, bitstreams y resultados de validacion utiles para revisar el estado actual.
