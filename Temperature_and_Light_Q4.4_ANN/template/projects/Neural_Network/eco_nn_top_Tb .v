
`timescale 1ns / 1ns  

module eco_nn_top_Tb ();


reg   clk,reset,temp_data_ready,Light_data_ready;
reg   [7:0] Temperature_sensor_in, Light_sensor_in;
wire  [7:0] prediction[0:1]; 



//Initialization of the component to be tested

eco_nn_top UUT (
     .clk(clk),
     .reset(reset),
     .Temperature_sensor_in(Temperature_sensor_in), 
     .Light_sensor_in(Light_sensor_in),	  
     .temp_data_ready(temp_data_ready),
	  .Light_data_ready(Light_data_ready),
     .prediction(prediction)
);

//Generation of the clock signal which changes state every 5ns

always begin
  #5 clk = ~clk;
end 



//stimulis generation
initial begin
   clk=0;
	reset =1;
	temp_data_ready=0; Light_data_ready=0;
	// --- Étape 1 : Temp_norm = 0.8777 (0x00E1) | Light_norm = 0.4088 (0x0069) ---
    Temperature_sensor_in = 16'h00fd; Light_sensor_in = 16'h0066;
    #5; 
    temp_data_ready = 1;   Light_data_ready = 1;     
    #10; temp_data_ready = 0;   Light_data_ready = 0;    
 
    // --- Étape 2 : Temp_norm = 0.8769 (0x00E0) | Light_norm = 0.4053 (0x0068) ---
    #10; Temperature_sensor_in = 16'h00fc; Light_sensor_in = 16'h0065; 
    temp_data_ready = 1;   Light_data_ready = 1;     
    #10; temp_data_ready = 0;   Light_data_ready = 0;
    
    // --- Étape 3 : Temp_norm = 0.8761 (0x00E0) | Light_norm = 0.4018 (0x0067) ---
    #10; Temperature_sensor_in = 16'h00fc; Light_sensor_in = 16'h0063;
    temp_data_ready = 1;   Light_data_ready = 1;
    #10; temp_data_ready = 0;   Light_data_ready = 0;
    
    // --- Étape 4 : Temp_norm = 0.8752 (0x00E0) | Light_norm = 0.3984 (0x0066) ---
    #10; Temperature_sensor_in = 16'h00fc; Light_sensor_in = 16'h0064; 
    temp_data_ready = 1;   Light_data_ready = 1;
    #10; temp_data_ready = 0;   Light_data_ready = 0;
    #40;
	 
    //Second windows ------------------------------------------------------------------{0x00a7, 0x00a6, 0x00a5, 0x00a5}, {0x0029, 0x002a, 0x002a, 0x002a}
	 
	 Temperature_sensor_in = 16'h00a7; Light_sensor_in = 16'h0029;
    #5; 
    temp_data_ready = 1;   Light_data_ready = 1;     
    #10; temp_data_ready = 0;   Light_data_ready = 0;    
 
    // --- Étape 2 : Temp_norm = 0.8769 (0x00E0) | Light_norm = 0.4053 (0x0068) ---
    #10; Temperature_sensor_in = 16'h00a6; Light_sensor_in = 16'h002a; 
    temp_data_ready = 1;   Light_data_ready = 1;     
    #10; temp_data_ready = 0;   Light_data_ready = 0;
    
    // --- Étape 3 : Temp_norm = 0.8761 (0x00E0) | Light_norm = 0.4018 (0x0067) ---
    #10; Temperature_sensor_in = 16'h00a5; Light_sensor_in = 16'h002a;
    temp_data_ready = 1;   Light_data_ready = 1;
    #10; temp_data_ready = 0;   Light_data_ready = 0;
    
    // --- Étape 4 : Temp_norm = 0.8752 (0x00E0) | Light_norm = 0.3984 (0x0066) ---
    #10; Temperature_sensor_in = 16'h00a5; Light_sensor_in = 16'h002a; 
    temp_data_ready = 1;   Light_data_ready = 1;
    #10; temp_data_ready = 0;   Light_data_ready = 0;
    #40;
	 
   
	
	

$finish;
end 
endmodule

  