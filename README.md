# DEEPCEL

Proyecto Arduino/FPGA para Arduino MKR Vidor 4000. El estado operativo actual usa DHT20 por I2C para temperatura/humedad y una red neuronal en FPGA para prediccion de temperatura. La integracion temperatura+luz queda conservada en el repo como trabajo en curso.

## Estructura del repositorio

| Carpeta | Contenido |
|---|---|
| `hardware/quartus/projects/ANeural_Network_power25_lowpower/` | Proyecto Quartus estable de temperatura. |
| `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/` | Proyecto Quartus multisensor Q4.4 temperatura+luz. |
| `hardware/quartus/constraints/` | Constraints originales de la MKR Vidor 4000. |
| `hardware/verilog_reference/common_rtl/` | RTL suelto historico/de referencia, no tratado como proyecto Quartus completo. |
| `software/arduino/Temperature_real_lowpower_hwtest/` | Sketch estable actual de temperatura/humedad. |
| `software/arduino/Temperature_light_i2c_q4_4_hwtest/` | Sketch multisensor I2C con prediccion de temperatura y luz; no es la version estable actual. |
| `software/python/base_model/` | Scripts y modelo Python principales. |
| `software/python/Temperature_and_Light_Q4.4_ANN/` | Paquete original de entrenamiento multisensor; las plantillas Arduino/Quartus historicas se retiraron del arbol activo. |
| `serial_dashboard/` | App Python/web offline y puente opcional hacia ThingsBoard. |
| `docs/reports/` | Informes de Arduino, Quartus y estrategias de bajo consumo. |
| `docs/captures/quartus/` | Capturas usadas en informes de Quartus. |
| `docs/evidence/hardware_validation/` | Logs de compilacion, carga, serie y snapshots de reportes. |
| `tools/` | Scripts auxiliares y sketches de diagnostico, incluido un scanner I2C. |

## Variante operativa actual

| Parte | Ruta |
|---|---|
| Sketch Arduino estable | `software/arduino/Temperature_real_lowpower_hwtest/` |
| Fichero `.ino` | `software/arduino/Temperature_real_lowpower_hwtest/Temperature_real_lowpower_hwtest.ino` |
| Proyecto Quartus estable | `hardware/quartus/projects/ANeural_Network_power25_lowpower/` |
| Proyecto `.qpf` | `hardware/quartus/projects/ANeural_Network_power25_lowpower/MKRVIDOR4000.qpf` |
| Bitstream Arduino | `software/arduino/Temperature_real_lowpower_hwtest/FPGA_Bitstream.h` |

Sensores:

- DHT20 por I2C para temperatura y humedad.
- No usar A2 en la version actual. El cableado objetivo del usuario es SDA/SCL.

Validacion hardware local del 2026-09-10: la MKR carga `Temperature_real_lowpower_hwtest`, configura la FPGA, imprime `FPGA successfully configured!`, pasa `SELFTEST PASS vectors=128 reads=256 failures=0` y emite filas `DATA` con temperatura, humedad y prediccion. Se observaron avisos I2C puntuales del DHT20, pero el firmware siguio entregando muestras validas.

Modelo:

- Red estable de temperatura con 4 muestras historicas.
- Salida: prediccion de temperatura.
- La humedad se mide y se imprime, pero no entra en la red neuronal estable.

Variante multisensor no estable:

| Parte | Ruta |
|---|---|
| Sketch temperatura+luz | `software/arduino/Temperature_light_i2c_q4_4_hwtest/` |
| Proyecto Quartus temperatura+luz | `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/` |

El escaneo I2C de pruebas vio `0x38`, `0x3C`, `0x60`, `0x6B` y a veces `0x77`, pero no quedo validada una lectura real y estable de luz. No tratar esa variante como lista para despliegue.

## Bajo consumo actual

La variante multisensor de bajo consumo queda conservada para trabajo posterior y combina:

- red neuronal secuencial activa por rafaga cuando llega una muestra nueva;
- reloj de modelo a 1 MHz;
- top FPGA reducido con perifericos no usados sin actividad util;
- salida serie texto/CSV para el dashboard Python.

El sketch estable actual usa la interfaz de temperatura incluida en `Temperature_real_lowpower_hwtest`. El sketch multisensor usa `FPGA.begin(32, 4)`: registros 0/1 para muestras Q4.4 de temperatura/luz y registros 2/3 como pulsos `ready`.

Power Analyzer estima `201.78 mW` para la FPGA en la variante ultralow multisensor. La confianza del analisis sigue siendo `Low` porque no se usa actividad real `.vcd`/`.saif`.

No se usa `ArduinoLowPower` en el sketch definitivo porque dio problemas de estabilidad con monitor serie. Las variantes anteriores quedan en el historial Git, no como proyectos activos dentro del arbol.

## Monitorizacion

La opcion principal es la app local en `http://localhost:8501`, que no necesita WiFi ni internet si se usa desde la propia Raspberry.

La app web puede usarse para monitorizacion por puerto serie. En el estado estable actual deben esperarse temperatura, humedad y prediccion de temperatura. Incluye `Reset Serial`; `Reset Board` depende de que el sketch cargado implemente el comando serie `R`.

ThingsBoard queda como espejo opcional para demos con red: `serial_dashboard/deepcel_thingsboard_bridge.py` lee los eventos de la app local y publica telemetria en ThingsBoard sin abrir de nuevo el puerto serie.

## Documentacion principal

- `docs/CONTEXTO_AGENTES_DEEPCEL.md`
- `serial_dashboard/THINGSBOARD.md`
- `docs/reports/INFORME_QUARTUS_POTENCIA_DEEPCEL.md`
- `docs/reports/INFORME_ARDUINO_DEEPCEL.md`
- `docs/reports/ESTRATEGIAS_BAJO_CONSUMO_DEEPCEL.md`

## Notas

Las carpetas generadas pesadas de Quartus (`db`, `incremental_db`, `simulation`, `work`) no se versionan. Los `output_files` se mantienen porque incluyen reportes, bitstreams y resultados de validacion utiles para revisar el estado actual.
