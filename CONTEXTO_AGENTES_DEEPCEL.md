# Contexto para agentes Codex sobre DEEPCEL

Este documento sirve para que Codex u otro agente pueda retomar el proyecto sin reconstruir todo el contexto de la conversacion. El estado recomendado es el proyecto Arduino/Quartus de temperatura, humedad y luz con red neuronal en FPGA, modo rafaga y reloj de red neuronal a 6 MHz.

## Repositorio

- Remoto GitHub: `https://github.com/Luisman400ml/DEEPCEL`
- Rama principal: `main`
- Plataforma hardware: Arduino MKR Vidor 4000
- FPGA: Cyclone 10 LP `10CL016YU256C8G`
- Herramientas usadas:
  - Quartus Prime Lite `25.1std.0 Build 1129`
  - Arduino core `arduino:samd` `1.8.14`
  - Arduino CLI `0.35.3`

## Variante actual recomendada

Usar estas dos carpetas como referencia actual:

| Parte | Ruta |
|---|---|
| Sketch Arduino actual | `Temperature_light_lowpower_hwtest_lowfreq/` |
| Fichero principal Arduino | `Temperature_light_lowpower_hwtest_lowfreq/Temperature_light_lowpower_hwtest_lowfreq.ino` |
| Proyecto Quartus actual | `QuartusProject/ANeural_Network_power25_lowpower_light_q4_4_lowfreq_6mhz/` |
| Proyecto Quartus | `QuartusProject/ANeural_Network_power25_lowpower_light_q4_4_lowfreq_6mhz/MKRVIDOR4000.qpf` |
| Top FPGA | `QuartusProject/ANeural_Network_power25_lowpower_light_q4_4_lowfreq_6mhz/MKRVIDOR4000_top.v` |
| Red neuronal RTL | `QuartusProject/ANeural_Network_power25_lowpower_light_q4_4_lowfreq_6mhz/eco_nn_top.v` |
| Neurona RTL | `QuartusProject/ANeural_Network_power25_lowpower_light_q4_4_lowfreq_6mhz/neuron.v` |
| Bitstream Arduino generado | `Temperature_light_lowpower_hwtest_lowfreq/FPGA_Bitstream.h` |
| Bitstream Quartus TTF | `QuartusProject/ANeural_Network_power25_lowpower_light_q4_4_lowfreq_6mhz/output_files/MKRVIDOR4000.ttf` |

Las otras carpetas se conservan como historico, comparativas o proyectos previos. No tomarlas como variante final salvo que el usuario lo pida.

## Sensores y conexiones

| Sensor | Uso | Conexion esperada |
|---|---|---|
| DHT20 | Temperatura y humedad | I2C de la MKR Vidor, direccion habitual `0x38` |
| Grove Light Sensor analogico | Luz | `SIG -> A2`, mas `VCC` y `GND` |

La humedad se mide y se imprime por serie, pero no entra en la red neuronal FPGA actual. La red usa cuatro muestras historicas de temperatura y cuatro muestras historicas de luz.

## Modelo neuronal actual

- Formato numerico en RTL actual: Q4.4 de 8 bits.
- Entradas: 8 valores.
- Orden de entradas:
  - `window[0:3]`: historico de temperatura.
  - `window[4:7]`: historico de luz.
- Capa oculta: 16 neuronas ReLU.
- Salidas: 2 valores.
  - `prediction_temperature`
  - `prediction_light`

Aviso importante: algunos comentarios heredados en `python/neuron.py` y `python/params_neural_net.txt` mencionan Q8.8, pero la implementacion actual exportada al RTL y al sketch trabaja como Q4.4 de 8 bits. No cambiar a Q8.8 sin rehacer el contrato Arduino/FPGA y el selftest.

## Protocolo Arduino/FPGA

El sketch usa:

```cpp
FPGA.begin(32, 4)
```

Mapa de registros:

