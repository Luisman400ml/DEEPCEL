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

La variante definitiva actual es `software/arduino/Temperature_real_lowpower_hwtest/`: temperatura y humedad con DHT20, luz analogica con Grove Light Sensor, inferencia de temperatura en FPGA y salida serie CSV para la app Python. El arbol activo queda consolidado para trabajar solo en esta variante y en el proyecto Quartus asociado; las variantes historicas quedan disponibles en el historial Git, no como proyectos vivos dentro del repo.

## Estructura del repo

| Area | Ruta | Uso |
|---|---|---|
| Hardware Quartus | `hardware/quartus/projects/ANeural_Network_power25_lowpower/` | Unico proyecto Quartus activo. |
| Constraints Vidor | `hardware/quartus/constraints/MKRVIDOR4000/` | Constraints originales recuperados de la MKR Vidor 4000. |
| RTL de referencia | `hardware/verilog_reference/common_rtl/` | HDL suelto historico; no asumir que es un proyecto Quartus completo. |
| Arduino | `software/arduino/Temperature_real_lowpower_hwtest/` | Unico sketch Arduino activo, compatible con Arduino IDE y Arduino CLI. |
| Python/modelo | `software/python/base_model/` | Scripts y modelo Keras principales. |
| Paquete multisensor | `software/python/Temperature_and_Light_Q4.4_ANN/` | Paquete original de entrenamiento; sus plantillas Arduino/Quartus historicas se eliminaron del arbol activo. |
| Informes | `docs/reports/` | Informes de Arduino, Quartus y estrategias de consumo. |
| Evidencias | `docs/evidence/hardware_validation/` | Logs serie, compilacion, carga y snapshots. |
| Capturas | `docs/captures/quartus/` | Capturas usadas por informes. |
| Herramientas | `tools/` | Scripts PowerShell auxiliares. |

## Variante definitiva

| Parte | Ruta |
|---|---|
| Sketch Arduino actual | `software/arduino/Temperature_real_lowpower_hwtest/` |
| Fichero principal Arduino | `software/arduino/Temperature_real_lowpower_hwtest/Temperature_real_lowpower_hwtest.ino` |
| Proyecto Quartus actual | `hardware/quartus/projects/ANeural_Network_power25_lowpower/` |
| Proyecto Quartus | `hardware/quartus/projects/ANeural_Network_power25_lowpower/MKRVIDOR4000.qpf` |
| Top FPGA | `hardware/quartus/projects/ANeural_Network_power25_lowpower/MKRVIDOR4000_top.v` |
| Red neuronal RTL | `hardware/quartus/projects/ANeural_Network_power25_lowpower/eco_nn_top.v` |
| Bitstream Quartus TTF | `hardware/quartus/projects/ANeural_Network_power25_lowpower/output_files/MKRVIDOR4000.ttf` |
| Bitstream Arduino generado | `software/arduino/Temperature_real_lowpower_hwtest/FPGA_Bitstream.h` |
| Reporte de potencia | `hardware/quartus/projects/ANeural_Network_power25_lowpower/output_files/MKRVIDOR4000.pow.rpt` |

No debe haber otros `.ino` ni otros `.qpf` activos en el repo. Si hace falta consultar `t1`, `t3`, luz o ultralow, recuperar esas variantes desde el historial Git, no recrearlas como rutas de trabajo.

## Sensores y conexiones

| Sensor | Uso | Conexion esperada |
|---|---|---|
| DHT20 | Temperatura y humedad | I2C de la MKR Vidor, direccion habitual `0x38` |
| Grove Light Sensor analogico | Luz por ADC, telemetria y plot | `SIG -> A2`, mas `VCC` y `GND` |

No conectar el Grove Light Sensor analogico a I2C. La luz se lee desde `A2` y se imprime junto al resto de telemetria. No entra en la red neuronal Q8.8 actual.

## Modelo neuronal

- Formato numerico actual: Q8.8 de 16 bits para temperatura.
- Entradas: 4 valores de historial temporal de temperatura.
- Orden de entradas: `temperature_history[0..3]`.
- Capa oculta: 8 neuronas ReLU.
- Salidas:
  - `prediction_c`

No mezclar formatos sin rehacer sketch, RTL, bitstream y selftest. La lectura `light_adc` es una medida auxiliar del SAMD21, no una entrada/salida de la red actual.

## Protocolo Arduino/FPGA

El sketch definitivo usa:

```cpp
FPGA.begin(32, 2)
```

Mapa de registros:

| Registro | Escritura desde Arduino | Lectura desde Arduino |
|---|---|---|
| `0` | Temperatura Q8.8 en bits bajos | Prediccion temperatura Q8.8 |
| `1` | Pulso `data_ready`, bit 0 | No usado como salida |

