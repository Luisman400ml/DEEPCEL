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

La variante recomendada actual es la ultralow-power con temperatura, humedad, luz, red neuronal Q4.4 secuencial y reloj de red a 1 MHz.

## Estructura del repo

| Area | Ruta | Uso |
|---|---|---|
| Hardware Quartus | `hardware/quartus/projects/` | Proyectos separados por variante; la base funcional para comparativa es `ANeural_Network_power25`. |
| Constraints Vidor | `hardware/quartus/constraints/MKRVIDOR4000/` | Constraints originales recuperados de la MKR Vidor 4000. |
| RTL de referencia | `hardware/verilog_reference/common_rtl/` | HDL suelto historico; no asumir que es un proyecto Quartus completo. |
| Arduino | `software/arduino/` | Sketches completos, cada uno en su carpeta compatible con Arduino IDE. |
| Python/modelo | `software/python/base_model/` | Scripts y modelo Keras principales. |
| Paquete multisensor | `software/python/Temperature_and_Light_Q4.4_ANN/` | Paquete original de entrenamiento/template. |
| Informes | `docs/reports/` | Informes de Arduino, Quartus y estrategias de consumo. |
| Evidencias | `docs/evidence/hardware_validation/` | Logs serie, compilacion, carga y snapshots. |
| Capturas | `docs/captures/quartus/` | Capturas usadas por informes. |
| Herramientas | `tools/` | Scripts PowerShell auxiliares. |

## Variante recomendada

| Parte | Ruta |
|---|---|
| Sketch Arduino actual | `software/arduino/Temperature_light_ultralowpower_seq_1mhz_samd_lowpower/` |
| Fichero principal Arduino | `software/arduino/Temperature_light_ultralowpower_seq_1mhz_samd_lowpower/Temperature_light_ultralowpower_seq_1mhz_samd_lowpower.ino` |
| Proyecto Quartus actual | `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/` |
| Proyecto Quartus | `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/MKRVIDOR4000.qpf` |
| Top FPGA | `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/MKRVIDOR4000_top.v` |
| Red neuronal RTL | `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/eco_nn_top.v` |
| Bitstream Quartus TTF | `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/output_files/MKRVIDOR4000.ttf` |
| Bitstream Arduino generado | `software/arduino/Temperature_light_ultralowpower_seq_1mhz_samd_lowpower/FPGA_Bitstream.h` |
| Reporte de potencia | `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/output_files/MKRVIDOR4000.pow.rpt` |

Las variantes anteriores se conservan para comparativa:

| Variante | Ruta Quartus | Ruta Arduino asociada |
|---|---|---|
| Base historica | `hardware/quartus/projects/ANeural_Network/` | `software/arduino/Data_prediction/` |
| Base 25.1 temperatura | `hardware/quartus/projects/ANeural_Network_power25/` | `software/arduino/Temperature_real_base_hwtest/` |
| Lowpower 24 MHz temperatura | `hardware/quartus/projects/ANeural_Network_power25_lowpower/` | `software/arduino/Temperature_real_lowpower_hwtest/` |
| Luz Q4.4 24 MHz | `hardware/quartus/projects/ANeural_Network_power25_lowpower_light_q4_4/` | `software/arduino/Temperature_light_lowpower_hwtest/` |
| Luz Q4.4 6 MHz | `hardware/quartus/projects/ANeural_Network_power25_lowpower_light_q4_4_lowfreq_6mhz/` | `software/arduino/Temperature_light_lowpower_hwtest_lowfreq/` |
| Luz Q4.4 6 MHz + SAMD idle | mismo Quartus de 6 MHz | `software/arduino/Temperature_light_lowpower_hwtest_lowfreq_samd_lowpower/` |
| Ultralow secuencial 1 MHz + SAMD idle | `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/` | `software/arduino/Temperature_light_ultralowpower_seq_1mhz_samd_lowpower/` |

`hardware/quartus/projects/ANeural_Network/` queda como historico/template y no debe usarse como referencia principal de compilacion.

## Sensores y conexiones

| Sensor | Uso | Conexion esperada |
|---|---|---|
| DHT20 | Temperatura y humedad | I2C de la MKR Vidor, direccion habitual `0x38` |
| Grove Light Sensor analogico | Luz | `SIG -> A2`, mas `VCC` y `GND` |

No conectar el Grove Light Sensor analogico a I2C. La humedad se mide y se imprime por serie, pero no entra en la red neuronal FPGA actual.

## Modelo neuronal

- Formato numerico actual: Q4.4 de 8 bits.
- Entradas: 8 valores.
- Orden de entradas:
  - `temperature_history[0..3]`
  - `light_history[0..3]`
- Capa oculta: 16 neuronas ReLU.
- Salidas:
  - `PredictionTemperature_C`
  - `PredictionLight_model`

Aviso: algunos ficheros historicos mencionan Q8.8, pero la implementacion activa del RTL y del selftest trabaja en Q4.4. No cambiar formato sin rehacer sketch, RTL, bitstream y selftest.

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
| `2` | Pulso `temp_data_ready`, bit 0 | No usado como salida |
| `3` | Pulso `light_data_ready`, bit 0 | No usado como salida |

