# Contexto para agentes Codex sobre DEEPCEL

Este documento sirve para que Codex u otro agente retome el proyecto desde el repositorio sin reconstruir el contexto de la conversacion. Todas las rutas son relativas a la raiz del repo.

## Estado actual

- Remoto GitHub: `https://github.com/Luisman400ml/DEEPCEL`
- Rama principal de trabajo: `main`
- Plataforma hardware: Arduino MKR Vidor 4000
- FPGA: Cyclone 10 LP `10CL016YU256C8G`
- Herramientas usadas:
  - Quartus Prime Lite `25.1std.0 Build 1129`
  - Arduino core `arduino:samd` `1.8.14`
  - Arduino CLI `0.35.3`

La variante recomendada actual es `software/arduino/Temperature_light_i2c_q4_4_hwtest/`: temperatura y humedad con DHT20, luz por sensor digital I2C, inferencia de temperatura y luz en FPGA y salida serie CSV/texto para la app Python. Se conserva `software/arduino/Temperature_real_lowpower_hwtest/` como respaldo estable de temperatura/humedad.

## Estructura del repo

| Area | Ruta | Uso |
|---|---|---|
| Hardware Quartus temperatura | `hardware/quartus/projects/ANeural_Network_power25_lowpower/` | Proyecto estable de temperatura. |
| Hardware Quartus temperatura+luz | `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/` | Proyecto multisensor Q4.4 recomendado. |
| Constraints Vidor | `hardware/quartus/constraints/MKRVIDOR4000/` | Constraints originales recuperados de la MKR Vidor 4000. |
| RTL de referencia | `hardware/verilog_reference/common_rtl/` | HDL suelto historico; no asumir que es un proyecto Quartus completo. |
| Arduino temperatura | `software/arduino/Temperature_real_lowpower_hwtest/` | Sketch estable de respaldo, compatible con Arduino IDE y Arduino CLI. |
| Arduino temperatura+luz | `software/arduino/Temperature_light_i2c_q4_4_hwtest/` | Sketch recomendado para medir y predecir temperatura y luz. |
| Python/modelo | `software/python/base_model/` | Scripts y modelo Keras principales. |
| Paquete multisensor | `software/python/Temperature_and_Light_Q4.4_ANN/` | Paquete original de entrenamiento Q4.4 temperatura+luz. |
| Informes | `docs/reports/` | Informes de Arduino, Quartus y estrategias de consumo. |
| Evidencias | `docs/evidence/hardware_validation/` | Logs serie, compilacion, carga y snapshots. |
| Capturas | `docs/captures/quartus/` | Capturas usadas por informes. |
| Herramientas | `tools/` | Scripts PowerShell auxiliares y sketches de diagnostico. |

## Variante recomendada

| Parte | Ruta |
|---|---|
| Sketch Arduino actual | `software/arduino/Temperature_light_i2c_q4_4_hwtest/` |
| Fichero principal Arduino | `software/arduino/Temperature_light_i2c_q4_4_hwtest/Temperature_light_i2c_q4_4_hwtest.ino` |
| Proyecto Quartus actual | `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/` |
| Proyecto Quartus | `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/MKRVIDOR4000.qpf` |
| Top FPGA | `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/MKRVIDOR4000_top.v` |
| Red neuronal RTL | `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/eco_nn_top.v` |
| Bitstream Quartus TTF | `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/output_files/MKRVIDOR4000.ttf` |
| Bitstream Arduino generado | `software/arduino/Temperature_light_i2c_q4_4_hwtest/FPGA_Bitstream.h` |
| Reporte de potencia | `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/output_files/MKRVIDOR4000.pow.rpt` |

La variante de respaldo de temperatura es `software/arduino/Temperature_real_lowpower_hwtest/` junto a `hardware/quartus/projects/ANeural_Network_power25_lowpower/`. No usarla para validar prediccion de luz porque su red solo tiene una salida.

## Sensores y conexiones

