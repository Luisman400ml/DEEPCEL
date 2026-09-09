# Informe Arduino DEEPCEL

Fecha: 2026-09-07

Ruta analizada:

```text
C:\Users\PC\OneDrive\Escritorio\DEEPCEL
```

Este informe es solo informativo. No se ha ejecutado ningun comando de carga a placa (`upload`) ni se ha programado ningun Arduino. Las comprobaciones realizadas han sido de estructura, dependencias y compilacion local.

## Resumen

La carpeta contiene dos proyectos Arduino para Arduino MKR Vidor 4000:

| Proyecto | Sketch principal | Proposito |
| --- | --- | --- |
| `Temperature_real` | `Temperature_real.ino` | Lee temperatura real con un sensor DHT20, envia el dato a la FPGA y muestra por Serial el historial de 4 muestras y la prediccion. |
| `Temperature_real_and_Thingsboard` | `Temperature_real_and_Thingsboard.ino` | Variante simplificada pensada para que una Raspberry Pi lea por USB la prediccion enviada por Serial. |

Aunque el segundo proyecto incluye `Thingsboard` en el nombre, no hay conexion directa desde el Arduino a ThingsBoard. La salida se limita a Serial, por lo que la integracion con ThingsBoard tendria que estar en otro programa, previsiblemente en la Raspberry Pi.

## Estructura encontrada

Archivos compartidos en ambos proyectos:

| Archivo | Funcion |
| --- | --- |
| `FPGA.cpp` / `FPGA.h` | Interfaz C++ para cargar el bitstream y leer/escribir registros de la FPGA por JTAG interno. |
| `jtag.c` / `jtag.h` | Implementacion de bajo nivel del protocolo JTAG y message box. |
| `upload.cpp` / `upload.h` | Logica de carga del bitstream incluido en `FPGA_Bitstream.h`. |
| `FPGA_Bitstream.h` | Bitstream de la FPGA incluido como lista de bytes. |

Los archivos `FPGA.*`, `jtag.*` y `upload.*` son identicos en los dos proyectos. Cambian el sketch `.ino` y el bitstream.

Tamanos aproximados:

| Archivo | Tamano textual |
| --- | ---: |
| `software/arduino/Temperature_real/FPGA_Bitstream.h` | 473726 bytes |
| `software/arduino/Temperature_real_and_Thingsboard/FPGA_Bitstream.h` | 714569 bytes |
| `software/arduino/Temperature_real/Temperature_real.ino` | 3169 bytes |
| `software/arduino/Temperature_real_and_Thingsboard/Temperature_real_and_Thingsboard.ino` | 1184 bytes |

Los bitstreams contienen aproximadamente:

| Bitstream | Valores numericos |
| --- | ---: |
| `software/arduino/Temperature_real/FPGA_Bitstream.h` | 175721 |
| `software/arduino/Temperature_real_and_Thingsboard/FPGA_Bitstream.h` | 175894 |

## Dependencias instaladas

Se ha usado el `arduino-cli.exe` incluido con Arduino IDE:

```text
C:\Users\PC\AppData\Local\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe
```

Version detectada:

```text
arduino-cli 0.35.3
```

Dependencias instaladas:

| Dependencia | Version |
| --- | --- |
| `arduino:samd` | 1.8.14 |
| `DHT20` | 0.3.3 |

Placa verificada:

```text
Arduino MKR Vidor 4000 -> arduino:samd:mkrvidor4000
```

Librerias usadas al compilar:

| Libreria | Version | Origen |
| --- | --- | --- |
| `DHT20` | 0.3.3 | `C:\Users\PC\OneDrive\Documentos\Arduino\libraries\DHT20` |
| `Wire` | 1.0 | Core `arduino:samd` |
| `SPI` | 1.0 | Core `arduino:samd` |

## Compilacion local

Comandos usados para compilar sin cargar en placa:

