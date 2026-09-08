module eco_nn_top (
    input clk,
    input reset,
    input [7:0] Temperature_sensor_in,     // Sensor data (Q4.84)
	 input [7:0] Light_sensor_in,  
    input temp_data_ready,  
	 input Light_data_ready,    // SAMD21 Trigger
    output [7:0] prediction[0:1]    //Finals predicted values
);

    // 1. Sliding window (Shift Register)
    reg signed [7:0] window [0:7];
	 
    always @(posedge clk) begin//-----TEMPERATURE DATA
        if (!reset) begin
            window[0] <= 0; window[1] <= 0; window[2] <= 0; window[3] <= 0;
        end else if (temp_data_ready) begin
            window[3] <= Temperature_sensor_in;
            window[2] <= window[3];
            window[1] <= window[2];
            window[0] <= window[1];
        end
    end
	 
	 
	 always @(posedge clk) begin //--------LIGHT DATA
        if (!reset) begin
            window[4] <= 0; window[5] <= 0; window[6] <= 0; window[7] <= 0;
        end else if (Light_data_ready) begin
            window[7] <= Light_sensor_in;
            window[6] <= window[7];
            window[5] <= window[6];
            window[4] <= window[5];
        end
    end
	 
    // 2. Declaration of Weights and Biases
    // We create a weight array for the 16 neurons of the hidden layer
    wire signed [7:0] w_hidden_layer [0:15][0:7]; 
    wire signed [7:0] b_hidden_layer [0:15];

   // Neurone 0
  assign w_hidden_layer[0] [0:7] = '{ 16'hFB, 16'hFD, 16'h09, 16'h05, 16'hFF, 16'hFF, 16'hFF, 16'hFE };
  assign b_hidden_layer[0] = 16'h03;

// Neurone 1
  assign w_hidden_layer[1] [0:7] = '{ 16'hFD, 16'h02, 16'hFE, 16'h05, 16'hF9, 16'hFB, 16'h03, 16'hFC };
  assign b_hidden_layer[1] = 16'hFF;

// Neurone 2
  assign w_hidden_layer[2] [0:7] = '{ 16'h07, 16'h05, 16'h03, 16'h02, 16'hFE, 16'h00, 16'hFE, 16'h04 };
  assign b_hidden_layer[2] = 16'hFF;

// Neurone 3
  assign w_hidden_layer[3] [0:7] = '{ 16'hFD, 16'h05, 16'h05, 16'hF9, 16'hFB, 16'h01, 16'h02, 16'hFF };
  assign b_hidden_layer[3] = 16'h00;

// Neurone 4
  assign w_hidden_layer[4] [0:7] = '{ 16'h08, 16'h03, 16'hFD, 16'hFE, 16'h03, 16'hFA, 16'h07, 16'hF9 };
  assign b_hidden_layer[4] = 16'h02;

// Neurone 5
  assign w_hidden_layer[5] [0:7] = '{ 16'h02, 16'hF9, 16'hFC, 16'h02, 16'hF9, 16'h06, 16'h06, 16'hF9 };
  assign b_hidden_layer[5] = 16'h00;

// Neurone 6
  assign w_hidden_layer[6] [0:7] = '{ 16'h05, 16'h02, 16'hFD, 16'h08, 16'h00, 16'h09, 16'h03, 16'h00 };
  assign b_hidden_layer[6] = 16'h01;

// Neurone 7
  assign w_hidden_layer[7] [0:7] = '{ 16'hFD, 16'h05, 16'hFA, 16'hFF, 16'h03, 16'h03, 16'hFF, 16'h05 };
  assign b_hidden_layer[7] = 16'h01;

// Neurone 8
  assign w_hidden_layer[8] [0:7] = '{ 16'h00, 16'h02, 16'h00, 16'h01, 16'hFE, 16'h03, 16'h05, 16'h00 };
  assign b_hidden_layer[8] = 16'hFF;

