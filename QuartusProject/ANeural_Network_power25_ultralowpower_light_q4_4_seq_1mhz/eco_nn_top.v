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
    reg signed [7:0] compute_inputs [0:7];
    reg signed [7:0] hidden_outs [0:15];
    reg signed [7:0] prediction_temperature_reg;
    reg signed [7:0] prediction_light_reg;

    reg temp_ready_meta;
    reg temp_ready_sync;
    reg temp_ready_d;
    reg light_ready_meta;
    reg light_ready_sync;
    reg light_ready_d;
    reg temp_pending;
    reg light_pending;
    reg inference_pending;

    wire temp_sample_pulse = temp_ready_sync & ~temp_ready_d;
    wire light_sample_pulse = light_ready_sync & ~light_ready_d;
    wire sample_pair_ready = (temp_pending | temp_sample_pulse) &
                             (light_pending | light_sample_pulse);

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

    wire signed [7:0] w_output_layer [0:1][0:15];
    wire signed [7:0] b_output_layer [0:1];

    assign w_output_layer[0] = '{ 8'h05, 8'hF7, 8'h06, 8'h05, 8'h04, 8'h04, 8'h00, 8'hF8, 8'h06, 8'hFE, 8'h02, 8'hFE, 8'h04, 8'h01, 8'hF7, 8'h07 };
    assign b_output_layer[0] = 8'hFF;
    assign w_output_layer[1] = '{ 8'hF8, 8'h07, 8'h00, 8'hF8, 8'hFD, 8'hF9, 8'h04, 8'h07, 8'hFB, 8'h04, 8'h05, 8'h00, 8'h01, 8'h06, 8'hF8, 8'h04 };
    assign b_output_layer[1] = 8'h01;

    localparam ST_IDLE = 3'd0;
    localparam ST_HIDDEN_ACCUM = 3'd1;
    localparam ST_HIDDEN_STORE = 3'd2;
    localparam ST_OUTPUT_ACCUM = 3'd3;
    localparam ST_OUTPUT_STORE = 3'd4;

    reg [2:0] state;
    reg [3:0] hidden_index;
    reg output_index;
    reg [4:0] input_index;
    reg signed [15:0] accumulator;

    wire start_compute = inference_pending & (state == ST_IDLE);

    wire signed [15:0] hidden_product =
        compute_inputs[input_index[2:0]] * w_hidden_layer[hidden_index][input_index[2:0]];
    wire signed [15:0] output_product =
        hidden_outs[input_index[3:0]] * w_output_layer[output_index][input_index[3:0]];

    function signed [7:0] relu8;
        input signed [15:0] value;
        begin
            relu8 = (value > 0) ? value[7:0] : 8'sd0;
        end
    endfunction

    integer k;

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
            inference_pending <= 1'b0;
        end else begin
            temp_ready_meta <= temp_data_ready;
            temp_ready_sync <= temp_ready_meta;
            temp_ready_d <= temp_ready_sync;
            light_ready_meta <= light_data_ready;
            light_ready_sync <= light_ready_meta;
            light_ready_d <= light_ready_sync;

            if (sample_pair_ready) begin
                temp_pending <= 1'b0;
                light_pending <= 1'b0;
                inference_pending <= 1'b1;
            end else begin
                if (temp_sample_pulse) begin
                    temp_pending <= 1'b1;
                end
                if (light_sample_pulse) begin
                    light_pending <= 1'b1;
                end
                if (start_compute) begin
                    inference_pending <= 1'b0;
                end
            end
        end
    end

    always @(posedge clk) begin
        if (!reset) begin
            for (k = 0; k < 8; k = k + 1) begin
                window[k] <= 8'sd0;
            end
        end else begin
            if (temp_sample_pulse) begin
                window[3] <= temperature_sensor_in;
                window[2] <= window[3];
                window[1] <= window[2];
                window[0] <= window[1];
            end
            if (light_sample_pulse) begin
                window[7] <= light_sensor_in;
                window[6] <= window[7];
                window[5] <= window[6];
                window[4] <= window[5];
            end
        end
    end

    always @(posedge clk) begin
        if (!reset) begin
            state <= ST_IDLE;
            hidden_index <= 4'd0;
            output_index <= 1'b0;
            input_index <= 5'd0;
            accumulator <= 16'sd0;
            prediction_temperature_reg <= 8'sd0;
            prediction_light_reg <= 8'sd0;
            for (k = 0; k < 8; k = k + 1) begin
                compute_inputs[k] <= 8'sd0;
            end
            for (k = 0; k < 16; k = k + 1) begin
                hidden_outs[k] <= 8'sd0;
            end
        end else begin
            case (state)
                ST_IDLE: begin
                    if (start_compute) begin
                        for (k = 0; k < 8; k = k + 1) begin
                            compute_inputs[k] <= window[k];
                        end
                        hidden_index <= 4'd0;
                        input_index <= 5'd0;
                        accumulator <= b_hidden_layer[0];
                        state <= ST_HIDDEN_ACCUM;
                    end
                end

                ST_HIDDEN_ACCUM: begin
                    accumulator <= accumulator + (hidden_product >>> 4);
                    if (input_index == 5'd7) begin
                        state <= ST_HIDDEN_STORE;
                    end else begin
                        input_index <= input_index + 5'd1;
                    end
                end

                ST_HIDDEN_STORE: begin
                    hidden_outs[hidden_index] <= relu8(accumulator);
                    if (hidden_index == 4'd15) begin
                        output_index <= 1'b0;
                        input_index <= 5'd0;
                        accumulator <= b_output_layer[0];
                        state <= ST_OUTPUT_ACCUM;
                    end else begin
                        hidden_index <= hidden_index + 4'd1;
                        input_index <= 5'd0;
                        accumulator <= b_hidden_layer[hidden_index + 4'd1];
                        state <= ST_HIDDEN_ACCUM;
                    end
                end

                ST_OUTPUT_ACCUM: begin
                    accumulator <= accumulator + (output_product >>> 4);
                    if (input_index == 5'd15) begin
                        state <= ST_OUTPUT_STORE;
                    end else begin
                        input_index <= input_index + 5'd1;
                    end
                end

                ST_OUTPUT_STORE: begin
                    if (output_index == 1'b0) begin
                        prediction_temperature_reg <= relu8(accumulator);
                        output_index <= 1'b1;
                        input_index <= 5'd0;
                        accumulator <= b_output_layer[1];
                        state <= ST_OUTPUT_ACCUM;
                    end else begin
                        prediction_light_reg <= relu8(accumulator);
                        state <= ST_IDLE;
                    end
                end

                default: begin
                    state <= ST_IDLE;
                end
            endcase
        end
    end

    assign prediction_temperature = prediction_temperature_reg;
    assign prediction_light = prediction_light_reg;

endmodule
