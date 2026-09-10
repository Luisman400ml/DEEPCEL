`timescale 1ns / 1ps

module eco_nn_top_tb;
    reg clk = 1'b0;
    reg reset = 1'b0;
    reg [7:0] temperature_sensor_in = 8'd0;
    reg [7:0] light_sensor_in = 8'd0;
    reg temp_data_ready = 1'b0;
    reg light_data_ready = 1'b0;
    wire [7:0] prediction_temperature;
    wire [7:0] prediction_light;

    eco_nn_top uut (
        .clk(clk),
        .reset(reset),
        .temperature_sensor_in(temperature_sensor_in),
        .light_sensor_in(light_sensor_in),
        .temp_data_ready(temp_data_ready),
        .light_data_ready(light_data_ready),
        .prediction_temperature(prediction_temperature),
        .prediction_light(prediction_light)
    );

    always #500 clk = ~clk;

    task push_pair(
        input [7:0] temperature,
        input [7:0] light,
        input [7:0] expected_temperature,
        input [7:0] expected_light
    );
        begin
            temperature_sensor_in = temperature;
            light_sensor_in = light;
            temp_data_ready = 1'b1;
            light_data_ready = 1'b1;
            #3000;
            temp_data_ready = 1'b0;
            light_data_ready = 1'b0;
            #250000;

            if (prediction_temperature !== expected_temperature ||
                prediction_light !== expected_light) begin
                $display("PREDICTION FAIL temp=%0d light=%0d expected=(%0d,%0d) actual=(%0d,%0d)",
                         temperature, light, expected_temperature, expected_light,
                         prediction_temperature, prediction_light);
                $stop;
            end
        end
    endtask

    initial begin
        #2000;
        reset = 1'b1;
        #2000;

        push_pair(8'd1,  8'd16, 8'd0, 8'd5);
        push_pair(8'd8,  8'd8,  8'd0, 8'd1);
        push_pair(8'd15, 8'd1,  8'd0, 8'd0);
        push_pair(8'd4,  8'd10, 8'd1, 8'd2);
        push_pair(8'd12, 8'd6,  8'd4, 8'd4);
        push_pair(8'd16, 8'd16, 8'd6, 8'd6);
        push_pair(8'd3,  8'd2,  8'd1, 8'd0);
        push_pair(8'd9,  8'd14, 8'd6, 8'd14);

        if (uut.window[0] !== 8'd12 || uut.window[1] !== 8'd16 ||
            uut.window[2] !== 8'd3 || uut.window[3] !== 8'd9 ||
            uut.window[4] !== 8'd6 || uut.window[5] !== 8'd16 ||
            uut.window[6] !== 8'd2 || uut.window[7] !== 8'd14) begin
            $display("WINDOW SHIFT FAIL");
            $stop;
        end

        $display("TEST PASS");
        $stop;
    end
endmodule