```powershell
& "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe" compile --fqbn arduino:samd:mkrvidor4000 .\software\arduino\Temperature_real
& "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe" compile --fqbn arduino:samd:mkrvidor4000 .\software\arduino\Temperature_real_and_Thingsboard
```

Resultado:

| Proyecto | Flash | RAM | Estado |
| --- | ---: | ---: | --- |
| `Temperature_real` | 32448 bytes / 262144 bytes | 3304 bytes / 32768 bytes | Compila correctamente |
| `Temperature_real_and_Thingsboard` | 32200 bytes / 262144 bytes | 3288 bytes / 32768 bytes | Compila correctamente |

Tambien se ha repetido la compilacion con `--warnings all`. El resultado sigue siendo correcto para ambos proyectos. Solo aparecen warnings del enlazador, no errores de compilacion del sketch.

Durante el enlazado aparecen warnings de este tipo:

```text
warning: changing start of section .rel.dyn by 2/3 bytes
```

La compilacion termina correctamente pese a esos warnings.

## Funcionamiento general

### `Temperature_real`

Flujo del sketch:

1. Inicializa Serial a 9600 baudios.
2. Espera a que el puerto Serial este conectado.
3. Llama a `FPGA.begin(32, 2)`.
4. Inicializa I2C con `Wire.begin()`.
5. Inicializa el sensor DHT20.
6. En cada ciclo:
   - Lee la temperatura.
   - Actualiza una ventana local de 4 muestras.
   - Convierte la temperatura a formato Q8.8 con `temperature * 256`.
   - Escribe el valor en el registro 0 de la FPGA.
   - Pulsa el registro 1 como senal `DataReady`.
   - Lee la prediccion desde el registro 0.
   - Convierte la prediccion desde Q8.8 a `float`.
   - Imprime historial y prediccion por Serial.
   - Espera 10 segundos.

### `Temperature_real_and_Thingsboard`

Flujo del sketch:

1. Inicializa Serial a 9600 baudios.
2. Espera a que el puerto Serial este conectado.
3. Configura la FPGA con `FPGA.begin(32, 2)`.
4. Inicializa el sensor DHT20.
5. En cada ciclo:
   - Si la lectura del sensor es correcta, envia la temperatura a la FPGA.
   - Pulsa `DataReady`.
   - Lee la prediccion desde la FPGA.
   - Imprime solo el valor numerico de prediccion.
   - Espera 10 segundos.

Esta variante es mas adecuada para parseo desde Raspberry Pi, pero todavia imprime mensajes de estado en `setup()`.

## Revision Arduino actualizada

La revision se ha realizado sobre los dos sketches `.ino` y los modulos comunes `FPGA.*`, `jtag.*` y `upload.*`. No se ha usado ningun comando de carga a placa.

### Hallazgos principales

