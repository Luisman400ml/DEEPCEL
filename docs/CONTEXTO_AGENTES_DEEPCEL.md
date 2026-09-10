# Contexto para agentes Codex sobre DEEPCEL

Este documento sirve para que Codex u otro agente retome el proyecto desde el repositorio sin reconstruir el contexto de la conversacion. Todas las rutas son relativas a la raiz del repo.

## Estado operativo actual

Fecha de contexto: 2026-09-10.

- Remoto GitHub: `https://github.com/Luisman400ml/DEEPCEL`
- Rama principal de trabajo: `main`
- Plataforma hardware: Arduino MKR Vidor 4000
- FPGA: Cyclone 10 LP `10CL016YU256C8G`
- Firmware estable actual: `software/arduino/Temperature_real_lowpower_hwtest/`
- Proyecto Quartus estable actual: `hardware/quartus/projects/ANeural_Network_power25_lowpower/`
- Sensor usado en la version estable: DHT20 por I2C en SDA/SCL, direccion habitual `0x38`
- Salida serie estable: `9600` baudios

La version que debe usar un agente ahora es la de temperatura/humedad. La integracion temperatura+luz queda en el repo como trabajo en curso, pero no es la version estable que hay que desplegar o depurar salvo peticion explicita.

## Reglas inmediatas para agentes

- Trabajar por defecto sobre `software/arduino/Temperature_real_lowpower_hwtest/`.
- No usar `software/arduino/Temperature_light_i2c_q4_4_hwtest/` como firmware estable.
- No usar A2: el usuario indico que no va a conectar nada en A2 y que el cableado previsto es SDA/SCL.
- No reintroducir `ArduinoLowPower`/`LowPower.idle(...)` en la version estable; dio problemas de estabilidad con monitor serie y recuperacion DHT20.
- No eliminar la humedad: debe seguir midiendose e imprimiendose.
- Trabajar en `main`; no usar `t1` como rama principal.
- No tratar los mW de Quartus como medida real de placa completa.
- No hardcodear tokens de ThingsBoard.

## Estructura del repo

| Area | Ruta | Uso |
|---|---|---|
| Hardware Quartus temperatura | `hardware/quartus/projects/ANeural_Network_power25_lowpower/` | Proyecto estable actual de temperatura. |
| Hardware Quartus temperatura+luz | `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/` | Proyecto multisensor Q4.4 pendiente/no estable. |
| Constraints Vidor | `hardware/quartus/constraints/MKRVIDOR4000/` | Constraints originales recuperados de la MKR Vidor 4000. |
| RTL de referencia | `hardware/verilog_reference/common_rtl/` | HDL suelto historico; no asumir que es un proyecto Quartus completo. |
| Arduino temperatura | `software/arduino/Temperature_real_lowpower_hwtest/` | Sketch estable actual, compatible con Arduino IDE y Arduino CLI. |
| Arduino temperatura+luz | `software/arduino/Temperature_light_i2c_q4_4_hwtest/` | Sketch multisensor I2C en trabajo pendiente. |
| Python/modelo | `software/python/base_model/` | Scripts y modelo Keras principales. |
| Paquete multisensor | `software/python/Temperature_and_Light_Q4.4_ANN/` | Paquete original de entrenamiento Q4.4 temperatura+luz. |
| Informes | `docs/reports/` | Informes de Arduino, Quartus y estrategias de consumo. |
| Evidencias | `docs/evidence/hardware_validation/` | Logs serie, compilacion, carga y snapshots. |
| Capturas | `docs/captures/quartus/` | Capturas usadas por informes. |
| Herramientas | `tools/` | Scripts PowerShell auxiliares y sketches de diagnostico. |
| Dashboard | `serial_dashboard/` | App local y puente opcional ThingsBoard. |

## Variante estable actual