// Neurone 9
  assign w_hidden_layer[9] [0:7] = '{ 16'h02, 16'h02, 16'h00, 16'hFC, 16'hFC, 16'h09, 16'h06, 16'h00 };
  assign b_hidden_layer[9] = 16'h01;

// Neurone 10
  assign w_hidden_layer[10] [0:7] = '{ 16'h02, 16'hFF, 16'hFA, 16'h08, 16'h00, 16'hFA, 16'h04, 16'h08 };
  assign b_hidden_layer[10] = 16'h01;

// Neurone 11
  assign w_hidden_layer[11] [0:7] = '{ 16'hF9, 16'hFB, 16'h05, 16'hFA, 16'h03, 16'h02, 16'h02, 16'hFD };
  assign b_hidden_layer[11] = 16'hFF;

// Neurone 12
  assign w_hidden_layer[12] [0:7] = '{ 16'hF9, 16'hFD, 16'h02, 16'hF8, 16'h05, 16'h06, 16'h01, 16'hF9 };
  assign b_hidden_layer[12] = 16'hFE;

// Neurone 13
  assign w_hidden_layer[13] [0:7] = '{ 16'h00, 16'h06, 16'hFA, 16'hFB, 16'h00, 16'hFF, 16'hFE, 16'hFA };
  assign b_hidden_layer[13] = 16'h00;

// Neurone 14
  assign w_hidden_layer[14] [0:7] = '{ 16'hF9, 16'hFA, 16'h04, 16'h05, 16'hFC, 16'h06, 16'hFE, 16'h01 };
  assign b_hidden_layer[14] = 16'h00;

// Neurone 15
  assign w_hidden_layer[15] [0:7] = '{ 16'h01, 16'h07, 16'hFD, 16'h03, 16'h01, 16'h04, 16'hFF, 16'h08 };
  assign b_hidden_layer[15] = 16'h01;


// 3.--------------------- Hidden Layer (8 neurons)------------------------------------------------------------------------------------
    wire signed [7:0] hidden_outs [0:15]; // The 16 outputs of hidden neurons

    genvar i;
    generate
        for (i = 0; i < 16; i = i + 1) begin : hidden_layer
            neuron #(8) h_neuron (
                .clk(clk),
                .reset(reset),
                //.inputs('{window[3],window[2],window[1],window[0]}),
					 .inputs(window),
                .weights(w_hidden_layer[i]),
                .bias(b_hidden_layer[i]),
                .out(hidden_outs[i])
            );
        end
    endgenerate
 // 4.----------------- Output Layer (2 neurone qui agrège les 16 sorties)-------------------------------------------
    // Weights and biases for the output neuron
  
	 wire signed [7:0]  w_output_layer[0:1][0:15] ;
	 wire signed [7:0]  b_output_layer[0:1];
// Neurone 0
  assign w_output_layer[0] [0:15] = '{ 16'h05, 16'hF7, 16'h06, 16'h05, 16'h04, 16'h04, 16'h00, 16'hF8, 16'h06, 16'hFE, 16'h02, 16'hFE, 16'h04, 16'h01, 16'hF7, 16'h07 };
  assign b_output_layer[0] = 16'hFF;

// Neurone 1
  assign w_output_layer[1] [0:15] = '{ 16'hF8, 16'h07, 16'h00, 16'hF8, 16'hFD, 16'hF9, 16'h04, 16'h07, 16'hFB, 16'h04, 16'h05, 16'h00, 16'h01, 16'h06, 16'hF8, 16'h04 };
  assign b_output_layer[1] = 16'h01;


	 genvar j;
	 generate
	     for(j = 0; j < 2; j = j+1) begin: output_layer
	  
           neuron #(16) final_neuron (
              .clk(clk),
              .reset(reset),
              .inputs(hidden_outs),// Receives the 16 outputs from the previous layer
              .weights(w_output_layer[j]),
              .bias(b_output_layer[j]),
              .out(prediction[j])
	
          );
		 end 
	  endgenerate

endmodule