Arduino escribe temperatura y luz, genera pulsos de `ready` y espera antes de leer. En la variante ultralow los pulsos se alargan a `20 us` en `fpga_selftest.h` para capturarlos con la red a 1 MHz.

## Bajo consumo aplicado

| Estrategia | Estado | Implementacion |
|---|---|---|
| Red activa por rafaga | Implementada | La inferencia se lanza solo cuando llega el par completo temperatura/luz. |
| Reloj reducido | Implementada | `wNN_CLK` usa `clk[0]` a 1 MHz; JTAG conserva 120 MHz. |
| Arquitectura secuencial | Implementada | `eco_nn_top.v` usa FSM, acumulador e indices para calcular la red por pasos. |
| Top minimo | Implementado | Perifericos no usados quedan sin actividad util o en tri-state. |
| Optimizacion Quartus | Implementada | `OPTIMIZATION_MODE "AGGRESSIVE POWER"`. |
| Bajo consumo SAMD21 | Implementado | `ArduinoLowPower` con `LowPower.idle(...)` entre muestras. |

Power Analyzer vectorless:

| Variante | Potencia total | Core dinamica | Jerarquia `eco_nn_top:uut` |
|---|---:|---:|---:|
| Base 25.1 | 234.21 mW | 45.81 mW | 22.86 mW |
| Lowpower 24 MHz | 212.53 mW | 24.51 mW | 4.71 mW |
| Luz Q4.4 6 MHz | 206.64 mW | 18.77 mW | 0.96 mW |
| Ultralow secuencial 1 MHz | 201.78 mW | 12.61 mW | 0.06 mW |

La confianza de Power Analyzer es `Low` porque no hay actividad real `.vcd`/`.saif`. No presentar esas cifras como medida real de placa completa.

## Salida serie esperada

Baudios: `9600`.

Arranque:

```text
FPGA successfully configured!
Build: Quartus 25.1 ultralowpower light Q4.4 sequential MAC + 1 MHz NN clock + SAMD21 idle low power, DHT20 humidity, Grove Light Sensor on A2
SELFTEST PASS multisensor_q4_4 vectors=128 reads=512 failures=0
```

Modo texto normal:

```text
TemperatureHistory_C:[25.88,25.88,25.87,25.87]
LightHistory_ADC:[952,512,889,862]
Temperature_C:25.87
Light_ADC:862
PredictionTemperature_C:24.61
PredictionLight_model:380
Humidity_pct:53.98
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
| `Arduino Low Power` | `LowPower.idle(...)` entre muestras. |
| `RTCZero` | Dependencia de `Arduino Low Power`. |
| `Wire` | Bus I2C desde core SAMD. |
| `SPI` | Soporte de plataforma desde core SAMD. |

Instalacion por Arduino CLI:

```powershell
& "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe" lib install "DHT20"
& "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe" lib install "Arduino Low Power"
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
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\Convert-VidorBitstream.ps1 -InputPath .\hardware\quartus\projects\ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz\output_files\MKRVIDOR4000.ttf -OutputPath .\software\arduino\Temperature_light_ultralowpower_seq_1mhz_samd_lowpower\FPGA_Bitstream.h
```

Compilar y cargar Arduino:

```powershell
cd C:\Users\PC\OneDrive\Escritorio\DEEPCEL
& "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe" compile --fqbn arduino:samd:mkrvidor4000 .\software\arduino\Temperature_light_ultralowpower_seq_1mhz_samd_lowpower
& "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe" upload -p COM4 --fqbn arduino:samd:mkrvidor4000 .\software\arduino\Temperature_light_ultralowpower_seq_1mhz_samd_lowpower
```

Si `COM4` esta ocupado, normalmente hay un monitor serie abierto desde Arduino IDE o VS Code. Cerrar el monitor antes de subir.

## Herramientas auxiliares

| Fichero | Uso |
|---|---|
| `tools/Convert-VidorBitstream.ps1` | Convierte `MKRVIDOR4000.ttf` a `FPGA_Bitstream.h` invirtiendo bits dentro de cada byte. |
| `tools/Capture-VidorSerial.ps1` | Captura salida serie de la MKR Vidor para logs. |

## Reglas practicas para agentes

- No asumir que `software/arduino/Temperature_real/` es el proyecto final; es historico de temperatura.
- No eliminar humedad: debe seguir midiendose e imprimiendose.
- No cambiar `FPGA.begin(32, 4)` sin cambiar tambien top Quartus, sketch y selftest.
- No tratar los mW de Quartus como medida real de la placa completa.
- No modificar el formato Q4.4 sin revalidar contra referencia software.
- No borrar `output_files/` de la variante recomendada: contienen reportes y bitstream reproducibles.
- El proyecto parcial `hardware/quartus/projects/ANeural_Network_power25_lowpower_light_q4_4_lowfreq/` esta ignorado y no debe usarse.
