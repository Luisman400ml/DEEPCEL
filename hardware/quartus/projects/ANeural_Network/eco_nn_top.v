module eco_nn_top (
    input clk,
    input reset,
    input [15:0] sensor_in,     // Sensor data (Q8.8)
    input data_ready,           // SAMD21 Trigger
    output [15:0] prediction    //Final predicted value
);

    // 1. Sliding window (Shift Register)
    reg signed [15:0] window [0:3];
    always @(posedge clk) begin
        if (!reset) begin
            window[0] <= 0; window[1] <= 0; window[2] <= 0; window[3] <= 0;
        end else if (data_ready) begin
            window[3] <= sensor_in;
            window[2] <= window[3];
            window[1] <= window[2];
            window[0] <= window[1];
        end
    end
    // 2. Declaration of Weights and Biases
    // We create a weight array for the 8 neurons of the hidden layer
    wire signed [15:0] w_hidden_layer [0:7][0:3]; 
    wire signed [15:0] b_hidden_layer [0:7];

   
	 /// Neurone 0
assign w_hidden_layer[0] = '{ 16'hFF63, 16'h0005, 16'hFF72, 16'hFFAC };
assign b_hidden_layer[0]= 16'h0000;

// Neurone 1
assign w_hidden_layer[1] = '{ 16'hFFB2, 16'h0085, 16'h00BD, 16'h0073 };
assign b_hidden_layer[1]= 16'hFFF5;

// Neurone 2
assign w_hidden_layer[2] = '{ 16'h0000, 16'h005C, 16'h000A, 16'h007D };
assign b_hidden_layer[2]= 16'hFFE3;

// Neurone 3
assign w_hidden_layer[3] = '{ 16'hFFB0, 16'hFF66, 16'hFF6E, 16'hFF97 };
assign b_hidden_layer[3]= 16'h0000;

// Neurone 4
assign w_hidden_layer[4] = '{ 16'hFFC8, 16'hFF6B, 16'h0040, 16'h0032 };
assign b_hidden_layer[4]= 16'hFFFF;

// Neurone 5
assign w_hidden_layer[5] = '{ 16'hFF9A, 16'hFFCB, 16'h0016, 16'hFFC7 };
assign b_hidden_layer[5]= 16'h0000;

// Neurone 6
assign w_hidden_layer[6] = '{ 16'h0099, 16'h0027, 16'h005C, 16'h0014 };
assign b_hidden_layer[6]= 16'hFFF1;

// Neurone 7
assign w_hidden_layer[7] = '{ 16'hFF6A, 16'h0045, 16'hFFAD, 16'hFF5D };
assign b_hidden_layer[7]= 16'h0000;





// 3.--------------------- Hidden Layer (8 neurons)------------------------------------------------------------------------------------
    wire signed [15:0] hidden_outs [0:7]; // The 8 outputs of hidden neurons

    genvar i;
    generate
        for (i = 0; i < 8; i = i + 1) begin : hidden_layer
            neuron #(4) h_neuron (
                .clk(clk),
                .reset(reset),
                //.inputs('{window[3],window[2],window[1],window[0]}),
					 .inputs(window),
                .weights( w_hidden_layer[i]),
                .bias(b_hidden_layer[i]),
                .out(hidden_outs[i])
            );
        end
    endgenerate
 // 4.----------------- Output Layer (1 neurone qui agrège les 8 sorties)-------------------------------------------
    // Weights and biases for the output neuron
	 
	 // Neurone 0
wire signed [15:0]  w_output_layer[0:7] = '{ 16'h0002, 16'h007D, 16'hFF8B, 16'h0018, 16'h00AE, 16'h00B2, 16'h0099, 16'hFF58 };


wire signed [15:0]  b_output_layer= 16'h0004;



    neuron #(8) final_neuron (
        .clk(clk),
        .reset(reset),
        .inputs(hidden_outs),// Receives the 8 outputs from the previous layer
        .weights(w_output_layer),
        .bias(b_output_layer),
        .out(prediction)
    );

endmodule