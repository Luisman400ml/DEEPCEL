module eco_nn_top (
    input clk,
    input reset,
    input [15:0] Temperature_sensor_in,     // Sensor data (Q8.8)
	 input [15:0] Light_sensor_in,  
    input temp_data_ready,  
	 input Light_data_ready,    // SAMD21 Trigger
    output [15:0] prediction[0:1]    //Finals predicted values
);

    // 1. Sliding window (Shift Register)
    reg signed [15:0] window [0:7];
	 
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
    wire signed [15:0] w_hidden_layer [0:15][0:7]; 
    wire signed [15:0] b_hidden_layer [0:15];

   // Neurone 0
  assign w_hidden_layer[0] [0:7] = '{ 16'h0047, 16'h0073, 16'hFFBF, 16'h0010, 16'h0097, 16'h006E, 16'h0090, 16'hFFE1 };
  assign b_hidden_layer[0] = 16'hFFFF;

// Neurone 1
  assign w_hidden_layer[1] [0:7] = '{ 16'hFFB6, 16'hFFB6, 16'h0050, 16'h003C, 16'h003B, 16'hFFB0, 16'hFFAE, 16'h0061 };
  assign b_hidden_layer[1] = 16'h0000;

// Neurone 2
  assign w_hidden_layer[2] [0:7] = '{ 16'hFFDE, 16'hFFBA, 16'hFFBB, 16'h000F, 16'hFFCA, 16'hFFC0, 16'h0029, 16'h0045 };
  assign b_hidden_layer[2] = 16'hFFFD;

// Neurone 3
  assign w_hidden_layer[3] [0:7] = '{ 16'h004D, 16'hFFC9, 16'hFFE1, 16'h000D, 16'hFFDC, 16'hFFD2, 16'hFFC8, 16'hFFA6 };
  assign b_hidden_layer[3] = 16'hFFFC;

// Neurone 4
  assign w_hidden_layer[4] [0:7] = '{ 16'h002E, 16'hFFB5, 16'hFFDB, 16'hFFFD, 16'h005F, 16'hFFB0, 16'hFFB1, 16'h000C };
  assign b_hidden_layer[4] = 16'h0000;

// Neurone 5
  assign w_hidden_layer[5] [0:7] = '{ 16'hFFCD, 16'hFF86, 16'h0059, 16'hFF82, 16'hFFED, 16'hFFE7, 16'h004A, 16'hFFD6 };
  assign b_hidden_layer[5] = 16'h0000;

// Neurone 6
  assign w_hidden_layer[6] [0:7] = '{ 16'h0048, 16'h00A2, 16'h002A, 16'h0030, 16'hFFBE, 16'h003E, 16'h0054, 16'hFF86 };
  assign b_hidden_layer[6] = 16'h0013;

// Neurone 7
  assign w_hidden_layer[7] [0:7] = '{ 16'hFFEE, 16'h002B, 16'hFF89, 16'hFFDF, 16'h0038, 16'hFFAE, 16'hFFC8, 16'hFFCE };
  assign b_hidden_layer[7] = 16'h0000;

// Neurone 8
  assign w_hidden_layer[8] [0:7] = '{ 16'hFFB4, 16'h0046, 16'h0059, 16'hFFA0, 16'h007D, 16'h0091, 16'hFFD2, 16'h0098 };
  assign b_hidden_layer[8] = 16'h0008;

// Neurone 9
  assign w_hidden_layer[9] [0:7] = '{ 16'hFF9A, 16'h0007, 16'h0028, 16'h0077, 16'h004D, 16'hFFFD, 16'hFFE4, 16'h0038 };
  assign b_hidden_layer[9] = 16'hFFF2;

// Neurone 10
  assign w_hidden_layer[10] [0:7] = '{ 16'h0071, 16'h006B, 16'h003C, 16'hFFDB, 16'h0024, 16'hFFE8, 16'h0053, 16'h0024 };
  assign b_hidden_layer[10] = 16'hFFF5;

// Neurone 11
  assign w_hidden_layer[11] [0:7] = '{ 16'h001A, 16'h0008, 16'h0002, 16'hFFCB, 16'hFFD9, 16'hFFAC, 16'hFFF6, 16'hFF92 };
  assign b_hidden_layer[11] = 16'h0000;

// Neurone 12
  assign w_hidden_layer[12] [0:7] = '{ 16'h0068, 16'hFF84, 16'h0024, 16'hFFBA, 16'hFFA4, 16'h0030, 16'hFF96, 16'hFFDD };
  assign b_hidden_layer[12] = 16'h0000;

// Neurone 13
  assign w_hidden_layer[13] [0:7] = '{ 16'hFF97, 16'hFFC9, 16'h0004, 16'hFFCD, 16'hFFB3, 16'hFF93, 16'hFFD3, 16'hFFEB };
  assign b_hidden_layer[13] = 16'h0000;

// Neurone 14
  assign w_hidden_layer[14] [0:7] = '{ 16'hFF97, 16'h001A, 16'hFFCB, 16'hFFAC, 16'hFFBB, 16'hFFE1, 16'h0040, 16'hFFD9 };
  assign b_hidden_layer[14] = 16'h0000;

// Neurone 15
  assign w_hidden_layer[15] [0:7] = '{ 16'hFF97, 16'h0029, 16'h000C, 16'hFFA9, 16'hFFA2, 16'hFFFB, 16'h0007, 16'hFFDB };
  assign b_hidden_layer[15] = 16'h0000;



// 3.--------------------- Hidden Layer (8 neurons)------------------------------------------------------------------------------------
    wire signed [15:0] hidden_outs [0:15]; // The 16 outputs of hidden neurons

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
  
	 wire signed [15:0]  w_output_layer[0:1][0:15] ;
	 wire signed [15:0]  b_output_layer[0:1];
// Neurone 0
  assign w_output_layer[0] [0:15] = '{ 16'h0017, 16'hFFAC, 16'h0064, 16'hFFE0, 16'h002B, 16'hFFC6, 16'h0095, 16'h0093, 16'hFFDD, 16'h004B, 16'h0023, 16'hFFF4, 16'h003B, 16'hFFCB, 16'h001A, 16'h0090 };
  assign b_output_layer[0] = 16'hFFFA;

// Neurone 1
  assign w_output_layer[1] [0:15] = '{ 16'h0051, 16'hFFE3, 16'hFF97, 16'hFF7A, 16'hFFB8, 16'hFF83, 16'hFFB1, 16'h0079, 16'h0050, 16'hFFB3, 16'h004F, 16'hFFE8, 16'h007E, 16'h0046, 16'hFFD8, 16'h002E };
  assign b_output_layer[1] = 16'h0004;



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