| Prioridad | Hallazgo | Referencias | Impacto |
| --- | --- | --- | --- |
| Alta | La variante `Temperature_real_and_Thingsboard` imprime una prediccion aunque falle la lectura del DHT20, porque `FPGA.read()` y `Serial.println()` estan fuera del bloque `if (status == DHT20_OK)`. | `software/arduino/Temperature_real_and_Thingsboard/Temperature_real_and_Thingsboard.ino:29`, `:43`, `:46`, `:50` | La Raspberry Pi podria recibir valores antiguos o no validos sin distinguirlos de una lectura correcta. |
| Media | `while(!Serial);` bloquea el arranque hasta que exista conexion USB/Serial. | `software/arduino/Temperature_real/Temperature_real.ino:11`, `software/arduino/Temperature_real_and_Thingsboard/Temperature_real_and_Thingsboard.ino:12` | En uso autonomo, el sistema puede quedarse parado si no hay host Serial abierto. |
| Media | `sensor1.begin()` devuelve `bool`, pero el resultado no se comprueba. | `software/arduino/Temperature_real/Temperature_real.ino:22`, `software/arduino/Temperature_real_and_Thingsboard/Temperature_real_and_Thingsboard.ino:22` | Si el DHT20 no esta conectado o falla el bus I2C, el programa no informa claramente del problema. |
| Media | La conversion Q8.8 usa `uint16_t` para entrada y prediccion. | `software/arduino/Temperature_real/Temperature_real.ino:41`, `software/arduino/Temperature_real/Temperature_real.ino:65`, `software/arduino/Temperature_real_and_Thingsboard/Temperature_real_and_Thingsboard.ino:32`, `software/arduino/Temperature_real_and_Thingsboard/Temperature_real_and_Thingsboard.ino:46` | No representa temperaturas negativas. Si la FPGA usa Q8.8 con signo, se debe usar `int16_t` y convertir con signo. |
| Media | El registro 0 se usa como entrada de temperatura y salida de prediccion. | `software/arduino/Temperature_real/Temperature_real.ino:44`, `software/arduino/Temperature_real/Temperature_real.ino:65`, `software/arduino/Temperature_real_and_Thingsboard/Temperature_real_and_Thingsboard.ino:35`, `software/arduino/Temperature_real_and_Thingsboard/Temperature_real_and_Thingsboard.ino:46` | Es valido si el diseno FPGA lo define asi, pero debe documentarse como contrato de protocolo para evitar errores al cambiar el bitstream. |
| Media | `Temperature_real` mantiene una ventana local de 4 temperaturas, pero solo envia la muestra actual a la FPGA. | `software/arduino/Temperature_real/Temperature_real.ino:33`, `software/arduino/Temperature_real/Temperature_real.ino:37`, `software/arduino/Temperature_real/Temperature_real.ino:41`, `software/arduino/Temperature_real/Temperature_real.ino:44` | Si el modelo FPGA necesita las 4 muestras y no guarda historial internamente, la prediccion no usara la ventana mostrada por Serial. |
| Baja | La salida Serial y algunos comentarios tienen texto con codificacion corrupta, por ejemplo `Â°C`. | `software/arduino/Temperature_real/Temperature_real.ino:32`, `software/arduino/Temperature_real/Temperature_real.ino:73`, `FPGA.h:39` | Es principalmente cosmetico, pero puede molestar si se registran logs o se parsea texto. |
| Baja | `upload.cpp` guarda el resultado de `jtagInit()` pero no lo valida, y tampoco valida el resultado de `mbEveSend()`. | `software/arduino/Temperature_real/upload.cpp:85`, `software/arduino/Temperature_real/upload.cpp:90` | Si falla la configuracion FPGA, el error final sera menos diagnostico. |
| Baja | En `jtag.c`, `jtagReadBuffer()` devuelve `len` despues de decrementar el contador hasta cero. | `software/arduino/Temperature_real/jtag.c:623`, `software/arduino/Temperature_real/jtag.c:645`, `software/arduino/Temperature_real/jtag.c:651` | Como API general deberia devolver el numero de palabras leidas o un codigo de error. En el flujo actual apenas se usa ese retorno. |
| Baja | `mbPinSet()` esta declarado como `int`, pero no retorna valor. | `software/arduino/Temperature_real/jtag.c:660`, `software/arduino/Temperature_real/jtag.c:669` | No rompe el sketch actual porque no se usa el retorno, pero conviene corregirlo por limpieza y portabilidad. |

### Revision del flujo Raspberry Pi / ThingsBoard

El proyecto `Temperature_real_and_Thingsboard` parece preparado para que otra maquina lea la prediccion por USB y la envie a ThingsBoard. Para esa funcion, la salida Serial deberia ser estable y facil de parsear.

Estado actual:

```text
FPGA successfully configured!
23.45
23.47
...
```

Riesgo:

```text
23.47
23.47
23.47
```

Si el sensor falla, el sketch puede seguir imprimiendo la ultima prediccion leida desde la FPGA. Desde la Raspberry Pi eso se veria como una medicion valida.