Arduino escribe la temperatura, genera un pulso de `ready` y espera antes de leer la prediccion. El selftest de `software/arduino/Temperature_real_lowpower_hwtest/fpga_selftest.h` valida 128 vectores y 256 lecturas.

## Bajo consumo aplicado

| Estrategia | Estado | Implementacion |
|---|---|---|
| Red activa por muestra | Implementada | La inferencia se lanza cuando llega una nueva temperatura. |
| Optimizacion Quartus | Implementada | Variante `ANeural_Network_power25_lowpower`. |
| Top minimo | Implementado | Perifericos no usados quedan sin actividad util o en tri-state. |
| Bajo consumo SAMD21 | No usar | No reintroducir `ArduinoLowPower`/`LowPower.idle(...)`; dio problemas de estabilidad con monitor serie. |

Power Analyzer vectorless:

| Variante activa | Potencia total | Core dinamica | Jerarquia `eco_nn_top:uut` |
|---|---:|---:|---:|
| Lowpower 24 MHz temperatura | 212.53 mW | 24.51 mW | 4.71 mW |

La confianza de Power Analyzer es `Low` porque no hay actividad real `.vcd`/`.saif`. No presentar esas cifras como medida real de placa completa. Las comparativas historicas estan en `docs/reports/`.

## Salida serie esperada

Baudios: `9600`.

Arranque:

```text
FPGA successfully configured!
```

Modo texto normal:

```text
Temperature_C:25.87	PredictionTemperature_C:24.61	Humidity_pct:53.98	Light_ADC:742
```

Modo CSV para la app Python:

```text
record,time_ms,temperature_c,humidity_rh_pct,light_adc,prediction_temperature_c
DATA,12345,25.8700,53.9800,742,24.6100
```

Comandos serie:

| Comando | Efecto |
|---|---|
| `T` | Imprime build y ejecuta selftest FPGA. |
| `C` | Cambia a salida CSV. |
| `P` | Vuelve a salida texto normal. |

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
cd C:\Users\PC\OneDrive\Escritorio\DEEPCEL\hardware\quartus\projects\ANeural_Network_power25_lowpower
& 'C:\altera_lite\25.1std\quartus\bin64\quartus_sh.exe' --flow compile MKRVIDOR4000
& 'C:\altera_lite\25.1std\quartus\bin64\quartus_pow.exe' MKRVIDOR4000 -c MKRVIDOR4000
```

Regenerar bitstream Arduino:

```powershell
cd C:\Users\PC\OneDrive\Escritorio\DEEPCEL
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\Convert-VidorBitstream.ps1 -InputPath .\hardware\quartus\projects\ANeural_Network_power25_lowpower\output_files\MKRVIDOR4000.ttf -OutputPath .\software\arduino\Temperature_real_lowpower_hwtest\FPGA_Bitstream.h
```

Compilar y cargar Arduino:

```powershell
cd C:\Users\PC\OneDrive\Escritorio\DEEPCEL
& "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe" compile --fqbn arduino:samd:mkrvidor4000 .\software\arduino\Temperature_real_lowpower_hwtest
& "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe" upload -p COM4 --fqbn arduino:samd:mkrvidor4000 .\software\arduino\Temperature_real_lowpower_hwtest
```

Si `COM4` esta ocupado, normalmente hay un monitor serie abierto desde Arduino IDE o VS Code. Cerrar el monitor antes de subir.

## Herramientas auxiliares

| Fichero | Uso |
|---|---|
| `tools/Convert-VidorBitstream.ps1` | Convierte `MKRVIDOR4000.ttf` a `FPGA_Bitstream.h` invirtiendo bits dentro de cada byte. |
| `tools/Capture-VidorSerial.ps1` | Captura salida serie de la MKR Vidor para logs. |

## Reglas practicas para agentes

- Trabajar por defecto sobre `software/arduino/Temperature_real_lowpower_hwtest/`; es el proyecto definitivo actual.
- Trabajar en `main`; no usar `t1` como rama de desarrollo.
- No crear nuevos sketches Arduino ni nuevos proyectos Quartus sin pedir confirmacion explicita.
- No eliminar humedad: debe seguir midiendose e imprimiendose.
- No cambiar `FPGA.begin(32, 2)` sin cambiar tambien top Quartus, sketch y selftest.
- No reintroducir `ArduinoLowPower`/`LowPower.idle(...)` en el sketch definitivo.
- No tratar los mW de Quartus como medida real de la placa completa.
- No modificar el formato Q8.8 sin revalidar contra referencia software.
- No borrar `output_files/` de la variante definitiva: contienen reportes y bitstream reproducibles.
