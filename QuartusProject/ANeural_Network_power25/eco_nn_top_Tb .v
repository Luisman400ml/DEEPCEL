
`timescale 1ns / 1ns  

module eco_nn_top_Tb ();


reg   clk,reset,data_ready;
reg   [15:0] sensor_in;
wire  [15:0] prediction ; 



//Initialization of the component to be tested

eco_nn_top UUT (
     .clk(clk),
     .reset(reset),
     .sensor_in(sensor_in),    
     .data_ready(data_ready),
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
	data_ready=0;
	//*********************** first input data window************************************************
	
	sensor_in = 16'h1900; // Step 1( send the first temperature value) : 25.00
	#5 
	data_ready =1;       // the FPGA can read this value 
	#10 data_ready=0;    // stop reading new value sending
 
	#10 sensor_in = 16'h190F; // step 2 : 25.06
	    data_ready =1;
	#10 data_ready=0;
   #10 sensor_in = 16'h191F; // step 3 : 25.12
	    data_ready =1;
	#10 data_ready=0;
   #10 sensor_in = 16'h192E; // step 4 : 25.18-----> prediction target : 25.24, model_sim_prediction: 6438/256 =25,148 (16h'1926)
	    data_ready=1;
   #10 data_ready =0;
   #40
	
	
	//*********************second input data window*******************
    sensor_in = 16'h193D; 
	 data_ready =1 ;//   actual temperature data :25.24 ----> prediction target: 25.3 , model_sim : 6452/256=25,203 (16h'1934)
	#10 data_ready=0;
	#40
	
	//*********************thirth input data window*******************
    sensor_in = 16'h194D; 
	 data_ready =1 ;//   actual temperature data :25.3 ----> prediction target: 25.36 , model_sim : 6452/256=25,203 (16h'1934)
	#10 data_ready=0;
	#40

$finish;
end 
endmodule

  