Formato recomendado para integracion:

```json
{"status":"ok","prediction":23.47}
{"status":"sensor_error","code":-11}
{"status":"fpga_error","message":"..."}
```

Si se prefiere mantener una salida numerica pura, entonces conviene no imprimir mensajes de estado en `setup()` y no imprimir nada cuando `sensor1.read()` falle.

## Observaciones tecnicas

1. `while(!Serial);` bloquea el arranque hasta que haya conexion Serial. Para uso autonomo con Raspberry Pi puede ser aceptable, pero para funcionamiento sin monitor Serial conviene usar un timeout.
2. La salida del proyecto `Temperature_real_and_Thingsboard` no es completamente numerica desde el arranque, porque imprime mensajes como `FPGA successfully configured!`. Si la Raspberry Pi espera solo floats, debe ignorar lineas no numericas o el sketch debe silenciar esos mensajes.
3. La lectura de prediccion en `Temperature_real_and_Thingsboard` deberia depender de una lectura valida del sensor o incluir un estado explicito de error.
4. La conversion Q8.8 usa `uint16_t`. Esto no representa temperaturas negativas. Si el modelo FPGA trabaja con valores con signo, deberia usarse `int16_t`.
5. `Temperature_real` mantiene una ventana local de 4 temperaturas, pero solo envia la muestra actual a la FPGA. Si el modelo necesita 4 muestras y la FPGA no mantiene su propio historial, faltaria enviar la ventana completa o modificar el protocolo.
6. `FPGA.begin(32, 2)` exige que el bitstream exponga una interfaz JTAG con registros de 32 bits y 2 registros utilizables. Si se cambia el bitstream, hay que mantener esa interfaz o actualizar esos parametros.
7. `upload.cpp` llama a `jtagInit()` y `mbEveSend()` pero no usa sus codigos de error para informar la causa exacta del fallo. Si la configuracion FPGA falla, la depuracion puede ser limitada.
8. En `jtag.c`, algunos campos `unsigned char` usan `-1` como valor centinela. Funciona por conversion a 255, pero es fragil y convendria sustituirlo por constantes explicitas o tipos con signo.

## Recomendaciones

Para mejorar robustez antes de uso continuo:

1. Mover la lectura e impresion de prediccion de `Temperature_real_and_Thingsboard` dentro del bloque `if (status == DHT20_OK)`, o imprimir un error estructurado cuando falle el sensor.
2. Comprobar el retorno de `sensor1.begin()` durante `setup()`.
3. Anadir timeout al bloqueo de Serial.
4. Dejar la variante Raspberry Pi con salida estrictamente numerica o formato claro, por ejemplo JSON lineal.
5. Confirmar si la prediccion FPGA usa Q8.8 con signo o sin signo.
6. Documentar el contrato de registros FPGA:
   - Registro 0: entrada de temperatura y salida de prediccion.
   - Registro 1: pulso `DataReady`.
7. Propagar errores de `jtagInit()` y `mbEveSend()` a `FPGA.begin()`.
8. Corregir retornos inconsistentes en `jtag.c`, especialmente `mbPinSet()` y `jtagReadBuffer()`.
9. Evitar compilar ambos proyectos en paralelo justo despues de instalar dependencias, ya que la primera compilacion inicializa caches del core Arduino.

## Revision de la carpeta Verilog

Fecha de revision: 2026-09-07

Se ha detectado una nueva carpeta en la raiz:

```text
C:\Users\PC\OneDrive\Escritorio\DEEPCEL\hardware\verilog_reference\common_rtl
```

Esta carpeta contiene fuentes HDL para la FPGA de la MKR Vidor 4000. No se ha cargado nada en placa durante esta revision.

### Que contiene