| Parte | Ruta |
|---|---|
| Sketch Arduino | `software/arduino/Temperature_real_lowpower_hwtest/` |
| Fichero principal Arduino | `software/arduino/Temperature_real_lowpower_hwtest/Temperature_real_lowpower_hwtest.ino` |
| Proyecto Quartus | `hardware/quartus/projects/ANeural_Network_power25_lowpower/` |
| Proyecto Quartus `.qpf` | `hardware/quartus/projects/ANeural_Network_power25_lowpower/MKRVIDOR4000.qpf` |
| Top FPGA | `hardware/quartus/projects/ANeural_Network_power25_lowpower/MKRVIDOR4000_top.v` |
| Bitstream Arduino embebido | `software/arduino/Temperature_real_lowpower_hwtest/FPGA_Bitstream.h` |
| Selftest Arduino/FPGA | `software/arduino/Temperature_real_lowpower_hwtest/fpga_selftest.h` |

El sketch estable usa:

```cpp
FPGA.begin(32, 2)
```

Mapa de registros estable:

| Registro | Escritura desde Arduino | Lectura desde Arduino |
|---|---|---|
| `0` | Temperatura Q8.8 en bits bajos | Prediccion temperatura Q8.8 |
| `1` | Pulso `ready` temperatura | No usado como salida |

El intervalo de muestreo estable es `10000 ms`. Si hay error puntual de DHT20, el sketch imprime el error y reintenta con intervalo corto de `2000 ms`.

## Salida serie estable

Baudios: `9600`.

Arranque esperado:

```text
FPGA successfully configured!
```

El mensaje `ERROR: DHT20 not found on I2C address 0x38.` puede aparecer en `setup()` aunque despues haya lecturas validas. No debe tratarse como fallo fatal si a continuacion aparecen filas `DATA` o lecturas de temperatura/humedad.

Modo texto:

```text
Temperatura_C:24.81    Prediccion_C:24.55    Humedad_pct:55.11
```

Modo CSV, activado enviando `C` por serie:

```text
record,time_ms,temperature_c,humidity_rh_pct,prediction_c
DATA,76350,24.8058,55.1096,24.5469
```

Comandos serie de la version estable:

| Comando | Efecto |
|---|---|
| `C` | Cambia a salida CSV. |
| `P` | Vuelve a salida texto normal. |
| `T` | Imprime build y ejecuta selftest FPGA. |

La version estable no implementa comando `R`. Si una app muestra `Reset Board`, comprobar antes si usa reset por puerto/bootloader o si espera el comando `R`.

## Validacion mas reciente

Validacion local en Windows, 2026-09-10:

| Comprobacion | Resultado |
|---|---|
| Compilacion Arduino | Correcta para `arduino:samd:mkrvidor4000`. |
| Carga en MKR | Correcta desde `COM4`, con bootloader temporal en `COM6`. |
| Configuracion FPGA | `FPGA successfully configured!` |
| Selftest FPGA | `SELFTEST PASS vectors=128 reads=256 failures=0` |
| Datos DHT20 | Filas `DATA` con temperatura ~24.8 C y humedad ~55 %. |
| Estabilidad | Hubo avisos I2C puntuales del DHT20, pero el firmware siguio entregando muestras validas. |

Estado de repo en Raspberry antes de esta actualizacion: `/home/raspberrypi/Downloads/DEEPCEL`, rama `main`, limpio contra `origin/main`. Despues de actualizar este documento, hacer `git pull --ff-only` en esa ruta.

## Flujo en Raspberry Pi

Actualizar repo:

```bash
cd /home/raspberrypi/Downloads/DEEPCEL
git pull --ff-only
git status --short --branch
```

Compilar firmware estable:

```bash
cd /home/raspberrypi/Downloads/DEEPCEL
arduino-cli compile --fqbn arduino:samd:mkrvidor4000 software/arduino/Temperature_real_lowpower_hwtest
```

Cargar firmware estable, ajustando el puerto si no es `/dev/ttyACM0`:

```bash
arduino-cli board list
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:samd:mkrvidor4000 software/arduino/Temperature_real_lowpower_hwtest
```