| Sensor | Uso | Conexion esperada |
|---|---|---|
| DHT20 | Temperatura y humedad | I2C de la MKR Vidor, direccion habitual `0x38` |
| Sensor de luz I2C digital | Luz para entrada/salida de la red Q4.4 | SDA/SCL de la MKR Vidor, 3.3 V y GND |

El firmware detecta TSL2561, BH1750, VEML7700 y SI114x/SI1145 en `0x60`. El modulo `Grove - Light Sensor` sin la palabra `Digital` es analogico segun Seeed; conectado directamente a SDA/SCL no sirve como I2C. Para ese modulo hay que cablear `SIG` a un pin analogico o usar un ADC I2C externo.

Validacion en Raspberry Pi del 2026-09-10: la MKR vio por I2C `0x19`, `0x38`, `0x3C`, `0x6B` y `0x77`. No aparecieron `0x29`, `0x23`, `0x5C` ni `0x10`, por lo que el firmware marco la luz como `NO_SENSOR` y uso el fallback `595.66`. No tratar ese valor como medida real de luz.

## Modelo neuronal

- Formato numerico actual: Q4.4 de 8 bits normalizado.
- Entradas: 8 valores, `temperature_history[0..3]` y `light_history[0..3]`.
- Orden de entradas: cuatro temperaturas y cuatro muestras de luz, como en `fpga_selftest.h`.
- Capa oculta: 8 neuronas ReLU.
- Salidas:
  - `prediction_temperature_c`
  - `prediction_light_model`

La humedad se mantiene como medida auxiliar del DHT20. No mezclar formatos sin rehacer sketch, RTL, bitstream y selftest.

## Protocolo Arduino/FPGA

El sketch recomendado usa:

```cpp
FPGA.begin(32, 4)
```

Mapa de registros:

| Registro | Escritura desde Arduino | Lectura desde Arduino |
|---|---|---|
| `0` | Temperatura Q4.4 en bits bajos | Prediccion temperatura Q4.4 |
| `1` | Luz Q4.4 en bits bajos | Prediccion luz Q4.4 |
| `2` | Pulso `ready` temperatura, bit 0 | No usado como salida |
| `3` | Pulso `ready` luz, bit 0 | No usado como salida |

Arduino desplaza una ventana real de 4 muestras cada 10 s, escribe temperatura y luz, genera los pulsos `ready` y lee ambas predicciones. El selftest de `software/arduino/Temperature_light_i2c_q4_4_hwtest/fpga_selftest.h` valida 128 vectores y 512 lecturas.

## Bajo consumo aplicado

| Estrategia | Estado | Implementacion |
|---|---|---|
| Red activa por rafaga | Implementada | La inferencia se lanza cuando llega una nueva pareja temperatura/luz. |
| Red secuencial | Implementada | `eco_nn_top.v` reutiliza multiplicadores en una FSM en vez de mantener toda la red en paralelo. |
| Reloj NN 1 MHz | Implementada | PLL con dominio de modelo a 1 MHz. |
| Optimizacion Quartus | Implementada | Variante `ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz`. |
| Top minimo | Implementado | Perifericos no usados quedan sin actividad util o en tri-state. |
| Bajo consumo SAMD21 | No usar | No reintroducir `ArduinoLowPower`/`LowPower.idle(...)`; dio problemas de estabilidad con monitor serie. |

Power Analyzer vectorless:

| Variante activa | Potencia total | Core dinamica | Jerarquia `eco_nn_top:uut` |
|---|---:|---:|---:|
| Ultralow Q4.4 temperatura+luz 1 MHz | 201.78 mW | 12.61 mW | 0.06 mW |

La confianza de Power Analyzer es `Low` porque no hay actividad real `.vcd`/`.saif`. No presentar esas cifras como medida real de placa completa. Las comparativas historicas estan en `docs/reports/`.

## Validacion hardware mas reciente

Fecha: 2026-09-10.

