import numpy as np
import pandas as pd
import matplotlib.pyplot as plt 

######################### DATA PART (MIMO VERSION) ######################################################################
######################################################################################################################### 

# --- 1. Convert function Q8.8 -----------------------------------------------------------------------------------
def to_q8_8_hex(value):
    """Converts a floating-point number to Q8.8 signed hexadecimal format (16 bits)"""
    scaled = int(round(value * 256))
    if scaled < 0:
        scaled = (1 << 16) + scaled
    return f"16'h{scaled & 0xFFFF:04X}"

# --- 2. DATA PREPARATION (MIMO: Temperature and Light) -----------------------------------------------------------------
t = np.linspace(0, 100, 1000)
data_temperature = 25 + 5 * np.sin(0.1 * t) + 0.1 * t
# Luce originale (0-1023) normalizzata dividendo per 32.0 (range 0-31.96)
data_light = (1023 * np.maximum(np.sin(0.1 * t), 0)) / 32.0

# Creating sliding windows (Input: 8 elements, Output: 2 elements)
X, y = [], []
for i in range(len(t) - 4):
    Temperature_Window = data_temperature[i:i+4]
    Light_Window = data_light[i:i+4]
    
    # Concatenazione dei due sensori (4 valori T + 4 valori L)
    Input_Window = np.concatenate((Temperature_Window, Light_Window))
    Target = [data_temperature[i+4], data_light[i+4]]
    
    X.append(Input_Window)
    y.append(Target)

X = np.array(X) # Shape: (996, 8)
y = np.array(y) # Shape: (996, 2)

# --- 3. STRUCTURE DOUBLE LIGNE (DECIMAL / HEXA) POUR EXCEL --------------------------------------------------------
excel_rows = []

for i in range(len(X)):
    # Estrazione e arrotondamento dei valori decimali
    inputs_dec = [round(val, 3) for val in X[i]]
    target_temp_dec = round(y[i][0], 3)
    target_light_dec = round(y[i][1], 3)
    
    # Conversione in esadecimale Q8.8
    inputs_hex = [to_q8_8_hex(val) for val in X[i]]
    target_temp_hex = to_q8_8_hex(y[i][0])
    target_light_hex = to_q8_8_hex(y[i][1])
    
    # Ligne 1 : Les valeurs Décimales
    row_dec = {
        "Index / Type": f"Data {i:03d} (Dec)",
        "T_Input 1": inputs_dec[0],
        "T_Input 2": inputs_dec[1],
        "T_Input 3": inputs_dec[2],
        "T_Input 4": inputs_dec[3],
        "L_Input 1": inputs_dec[4],
        "L_Input 2": inputs_dec[5],
        "L_Input 3": inputs_dec[6],
        "L_Input 4": inputs_dec[7],
        "Target Temp Y0": target_temp_dec,
        "Target Light Y1": target_light_dec
    }
    
    # Ligne 2 : Les valeurs Hexadécimales
    row_hex = {
        "Index / Type": f"Data {i:03d} (Hex)",
        "T_Input 1": inputs_hex[0],
        "T_Input 2": inputs_hex[1],
        "T_Input 3": inputs_hex[2],
        "T_Input 4": inputs_hex[3],
        "L_Input 1": inputs_hex[4],
        "L_Input 2": inputs_hex[5],
        "L_Input 3": inputs_hex[6],
        "L_Input 4": inputs_hex[7],
        "Target Temp Y0": target_temp_hex,
        "Target Light Y1": target_light_hex
    }
    
    excel_rows.append(row_dec)
    excel_rows.append(row_hex)

# Conversion en DataFrame Pandas
df = pd.DataFrame(excel_rows)

# --- 4. EXPORTATION VERS EXCEL ET TEXTE ----------------------------------------------------------------------------
nome_file_xlsx = "dataset_mimo_presentation.xlsx"
nome_file_txt = "dataset_mimo_visuel.txt"

df.to_excel(nome_file_xlsx, index=False)
df.to_csv(nome_file_txt, sep="\t", index=False)

print(f"✅ Génération terminée avec succès !")
print(f"   -> Fichier Excel MIMO créé : {nome_file_xlsx}")
print(f"   -> Fichier Texte MIMO créé : {nome_file_txt}")


# --- 5. TRACCIAMENTO DELLE DUE CURVE (MATPLOTLIB) -----------------------------------------------------------
fig, ax1 = plt.subplots(figsize=(11, 5))

# --- Prima Curva: Temperatura (Asse Y a sinistra) ---
color_temp = '#2c3e50'
ax1.set_xlabel('Tempo / Campioni (t)', fontsize=12)
ax1.set_ylabel('Temperatura (°C)', color=color_temp, fontsize=12)
line1 = ax1.plot(t, data_temperature, color=color_temp, linewidth=2.5, 
                 label=r'Temp: $T(t) = 25 + 5 \cdot \sin(0.1 \cdot t) + 0.1 \cdot t$')
ax1.tick_params(axis='y', labelcolor=color_temp)
ax1.grid(True, linestyle='--', alpha=0.5)

# --- Seconda Curva: Luce (Asse Y a destra per via della scala diversa) ---
ax2 = ax1.twinx()  
color_light = '#f39c12' # Colore oro/arancione per la luce
ax2.set_ylabel('Luce Normalizzata (ADC / 32)', color=color_light, fontsize=12)
line2 = ax2.plot(t, data_light, color=color_light, linewidth=2.0, linestyle='-.',
                 label=r'Luce: $L(t) = [1023 \cdot \max(\sin(0.1 \cdot t), 0)] / 32$')
ax2.tick_params(axis='y', labelcolor=color_light)

# Unione delle legende dei due assi in un unico box
lines = line1 + line2
labels = [l.get_label() for l in lines]
ax1.legend(lines, labels, fontsize=10, loc='upper left')

plt.title('Profilo Multivariabile Simulato (Dataset MIMO per FPGA)', fontsize=14, fontweight='bold', pad=15)
plt.tight_layout()

# Salvataggio del grafico ad alta risoluzione
plt.savefig('courbe_mimo_dataset.png', dpi=300)
plt.show()