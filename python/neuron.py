import numpy as np
import tensorflow as tf
import os
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Dense
from sklearn.model_selection import train_test_split

# --- 1. Q8.8 Fixed-Point Conversion Function ---------------------------------------------------------------------

def to_q4_4_hex(value):
    """Converts a floating-point number to Q8.8 signed hexadecimal format (16 bits)"""
    scaled = int(round(value * 16))
    if scaled < 0:
        scaled = (1 << 8) + scaled
    return f"16'h{scaled & 0xFF:02X}"


# --- 2. DATA PREPARATION (Temperature & Light Simulation) --------------------------------------------------------

# Generate continuous time vector
t = np.linspace(0, 100, 1000)

# Simulate Temperature curve (Sine wave + trend)
data_temp = 25 + 5 * np.sin(0.1 * t) + 0.1 * t 

# Simulate Light Intensity curve (Lux) (Phase-shifted sine wave to simulate day/night cycles)
data_light = 500 + 400 * np.sin(0.1 * t + 1.5) + 2 * t
# Normalize Temperature dataset (0 to 1)
temp_min, temp_max = np.min(data_temp), np.max(data_temp)
temp_norm = (data_temp - temp_min) / (temp_max - temp_min)

# Normalize Light dataset (0 to 1) separately
light_min, light_max = np.min(data_light), np.max(data_light)
light_norm = (data_light - light_min) / (light_max - light_min)

# Initialize empty lists for sliding windows
X_norm, y_norm = [], []
X_raw, y_raw = [], []

# Build windows: Input = 4 past Temps + 4 past Lights (8 features) -> Output = Next Temp + Next Light (2 targets)
for i in range(len(t) - 4):
    # Normalized features and targets for AI training
    normalized_features = np.concatenate([temp_norm[i:i+4], light_norm[i:i+4]])
    normalized_targets = [temp_norm[i+4], light_norm[i+4]]
    X_norm.append(normalized_features)
    y_norm.append(normalized_targets)
    
    # Raw features and targets for validation and terminal display
    raw_features = np.concatenate([data_temp[i:i+4], data_light[i:i+4]])
    raw_targets = [data_temp[i+4], data_light[i+4]]
    X_raw.append(raw_features)
    y_raw.append(raw_targets)

# Convert to structured NumPy arrays
X_norm = np.array(X_norm)   # Shape: (996, 8)
y_norm = np.array(y_norm)   # Shape: (996, 2)
X_raw = np.array(X_raw)     # Shape: (996, 8)
y_raw = np.array(y_raw)     # Shape: (996, 2)

# Synchronized Train/Test Splitting (80% train, 20% test)
X_train, X_test, y_train, y_test = train_test_split(
    X_norm, y_norm, test_size=0.2, shuffle=True, random_state=42
) 

X_train_brut, X_test_brut, y_train_brut, y_test_brut = train_test_split(
    X_raw, y_raw, test_size=0.2, shuffle=True, random_state=42
)


# --- 3. NEURAL NETWORK ARCHITECTURE & TRAINING (MIMO) ------------------------------------------------------------

nome_modello = "model_multisensor_fpga.keras"

if os.path.exists(nome_modello):
    print(f"📂 Saved model found! Loading '{nome_modello}'...")
    model = load_model(nome_modello)
else:
    print(f"🧠 No saved model found under '{nome_modello}'. Training begins...")
    
    # Multilayer Perceptron designed for multi-sensor hardware mapping
    model = Sequential([
        # Hidden layer with 16 neurons to process the 8 mixed inputs (4 Temp + 4 Light)
        Dense(16, activation='relu', input_shape=(8,), name="hidden_layer"),
        # Output layer with 2 neurons: Neuron 0 predicts Temp, Neuron 1 predicts Light
        Dense(2, name="output_layer")
    ])

    model.compile(optimizer='adam', loss='mse')
    print("Training Multi-Sensor Network in progress...")
    model.fit(X_train, y_train, epochs=120, verbose=1)
    model.save(nome_modello)
    print(f"✅ Training complete and model saved under '{nome_modello}'")