| Comprobacion | Resultado |
|---|---|
| Carga Arduino en Raspberry | Correcta tras reset a bootloader por 1200 baudios. |
| Configuracion FPGA | `FPGA successfully configured!` |
| Selftest FPGA | `SELFTEST PASS multisensor_q4_4 vectors=128 reads=512 failures=0` |
| DHT20 | Detectado en `0x38`; 7 muestras CSV/texto validas en 90 s, con 1 error I2C aislado recuperado. |
| Sensor de luz I2C | No detectado; estado `NO_SENSOR sensor=none`. |
| Parser Python | 9 muestras parseadas del log de validacion, con historicos y prediccion de luz. |

La funcionalidad de red Q4.4 queda validada contra selftest. La medida real de luz queda pendiente de conectar un sensor de luz I2C soportado o un ADC I2C si se usa el Grove analogico.

## Salida serie esperada

Baudios: `9600`.

Arranque:

```text
FPGA successfully configured!
```

Modo texto normal:

```text
TemperatureHistory_C:[25.88,25.88,25.87,25.87]
LightHistory_value:[952.00,512.00,889.00,862.00]
Temperature_C:25.87
Light_value:862.00
PredictionTemperature_C:24.61
PredictionLight_model:380.00
LightStatus:OK sensor=TSL2561
DHTStatus:OK code=0 errors=0
Humidity_pct:53.98
```

Modo CSV para la app Python:

```text
record,time_ms,temperature_history_c,humidity_rh_pct,dht_status,dht_error_count,dht_last_status,light_history_value,prediction_temperature_c,prediction_light_model,temperature_q4_4,light_q4_4,prediction_temperature_q4_4,prediction_light_q4_4,light_status,light_sensor
DATA,12345,"[25.8700,25.8800,25.8900,25.9000]",53.9800,OK,0,0,"[742.00,750.00,760.00,755.00]",24.6100,380.0000,2,11,0,4,OK,TSL2561
```

Comandos serie:

| Comando | Efecto |
|---|---|
| `T` | Imprime build y ejecuta selftest FPGA. |
| `C` | Cambia a salida CSV. |
| `P` | Vuelve a salida texto normal. |
| `I` | Escanea el bus I2C y lista direcciones detectadas. |
| `R` | Reinicia la MKR con `NVIC_SystemReset()`. |

## Dependencias Arduino

| Libreria | Uso |
|---|---|
| `DHT20` | Temperatura y humedad por I2C. |
| `Wire` | Bus I2C desde core SAMD. |
| `SPI` | Soporte de plataforma desde core SAMD. |

Instalacion por Arduino CLI:

```powershell
& "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe" lib install "DHT20"
```

## Dependencias Python

Scripts principales en `software/python/base_model/`:

| Fichero | Funcion |
|---|---|
| `Data_Set_Generation.py` | Genera datos sinteticos de temperatura/luz y dataset de presentacion. |
| `neuron.py` | Entrena/carga el modelo Keras multisensor y exporta pesos/biases. |
| `model_multisensor_fpga.keras` | Modelo Keras guardado. |
| `params_neural_net.txt` | Pesos y bias exportados. |

Dependencias esperadas:

```text
numpy
pandas
matplotlib
tensorflow
scikit-learn
openpyxl
```

## Flujos de trabajo

Compilar Quartus recomendado:

```powershell
cd C:\Users\PC\OneDrive\Escritorio\DEEPCEL\hardware\quartus\projects\ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz
& 'C:\altera_lite\25.1std\quartus\bin64\quartus_sh.exe' --flow compile MKRVIDOR4000
& 'C:\altera_lite\25.1std\quartus\bin64\quartus_pow.exe' MKRVIDOR4000 -c MKRVIDOR4000
```

Regenerar bitstream Arduino:

```powershell
cd C:\Users\PC\OneDrive\Escritorio\DEEPCEL
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\Convert-VidorBitstream.ps1 -InputPath .\hardware\quartus\projects\ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz\output_files\MKRVIDOR4000.ttf -OutputPath .\software\arduino\Temperature_light_i2c_q4_4_hwtest\FPGA_Bitstream.h
```

Compilar y cargar Arduino:

```powershell
cd C:\Users\PC\OneDrive\Escritorio\DEEPCEL
& "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe" compile --fqbn arduino:samd:mkrvidor4000 .\software\arduino\Temperature_light_i2c_q4_4_hwtest
& "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe" upload -p COM4 --fqbn arduino:samd:mkrvidor4000 .\software\arduino\Temperature_light_i2c_q4_4_hwtest
```

Si `COM4` esta ocupado, normalmente hay un monitor serie abierto desde Arduino IDE o VS Code. Cerrar el monitor antes de subir.

## Monitorizacion

La app principal es local/offline y debe seguir funcionando sin WiFi:

```bash
cd /home/raspberrypi/Downloads/DEEPCEL
python3 serial_dashboard/deepcel_serial_dashboard.py --serial-port /dev/ttyACM0
```

Abrir en la propia Raspberry:

```text
http://localhost:8501
```

La web tiene dos acciones de recuperacion:

| Accion | Uso |
|---|---|
| `Reset Serial` | Cierra y reabre el puerto serie; no reinicia la MKR. |
| `Reset Board` | Envia `R` al firmware, el sketch ejecuta `NVIC_SystemReset()`, espera el reinicio y reabre el puerto. |

ThingsBoard es opcional y se ejecuta como espejo en una segunda terminal. No abre el puerto serie; lee los eventos SSE de la app local y publica por HTTP:

```bash
export DEEPCEL_TB_HOST="https://thingsboard.cloud"
export DEEPCEL_TB_TOKEN="TOKEN_DEL_DEVICE"
python3 serial_dashboard/deepcel_thingsboard_bridge.py
```

No guardar tokens reales en el repo. Si no hay red/token, dejar ThingsBoard desactivado y usar solo la app local.

## Herramientas auxiliares

| Fichero | Uso |
|---|---|
| `tools/Convert-VidorBitstream.ps1` | Convierte `MKRVIDOR4000.ttf` a `FPGA_Bitstream.h` invirtiendo bits dentro de cada byte. |
| `tools/Capture-VidorSerial.ps1` | Captura salida serie de la MKR Vidor para logs. |
| `tools/arduino/I2CScanner/` | Sketch minimo para listar direcciones I2C vistas por la MKR. |
| `serial_dashboard/deepcel_serial_dashboard.py` | Dashboard web local/offline sobre `localhost:8501`. |
| `serial_dashboard/deepcel_thingsboard_bridge.py` | Puente opcional desde el dashboard local hacia ThingsBoard. |
| `serial_dashboard/THINGSBOARD.md` | Guia de telemetria y widgets recomendados para ThingsBoard. |

## Reglas practicas para agentes

- Trabajar por defecto sobre `software/arduino/Temperature_light_i2c_q4_4_hwtest/`; es el proyecto recomendado actual.
- Trabajar en `main`; no usar `t1` como rama de desarrollo.
- Conservar `Temperature_real_lowpower_hwtest` como respaldo estable de temperatura/humedad.
- No eliminar humedad: debe seguir midiendose e imprimiendose.
- No cambiar `FPGA.begin(32, 4)` sin cambiar tambien top Quartus, sketch y selftest.
- No reintroducir `ArduinoLowPower`/`LowPower.idle(...)` en el sketch definitivo.
- No hacer depender la app local de ThingsBoard ni de WiFi; ThingsBoard debe ser opcional.
- No hardcodear tokens de ThingsBoard; usar variables de entorno.
- No tratar los mW de Quartus como medida real de la placa completa.
- No modificar el formato Q4.4 sin revalidar contra referencia software.
- No borrar `output_files/` de la variante definitiva: contienen reportes y bitstream reproducibles.