| Registro | Escritura desde Arduino | Lectura desde Arduino |
|---|---|---|
| `0` | Temperatura Q4.4, bits bajos | Prediccion temperatura Q4.4, bits bajos |
| `1` | Luz Q4.4, bits bajos | Prediccion luz Q4.4, bits bajos |
| `2` | `temp_data_ready`, bit 0 | No usado como salida |
| `3` | `light_data_ready`, bit 0 | No usado como salida |

Arduino escribe primero temperatura y luz, despues genera pulsos cortos en los registros `2` y `3`. La FPGA detecta los flancos, marca muestras pendientes y solo ejecuta inferencia cuando llega el par completo temperatura/luz.

## Bajo consumo aplicado

Hay dos optimizaciones funcionales ya aplicadas:

| Punto | Estado | Implementacion |
|---|---|---|
| Modo rafaga | Implementado | La red solo calcula cuando llega un par completo temperatura/luz. |
| Menor frecuencia | Implementado | `wNN_CLK` usa `wCLK6`; PLL `clk0_divide_by = 8`, equivalente a 6 MHz. |

Valores de Power Analyzer vectorless:

| Variante | Reloj NN | Potencia total | Core dinamica | Dominio NN |
|---|---:|---:|---:|---:|
| Burst 24 MHz | 24 MHz | 212.19 mW | 24.23 mW | 18.93 mW |
| Burst 6 MHz | 6 MHz | 206.64 mW | 18.77 mW | 14.23 mW |

La confianza del Power Analyzer es `Low` porque no hay actividad real VCD/SAIF. La comparativa es util solo porque ambas variantes se midieron con la misma metodologia.

## Arduino Low Power

La libreria oficial `ArduinoLowPower` permite usar modos de bajo consumo del microcontrolador SAMD21 de la MKR Vidor. En este proyecto solo afectaria al SAMD21 entre muestras; no apaga automaticamente la FPGA Cyclone 10, el PLL ni los I/O de la FPGA.

Referencias:

- `https://github.com/arduino-libraries/ArduinoLowPower`
- `https://www.arduinolibraries.info/libraries/arduino-low-power`

Instalacion por Arduino CLI:

```powershell
& "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe" lib install "Arduino Low Power"
```

Uso conceptual para el sketch actual:

```cpp
#include <ArduinoLowPower.h>

// Tras leer DHT20/luz, enviar datos a FPGA, leer prediccion e imprimir:
LowPower.idle(10000);
```

Modos relevantes:

| API | Uso | Riesgo practico en este proyecto |
|---|---|---|
| `LowPower.idle(ms)` | Sueno ligero temporizado. | Mejor primera prueba porque conserva mejor la depuracion por USB serie. |
| `LowPower.sleep(ms)` | Sueno mas profundo temporizado. | Puede desconectar o alterar el comportamiento de USB Serial; validar `Wire`/DHT20 al despertar. |
| `LowPower.deepSleep(ms)` | En SAMD se comporta practicamente como `sleep`. | Mismo riesgo de USB/I2C; no empezar por aqui durante depuracion. |
| `LowPower.attachInterruptWakeup(pin, callback, mode)` | Despertar por GPIO. | Util solo si se quiere despertar por evento externo, no necesario para muestreo cada 10 s. |
| `LowPower.attachAdcInterrupt(...)` | Despertar por ventana ADC en SAMD. | Podria usarse con el sensor de luz, pero complica el flujo y debe validarse aparte. |

Integracion recomendada si se prueba:

1. Mantener `SAMPLE_INTERVAL_MS = 10000`.
2. Sustituir la espera pasiva entre muestras por `LowPower.idle(...)` en tramos cortos o por el tiempo restante hasta la siguiente muestra.
3. No dormir mientras se esta configurando la FPGA, ejecutando `runFpgaSelfTest`, leyendo DHT20, leyendo `A2`, escribiendo registros FPGA o imprimiendo por serie.
4. Empezar con `idle`, verificar que siguen funcionando `T`, `C`, `P` y que no aumentan errores `DHT20 read error`.
5. Solo despues probar `sleep`; asumir que la depuracion USB puede ser menos comoda.