Monitorizar:

```bash
python3 -m serial.tools.miniterm /dev/ttyACM0 9600
```

Para activar CSV desde el monitor, enviar `C`. Para ejecutar selftest, enviar `T`.

## Dashboard y ThingsBoard

La app principal es local/offline:

```bash
cd /home/raspberrypi/Downloads/DEEPCEL
python3 serial_dashboard/deepcel_serial_dashboard.py --serial-port /dev/ttyACM0
```

Abrir en la propia Raspberry:

```text
http://localhost:8501
```

ThingsBoard es opcional y se ejecuta como espejo en una segunda terminal. No guardar tokens reales en el repo:

```bash
export DEEPCEL_TB_HOST="https://thingsboard.cloud"
export DEEPCEL_TB_TOKEN="TOKEN_DEL_DEVICE"
python3 serial_dashboard/deepcel_thingsboard_bridge.py
```

## Variante multisensor pendiente

| Parte | Ruta |
|---|---|
| Sketch Arduino multisensor | `software/arduino/Temperature_light_i2c_q4_4_hwtest/` |
| Proyecto Quartus multisensor | `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/` |
| Bitstream Arduino multisensor | `software/arduino/Temperature_light_i2c_q4_4_hwtest/FPGA_Bitstream.h` |

Esta variante usa temperatura, luz y predicciones Q4.4. Se conserva porque la red y el selftest FPGA son utiles, pero la lectura real de luz no quedo cerrada con el hardware conectado.

Notas de depuracion de luz:

- El usuario quiere sensores por SDA/SCL, no A2.
- El scanner I2C vio `0x38`, `0x3C`, `0x60`, `0x6B` y a veces `0x77`.
- El sensor `Grove - Light Sensor` a secas suele ser analogico; si no lleva un chip I2C o un ADC I2C, no puede leerse solo por SDA/SCL.
- No tratar `NO_SENSOR`, fallback ni valores fijos de luz como medida real.

## Bajo consumo

La variante multisensor de bajo consumo queda conservada para trabajo posterior:

| Estrategia | Estado |
|---|---|
| Red activa por rafaga | Implementada en la variante multisensor. |
| Red secuencial | Implementada en `eco_nn_top.v` multisensor. |
| Reloj NN 1 MHz | Implementado en la variante multisensor ultralow. |
| `ArduinoLowPower` | No usar en estable por problemas de estabilidad. |

Power Analyzer vectorless de la variante multisensor ultralow:

| Variante | Potencia total | Core dinamica | Jerarquia `eco_nn_top:uut` |
|---|---:|---:|---:|
| Ultralow Q4.4 temperatura+luz 1 MHz | 201.78 mW | 12.61 mW | 0.06 mW |

La confianza de Power Analyzer es `Low` porque no hay actividad real `.vcd`/`.saif`. No presentar esas cifras como consumo real medido de la placa completa.

## Dependencias

Arduino:

| Libreria | Uso |
|---|---|
| `DHT20` | Temperatura y humedad por I2C. |
| `Wire` | Bus I2C desde core SAMD. |
| `SPI` | Soporte de plataforma desde core SAMD. |

Python principal:

```text
numpy
pandas
matplotlib
tensorflow
scikit-learn
openpyxl
pyserial
streamlit
```

## Herramientas auxiliares

| Fichero | Uso |
|---|---|
| `tools/Convert-VidorBitstream.ps1` | Convierte `MKRVIDOR4000.ttf` a `FPGA_Bitstream.h`. |
| `tools/Capture-VidorSerial.ps1` | Captura salida serie de la MKR Vidor para logs. |
| `tools/arduino/I2CScanner/` | Sketch minimo para listar direcciones I2C vistas por la MKR. |
| `serial_dashboard/deepcel_serial_dashboard.py` | Dashboard web local/offline. |
| `serial_dashboard/deepcel_thingsboard_bridge.py` | Puente opcional hacia ThingsBoard. |
