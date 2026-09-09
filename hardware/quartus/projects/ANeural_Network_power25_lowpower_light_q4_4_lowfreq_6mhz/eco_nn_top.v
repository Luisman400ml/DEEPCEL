module eco_nn_top (
    input clk,
    input reset,
    input [7:0] temperature_sensor_in,
    input [7:0] light_sensor_in,
    input temp_data_ready,
    input light_data_ready,
    output [7:0] prediction_temperature,
    output [7:0] prediction_light
);

    reg signed [7:0] window [0:7];

    reg temp_ready_meta;
    reg temp_ready_sync;
    reg temp_ready_d;
    reg light_ready_meta;
    reg light_ready_sync;
    reg light_ready_d;
    reg temp_pending;
    reg light_pending;
    reg hidden_enable;
    reg output_enable;

    wire temp_sample_pulse = temp_ready_sync & ~temp_ready_d;
    wire light_sample_pulse = light_ready_sync & ~light_ready_d;
    wire inference_start = (temp_pending | temp_sample_pulse) & (light_pending | light_sample_pulse);

    always @(posedge clk) begin
        if (!reset) begin
            temp_ready_meta <= 1'b0;
            temp_ready_sync <= 1'b0;
            temp_ready_d <= 1'b0;
            light_ready_meta <= 1'b0;
            light_ready_sync <= 1'b0;
            light_ready_d <= 1'b0;
            temp_pending <= 1'b0;
            light_pending <= 1'b0;
            hidden_enable <= 1'b0;
            output_enable <= 1'b0;
        end else begin
            temp_ready_meta <= temp_data_ready;
            temp_ready_sync <= temp_ready_meta;
            temp_ready_d <= temp_ready_sync;
            light_ready_meta <= light_data_ready;
            light_ready_sync <= light_ready_meta;
            light_ready_d <= light_ready_sync;

            if (inference_start) begin
                temp_pending <= 1'b0;
                light_pending <= 1'b0;
            end else begin
                if (temp_sample_pulse) begin
                    temp_pending <= 1'b1;
                end
                if (light_sample_pulse) begin
                    light_pending <= 1'b1;
                end
            end

            hidden_enable <= inference_start;
            output_enable <= hidden_enable;
        end
    end

    always @(posedge clk) begin
        if (!reset) begin
            window[0] <= 8'sd0;
            window[1] <= 8'sd0;
            window[2] <= 8'sd0;
            window[3] <= 8'sd0;
        end else if (temp_sample_pulse) begin
            window[3] <= temperature_sensor_in;
            window[2] <= window[3];
            window[1] <= window[2];
            window[0] <= window[1];
        end
    end

    always @(posedge clk) begin
        if (!reset) begin
            window[4] <= 8'sd0;
            window[5] <= 8'sd0;
            window[6] <= 8'sd0;
            window[7] <= 8'sd0;
        end else if (light_sample_pulse) begin
            window[7] <= light_sensor_in;
            window[6] <= window[7];
            window[5] <= window[6];
            window[4] <= window[5];
        end
    end

    wire signed [7:0] w_hidden_layer [0:15][0:7];
    wire signed [7:0] b_hidden_layer [0:15];

    assign w_hidden_layer[0]  = '{ 8'hFB, 8'hFD, 8'h09, 8'h05, 8'hFF, 8'hFF, 8'hFF, 8'hFE };
    assign b_hidden_layer[0]  = 8'h03;
    assign w_hidden_layer[1]  = '{ 8'hFD, 8'h02, 8'hFE, 8'h05, 8'hF9, 8'hFB, 8'h03, 8'hFC };
    assign b_hidden_layer[1]  = 8'hFF;
    assign w_hidden_layer[2]  = '{ 8'h07, 8'h05, 8'h03, 8'h02, 8'hFE, 8'h00, 8'hFE, 8'h04 };
    assign b_hidden_layer[2]  = 8'hFF;
    assign w_hidden_layer[3]  = '{ 8'hFD, 8'h05, 8'h05, 8'hF9, 8'hFB, 8'h01, 8'h02, 8'hFF };
    assign b_hidden_layer[3]  = 8'h00;
    assign w_hidden_layer[4]  = '{ 8'h08, 8'h03, 8'hFD, 8'hFE, 8'h03, 8'hFA, 8'h07, 8'hF9 };
    assign b_hidden_layer[4]  = 8'h02;
    assign w_hidden_layer[5]  = '{ 8'h02, 8'hF9, 8'hFC, 8'h02, 8'hF9, 8'h06, 8'h06, 8'hF9 };
    assign b_hidden_layer[5]  = 8'h00;
    assign w_hidden_layer[6]  = '{ 8'h05, 8'h02, 8'hFD, 8'h08, 8'h00, 8'h09, 8'h03, 8'h00 };
    assign b_hidden_layer[6]  = 8'h01;
    assign w_hidden_layer[7]  = '{ 8'hFD, 8'h05, 8'hFA, 8'hFF, 8'h03, 8'h03, 8'hFF, 8'h05 };
    assign b_hidden_layer[7]  = 8'h01;
    assign w_hidden_layer[8]  = '{ 8'h00, 8'h02, 8'h00, 8'h01, 8'hFE, 8'h03, 8'h05, 8'h00 };
    assign b_hidden_layer[8]  = 8'hFF;
    assign w_hidden_layer[9]  = '{ 8'h02, 8'h02, 8'h00, 8'hFC, 8'hFC, 8'h09, 8'h06, 8'h00 };
    assign b_hidden_layer[9]  = 8'h01;
    assign w_hidden_layer[10] = '{ 8'h02, 8'hFF, 8'hFA, 8'h08, 8'h00, 8'hFA, 8'h04, 8'h08 };
    assign b_hidden_layer[10] = 8'h01;
    assign w_hidden_layer[11] = '{ 8'hF9, 8'hFB, 8'h05, 8'hFA, 8'h03, 8'h02, 8'h02, 8'hFD };
    assign b_hidden_layer[11] = 8'hFF;
    assign w_hidden_layer[12] = '{ 8'hF9, 8'hFD, 8'h02, 8'hF8, 8'h05, 8'h06, 8'h01, 8'hF9 };
    assign b_hidden_layer[12] = 8'hFE;
    assign w_hidden_layer[13] = '{ 8'h00, 8'h06, 8'hFA, 8'hFB, 8'h00, 8'hFF, 8'hFE, 8'hFA };
    assign b_hidden_layer[13] = 8'h00;
    assign w_hidden_layer[14] = '{ 8'hF9, 8'hFA, 8'h04, 8'h05, 8'hFC, 8'h06, 8'hFE, 8'h01 };
    assign b_hidden_layer[14] = 8'h00;
    assign w_hidden_layer[15] = '{ 8'h01, 8'h07, 8'hFD, 8'h03, 8'h01, 8'h04, 8'hFF, 8'h08 };
    assign b_hidden_layer[15] = 8'h01;

    wire signed [7:0] hidden_outs [0:15];

    genvar i;
    generate
        for (i = 0; i < 16; i = i + 1) begin : hidden_layer
            neuron #(8) h_neuron (
                .clk(clk),
                .reset(reset),
                .enable(hidden_enable),
                .inputs(window),
                .weights(w_hidden_layer[i]),
                .bias(b_hidden_layer[i]),
                .out(hidden_outs[i])
            );
        end
    endgenerate

    wire signed [7:0] w_output_layer [0:1][0:15];
    wire signed [7:0] b_output_layer [0:1];

    assign w_output_layer[0] = '{ 8'h05, 8'hF7, 8'h06, 8'h05, 8'h04, 8'h04, 8'h00, 8'hF8, 8'h06, 8'hFE, 8'h02, 8'hFE, 8'h04, 8'h01, 8'hF7, 8'h07 };
    assign b_output_layer[0] = 8'hFF;
    assign w_output_layer[1] = '{ 8'hF8, 8'h07, 8'h00, 8'hF8, 8'hFD, 8'hF9, 8'h04, 8'h07, 8'hFB, 8'h04, 8'h05, 8'h00, 8'h01, 8'h06, 8'hF8, 8'h04 };
    assign b_output_layer[1] = 8'h01;

    wire signed [7:0] output_outs [0:1];

    genvar j;
    generate
        for (j = 0; j < 2; j = j + 1) begin : output_layer
            neuron #(16) final_neuron (
                .clk(clk),
                .reset(reset),
                .enable(output_enable),
                .inputs(hidden_outs),
                .weights(w_output_layer[j]),
                .bias(b_output_layer[j]),
                .out(output_outs[j])
            );
        end
    endgenerate

    assign prediction_temperature = output_outs[0];
    assign prediction_light = output_outs[1];

endmodule
