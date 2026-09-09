# Estrategias de bajo consumo para DEEPCEL

Este documento lista estrategias para reducir el consumo del proyecto FPGA manteniendo la funcionalidad: captura de temperatura, humedad, luz y predicciones de temperatura/luz desde la red neuronal.

## 1. Red neuronal activa por rafagas

La FPGA debe cargar las muestras de temperatura y luz, actualizar sus ventanas historicas y activar la red neuronal solo cuando el par de muestras este completo. En el diseno anterior, la red podia recalcular al llegar temperatura y volver a recalcular al llegar luz. Con rafagas, la inferencia se ejecuta una sola vez por muestra completa.

Estado: implementada primero sobre `hardware/quartus/projects/ANeural_Network_power25_lowpower_light_q4_4` y mantenida en la variante recomendada `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz`.

Resultado aplicado: el RTL guarda flags de temperatura y luz pendientes, actualiza las dos ventanas historicas y solo lanza la inferencia cuando ambas muestras del par estan disponibles. La validacion hardware paso `SELFTEST PASS multisensor_q4_4 vectors=128 reads=512 failures=0`.

Nota de medida: el Power Analyzer actual sigue usando actividad vectorless con confianza baja. Por eso la estimacion puede no reflejar la reduccion real de conmutacion temporal conseguida al pasar de dos activaciones a una activacion por par temperatura/luz.

## 2. Bajar la frecuencia de la red neuronal

La aplicacion mide cada 10 segundos, por lo que la red no necesita funcionar a decenas de MHz durante toda la ejecucion. Se puede usar un reloj mas lento para la red o una estrategia de reloj derivado con habilitacion controlada.

Estado: implementada sobre la variante `hardware/quartus/projects/ANeural_Network_power25_lowpower_light_q4_4_lowfreq_6mhz` y llevada a 1 MHz en `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz`.

Cambio aplicado: la salida `c0` del PLL usada por `wNN_CLK` pasa de 24 MHz a 6 MHz (`clk0_divide_by = 8`). La interfaz JTAG mantiene `wCLK120`, el intervalo de muestreo sigue en 10 segundos y la red conserva el modo rafaga del punto 1. La latencia de inferencia sigue siendo despreciable frente al muestreo: dos ciclos de red a 6 MHz son aproximadamente 0.33 us, y Arduino espera 10 ms antes de leer la prediccion.

Comparativa Quartus Power Analyzer:

| Variante | Reloj NN | Potencia total | Core dinamica | Dominio NN `clk[0]` |
|---|---:|---:|---:|---:|
| `ANeural_Network_power25_lowpower_light_q4_4` | 24 MHz | 212.19 mW | 24.23 mW | 18.93 mW |
| `ANeural_Network_power25_lowpower_light_q4_4_lowfreq_6mhz` | 6 MHz | 206.64 mW | 18.77 mW | 14.23 mW |

Validacion: compilacion Quartus completa con `0 errors`, timing cerrado y carga en MKR Vidor 4000 por `COM4`. El comando serie `T` devuelve `SELFTEST PASS multisensor_q4_4 vectors=128 reads=512 failures=0` y el sketch sigue mostrando `TemperatureHistory_C`, `LightHistory_ADC`, `Temperature_C`, `Light_ADC`, `PredictionTemperature_C`, `PredictionLight_model` y `Humidity_pct`.

Nota de medida: la confianza del Power Analyzer sigue siendo `Low` porque no hay actividad real VCD/SAIF. La comparativa es util porque ambas variantes usan la misma metodologia vectorless, pero no sustituye una medida electrica real en placa.

## 3. Clock enable mas agresivo

Congelar registros internos, salidas y acumuladores cuando no hay inferencia valida. Esto reduce conmutacion interna sin cambiar resultados.

Estado: integrado en la variante ultralow-power mediante una FSM que solo actualiza acumuladores, indices y salidas durante la inferencia. Fuera de rafaga, la red conserva su prediccion previa.

## 4. Arquitectura secuencial con MAC reutilizado

Sustituir parte del paralelismo por una unidad multiply-accumulate reutilizada durante varios ciclos. La latencia adicional seria despreciable frente al intervalo de muestreo.

Estado: implementado en `hardware/quartus/projects/ANeural_Network_power25_ultralowpower_light_q4_4_seq_1mhz/eco_nn_top.v`. Se probo una version de un unico multiplicador, pero Quartus estimo `201.89 mW`, peor que los `201.78 mW` de la version final con dos multiplicadores, asi que se mantuvo la opcion mas eficiente estimada.

## 5. Reducir conmutacion combinacional

Mantener entradas estables, evitar cambios innecesarios en buses y registrar senales intermedias para que multiplicadores/sumadores no conmuten fuera de la ventana de calculo.

## 6. Revisar precision fija

Validar si algunas rutas admiten menos bits internos o saturacion controlada sin cambiar la funcionalidad observable. Cualquier cambio debe comprobarse contra el modelo de referencia.

## 7. Eliminar o fijar IP y pines no usados

Revisar HDMI, SDRAM, MIPI, flash y pines de plantilla MKR para dejarlos en estados definidos y con minima actividad.

Estado: aplicado en el top minimo de la variante ultralow-power. El puente JTAG se conserva a 120 MHz por compatibilidad, y la red usa 1 MHz.

## 8. Constraints de pines no usados

Definir comportamiento de pines no utilizados: tri-state, sin pull-ups innecesarios y drive strength bajo cuando aplique.

## 9. Power Analyzer con actividad real

Usar VCD/SAIF o actividad representativa de la aplicacion. Los reportes vectorless tienen confianza baja y pueden ocultar donde esta realmente el consumo dinamico.

## 10. Separar modo diagnostico y modo normal

El selftest y las capturas diagnosticas deben activarse solo bajo comando serie. En modo normal conviene minimizar trabajo extra en Arduino y FPGA.