| Archivo | Funcion probable |
| --- | --- |
| `MKRVIDOR4000_top.v` | Top-level para la FPGA de Arduino MKR Vidor 4000. Instancia la PLL, la red neuronal y la interfaz JTAG. |
| `eco_nn_top.v` | Red neuronal para prediccion de temperatura y luz. Usa una ventana de 8 valores: 4 de temperatura y 4 de luz. |
| `neuron.v` | Neurona parametrizable con suma ponderada Q8.8 y activacion ReLU. |
| `q_multiplier.v` | Multiplicador Q8.8 independiente. No aparece instanciado por el top actual. |
| `q_multiplier_tb.v` | Testbench simple para `q_multiplier.v`. |
| `eco_nn_top_Tb .v` | Testbench para `eco_nn_top.v`; el nombre contiene un espacio antes de `.v`. |
| `jtag_interface.v` | Interfaz JTAG generica con registros parametrizables. |
| `jtag_memory.v` | Banco de registros accesible desde Arduino por JTAG. |
| `jtag_interface3.v`, `jtag_interface7.v`, `jtag_interface15.v`, `jtag_interface31.v` | Wrappers para diferentes numeros de registros. |
| `jtag_synchronizer_basic.v` | Sincronizador basico de una senal. |
| `MKRVIDOR4000.vhd` | Ejemplo VHDL de incremento de dato. Parece un archivo antiguo o de prueba, no conectado al top Verilog actual. |

### Relacion con los proyectos Arduino

El top nuevo instancia:

```verilog
jtag_interface #(
  .REGISTER_SIZE(16),
  .NUMBER_OF_REGISTERS(4)
)
```

Por tanto, esta carpeta encaja con los proyectos:

```text
software\arduino\Data_prediction
software\arduino\Data_prediction_and_Thingsboard
```

Estos sketches usan:

```cpp
FPGA.begin(16, 4)
```

No encaja directamente con los proyectos simples de temperatura:

```text
Temperature_real
Temperature_real_and_Thingsboard
```

Estos usan:

```cpp
FPGA.begin(32, 2)
```

Conclusion: la carpeta `Verilog` corresponde al diseno de temperatura + luz, no al sketch simple de temperatura que se cargo en la placa.

### Hallazgos principales

| Prioridad | Hallazgo | Referencias | Impacto |
| --- | --- | --- | --- |
| Alta | Falta el modulo `jtag_synchronizer`. `jtag_interface.v` lo instancia, pero el archivo disponible declara `synchronizer_basic`, no `jtag_synchronizer`. | `hardware/verilog_reference/common_rtl/jtag_interface.v:45`, `hardware/verilog_reference/common_rtl/jtag_synchronizer_basic.v:2` | El proyecto no deberia sintetizar tal como esta salvo que exista otro archivo no incluido. |
| Alta | No estan los archivos completos de proyecto Quartus: no se ven `.qpf`, `.qsf`, `.sdc` ni el IP generado de `SYSTEM_PLL`. | `hardware/verilog_reference/common_rtl/MKRVIDOR4000_top.v:153` | Con solo esta carpeta probablemente no se puede regenerar `FPGA_Bitstream.h`. |
| Alta | El top deja muchas senales fisicas declaradas pero sin asignacion visible: SDRAM, HDMI, flash, MKR, Mini PCIe, NINA, etc. | `hardware/verilog_reference/common_rtl/MKRVIDOR4000_top.v:27`, `:30`, `:42`, `:47`, `:74`, `:97`, `:113` | Puede producir warnings de sintesis y comportamiento indefinido si no hay constraints o asignaciones externas que lo controlen. |
| Media | `wFLASH_CLK` se usa en la PLL pero no esta declarado. | `hardware/verilog_reference/common_rtl/MKRVIDOR4000_top.v:160` | Verilog puede crear una red implicita, pero es fragil. Con `default_nettype none` seria error. |
| Media | `eco_nn_top_Tb .v` tiene un espacio en el nombre antes de `.v`. | `hardware/verilog_reference/common_rtl/eco_nn_top_Tb .v` | Puede causar problemas en scripts, rutas o herramientas de simulacion. |
| Media | El testbench no aplica reset activo bajo. Inicializa `reset = 1`, pero el diseno resetea con `if (!reset)`. | `hardware/verilog_reference/common_rtl/eco_nn_top_Tb .v:36`, `hardware/verilog_reference/common_rtl/eco_nn_top.v:15` | En simulacion, la ventana interna puede arrancar en `X` hasta recibir suficientes muestras. |
| Media | El mismo modulo `neuron.v` usa ReLU tambien en la capa de salida. | `hardware/verilog_reference/common_rtl/eco_nn_top.v:144`, `hardware/verilog_reference/common_rtl/neuron.v:24` | Para regresion de temperatura/luz, una salida lineal suele ser mas apropiada. ReLU fuerza predicciones negativas a cero. |
| Media | La suma de la neurona trunca `sum[15:0]` sin saturacion. | `hardware/verilog_reference/common_rtl/neuron.v:24` | Si hay overflow, la salida puede envolver en lugar de saturar. |
| Baja | Hay archivos que parecen auxiliares o no usados por el top actual, como `q_multiplier.v`, `q_multiplier_tb.v`, `jtag_interface3/7/15/31.v` y `MKRVIDOR4000.vhd`. | `hardware/verilog_reference/common_rtl/q_multiplier.v:1`, `hardware/verilog_reference/common_rtl/MKRVIDOR4000.vhd:6` | Conviene documentar si son pruebas, ejemplos o versiones antiguas para evitar confusion. |