Resultado esperado: menor consumo del SAMD21 durante los 10 segundos entre muestras. Resultado no garantizado: gran reduccion de potencia total de placa, porque la FPGA sigue alimentada y configurada. Para medir el impacto real hace falta corriente externa o instrumentacion equivalente.

## Salida serie esperada

Baudios: `9600`.

Modo texto normal:

```text
TemperatureHistory_C:[27.55,27.57,27.57,27.57]
LightHistory_ADC:[673,894,765,892]
Temperature_C:27.57
Light_ADC:892
PredictionTemperature_C:24.61
PredictionLight_model:326
Humidity_pct:52.46
```

Comandos serie:

| Comando | Efecto |
|---|---|
| `T` | Imprime build y ejecuta selftest FPGA. |
| `C` | Cambia a salida CSV. |
| `P` | Vuelve a salida texto normal. |

Validacion conocida en placa:

```text
SELFTEST PASS multisensor_q4_4 vectors=128 reads=512 failures=0
```

## Ficheros Arduino necesarios

La carpeta `Temperature_light_lowpower_hwtest_lowfreq/` contiene todo lo necesario para abrir y compilar desde Arduino IDE:

| Fichero | Funcion |
|---|---|
| `Temperature_light_lowpower_hwtest_lowfreq.ino` | Sketch principal. |
| `FPGA_Bitstream.h` | Bitstream embebido para configurar la FPGA desde el SAMD21. |
| `fpga_selftest.h` | Selftest bit-exacto de la red Q4.4 multisensor. |
| `FPGA.cpp`, `FPGA.h` | Carga/configuracion FPGA y API de registros. |
| `jtag.c`, `jtag.h` | Acceso JTAG interno usado por la libreria Vidor. |
| `upload.cpp`, `upload.h` | Rutina de carga del bitstream. |

Dependencia externa Arduino:

| Libreria | Version usada | Uso |
|---|---:|---|
| `DHT20` | `0.3.3` | Lectura de temperatura y humedad por I2C. |
| `ArduinoLowPower` | opcional | Dormir el SAMD21 entre muestras si se implementa la siguiente optimizacion de consumo. |
| `Wire` | core SAMD | Bus I2C. |
| `SPI` | core SAMD | Dependencia de soporte de la plataforma. |

## Ficheros Quartus necesarios

La carpeta `QuartusProject/ANeural_Network_power25_lowpower_light_q4_4_lowfreq_6mhz/` conserva los ficheros necesarios para abrir, revisar y recompilar el proyecto:

| Fichero/carpeta | Funcion |
|---|---|
| `MKRVIDOR4000.qpf` | Proyecto Quartus. |
| `MKRVIDOR4000.qsf` | Asignaciones de proyecto, pines y fuentes. |
| `MKRVIDOR4000.sdc` | Constraints temporales. |
| `MKRVIDOR4000_top.v` | Top de la MKR Vidor 4000 y puente Arduino/FPGA. |
| `eco_nn_top.v` | Red neuronal Q4.4, historicos, modo rafaga. |
| `neuron.v` | Neurona parametrizable con acumulacion Q4.4. |
| `SYSTEM_PLL.v`, `SYSTEM_PLL_altpll.v` | PLL con salida de red a 6 MHz. |
| `jtag_interface*.v`, `jtag_memory.v`, `jtag_synchronizer*.v` | Interfaz de registros via JTAG virtual. |
| `vidor_s_pins_recovered.qsf` | Constraints originales recuperados de la MKR Vidor. |
| `output_files/` | Reportes y bitstreams generados, incluido `MKRVIDOR4000.ttf`. |

No se versionan `db/`, `incremental_db/`, `simulation/` ni `work/` porque son artefactos regenerables de Quartus o simulacion.

## Ficheros Python incluidos

Los ficheros Python del modelo estan incluidos en `python/`:

| Fichero | Funcion |
|---|---|
| `python/Data_Set_Generation.py` | Genera datos sinteticos de temperatura/luz y exporta dataset de presentacion. |
| `python/neuron.py` | Entrena/carga el modelo Keras multisensor y exporta pesos/biases. |
| `python/model_multisensor_fpga.keras` | Modelo Keras guardado. |
| `python/params_neural_net.txt` | Pesos y bias exportados, usados como referencia para el RTL. |

Dependencias Python esperadas por los scripts:

```text
numpy
pandas
matplotlib
tensorflow
scikit-learn
openpyxl
```

`openpyxl` es necesario si se ejecuta `Data_Set_Generation.py` y se quiere escribir el `.xlsx` con pandas.

## Flujo para recompilar Quartus

Desde PowerShell:

```powershell
cd C:\Users\PC\OneDrive\Escritorio\DEEPCEL\QuartusProject\ANeural_Network_power25_lowpower_light_q4_4_lowfreq_6mhz
& 'C:\altera_lite\25.1std\quartus\bin64\quartus_sh.exe' --flow compile MKRVIDOR4000
& 'C:\altera_lite\25.1std\quartus\bin64\quartus_pow.exe' MKRVIDOR4000 -c MKRVIDOR4000
```

Salida esperada de referencia:

- Full compile: `0 errors`.
- Timing cerrado.
- Power Analyzer: `206.64 mW`, confidence `Low`.

## Flujo para regenerar el bitstream Arduino

Despues de compilar Quartus, convertir el TTF a cabecera Arduino:

```powershell
cd C:\Users\PC\OneDrive\Escritorio\DEEPCEL
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\Convert-VidorBitstream.ps1 -InputPath .\QuartusProject\ANeural_Network_power25_lowpower_light_q4_4_lowfreq_6mhz\output_files\MKRVIDOR4000.ttf -OutputPath .\Temperature_light_lowpower_hwtest_lowfreq\FPGA_Bitstream.h
```

El conversor invierte el orden de bits dentro de cada byte del `.ttf`, requisito del flujo de carga usado por la libreria Vidor.

## Flujo Arduino IDE / Arduino CLI

Abrir en Arduino IDE la carpeta:

```text
Temperature_light_lowpower_hwtest_lowfreq/
```

Seleccionar:

```text
Board: Arduino MKR Vidor 4000
Port: COM4
```

Compilar y subir por CLI:

```powershell
cd C:\Users\PC\OneDrive\Escritorio\DEEPCEL
& "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe" compile --fqbn arduino:samd:mkrvidor4000 .\Temperature_light_lowpower_hwtest_lowfreq
& "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe" upload -p COM4 --fqbn arduino:samd:mkrvidor4000 .\Temperature_light_lowpower_hwtest_lowfreq
```

Si `COM4` esta ocupado, normalmente hay un `serial-monitor.exe` abierto desde Arduino IDE. Cerrar el monitor serie antes de subir.

## Herramientas auxiliares

| Fichero | Uso |
|---|---|
| `tools/Convert-VidorBitstream.ps1` | Convierte `MKRVIDOR4000.ttf` a `FPGA_Bitstream.h`. |
| `tools/Capture-VidorSerial.ps1` | Captura salida serie de la MKR Vidor para logs. |

## Reglas practicas para agentes

- No asumir que `Temperature_real/` es el proyecto final actual; es historico de temperatura.
- No eliminar humedad: se debe seguir midiendo e imprimiendo.
- No conectar Grove Light Sensor al I2C: es analogico y va a `A2`.
- No cambiar el numero de registros de `FPGA.begin(32, 4)` sin cambiar tambien el top Quartus y el selftest.
- No vender los mW de Quartus como medida real de placa: son estimaciones vectorless.
- Para demostrar consumo real hace falta medir corriente externa o usar actividad real VCD/SAIF.
- `ArduinoLowPower` reduce consumo del SAMD21 entre muestras, pero no debe presentarse como apagado de la FPGA.
- El proyecto parcial `QuartusProject/ANeural_Network_power25_lowpower_light_q4_4_lowfreq/` esta ignorado y no debe usarse.