# --- 4. HARDWARE EXPORT: GENERATING VERILOG PARAMETER CONSTANTS -------------------------------------------------

nome_file_parametri = "params_neural_net.txt" 

with open(nome_file_parametri, "w", encoding="utf-8") as f:
    f.write("// =====================================================================\n")
    f.write("// Weights and biases converted for FPGA multi-sensor network (Q8.8 format)\n")
    f.write(f"// Inputs: 0-3 = Temp, 4-7 = Light | Outputs: 0 = Temp, 1 = Light\n")
    f.write(f"// Source Model: {nome_modello}\n")
    f.write("// =====================================================================\n\n")

    for layer in model.layers:
        weights, biases = layer.get_weights()
        layer_name = layer.name
        f.write(f"// --- {layer_name.upper()} ---\n")
        
        num_inputs = weights.shape[0]
        num_neurons = weights.shape[1]
        
        for n in range(num_neurons):
            w_hex = [to_q4_4_hex(weights[i, n]) for i in range(num_inputs)]
            b_hex = to_q4_4_hex(biases[n])
            f.write(f"// Neurone {n}\n")
            f.write(f"  assign w_{layer_name}[{n}] [0:{num_inputs-1}] = '{{ {', '.join(w_hex)} }};\n")
            f.write(f"  assign b_{layer_name}[{n}] = {b_hex};\n\n")

print(f"✅ Success! The Verilog constants have been recorded in : {nome_file_parametri}")


# --- 5. VALIDATION, SEPARATED METRICS & SYNCHRONIZED DISPLAY -----------------------------------------------------

# Generate model predictions on the multi-sensor test dataset
y_pred_norm = model.predict(X_test)  # Returns a 2D array of shape (N, 2)

# Denormalize predictions row by row using respective scales
y_pred_real = np.zeros_like(y_pred_norm)
y_pred_real[:, 0] = y_pred_norm[:, 0] * (temp_max - temp_min) + temp_min   # Temp denorm
y_pred_real[:, 1] = y_pred_norm[:, 1] * (light_max - light_min) + light_min # Light denorm

# Isolate columns for accurate, distinct metrics calculation
y_test_temp, y_pred_temp = y_test_brut[:, 0], y_pred_real[:, 0]
y_test_light, y_pred_light = y_test_brut[:, 1], y_pred_real[:, 1]

# Calculate separate Mean Squared Errors
mse_temp = np.mean((y_test_temp - y_pred_temp) ** 2)
mse_light = np.mean((y_test_light - y_pred_light) ** 2)

print("\n=======================================================")
print("             MULTI-SENSOR PERFORMANCE METRICS          ")
print("=======================================================")
print(f"Temperature - Mean Squared Error (MSE) : {mse_temp:.6f} (°C²)")
print(f"Light Intensity - Mean Squared Error (MSE) : {mse_light:.6f} (Lux²)")
print("=======================================================\n")

print("--- RESULTS ON 5 MULTI-SENSOR TEST WINDOWS ---")

for i in range(5):
    # Slice the 8-element window into readable parts
    past_temps = np.round(X_test_brut[i, 0:4], 3)
    past_lights = np.round(X_test_brut[i, 4:8], 3)
    
    print(f"\nTest Input Sample {i+1}:")
    print(f"   [Past Temperatures] : {past_temps} °C")
    print(f"   [Past Light Lux]    : {past_lights} Lux")
    print(f" -> Real Target Temp    : {y_test_temp[i]:.3f} °C  | Predicted : {y_pred_temp[i]:.3f} °C")
    print(f" -> Real Target Light   : {y_test_light[i]:.3f} Lux | Predicted : {y_pred_light[i]:.3f} Lux")


print(temp_min)
print(temp_max)
print(light_max)
print(light_min)