### Mapeo JTAG esperado por este diseno

En `MKRVIDOR4000_top.v`, la interfaz JTAG mapea 4 registros de 16 bits:

| Registro Arduino | Direccion | Uso segun el top |
| --- | ---: | --- |
| Registro 0 | `FPGA.write(0, ...)` / `FPGA.read(0)` | Entrada de temperatura desde Arduino y salida de prediccion de temperatura. |
| Registro 1 | `FPGA.write(1, ...)` / `FPGA.read(1)` | Entrada de luz desde Arduino y salida de prediccion de luz. |
| Registro 2 | `FPGA.write(2, ...)` | Pulso `temp_data_ready`. |
| Registro 3 | `FPGA.write(3, ...)` | Pulso `Light_data_ready`. |

Este mapeo coincide con `software\arduino\Data_prediction.ino` y `software\arduino\Data_prediction_and_Thingsboard.ino`.

### Estado de validacion

No se ha podido lanzar una validacion HDL real desde consola porque no se han encontrado herramientas como `iverilog`, `verilator` o `quartus_sh` en el `PATH`.

Para poder sintetizar o regenerar el bitstream faltaria confirmar o aportar:

1. Proyecto Quartus (`.qpf`).
2. Constraints de placa y pines (`.qsf`).
3. Constraints de timing (`.sdc`).
4. IP generado de `SYSTEM_PLL`.
5. El modulo correcto `jtag_synchronizer` o adaptar `jtag_interface.v` al sincronizador disponible.
6. Script o flujo para convertir el bitstream generado a `FPGA_Bitstream.h`.

## Comandos utiles

Listar cores instalados:

```powershell
& "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe" core list
```

Listar placa MKR Vidor 4000:

```powershell
& "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe" board listall vidor
```

Compilar `Temperature_real` sin cargar:

```powershell
& "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe" compile --fqbn arduino:samd:mkrvidor4000 .\software\arduino\Temperature_real
```

Compilar `Temperature_real_and_Thingsboard` sin cargar:

```powershell
& "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe" compile --fqbn arduino:samd:mkrvidor4000 .\software\arduino\Temperature_real_and_Thingsboard
```

Comando que no se ha usado porque cargaria el programa en la placa:

```powershell
arduino-cli upload
```
