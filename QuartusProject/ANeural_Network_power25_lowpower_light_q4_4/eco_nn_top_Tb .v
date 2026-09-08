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

    always #20 clk = ~clk;

    task push_temperature(input [7:0] sample);
        begin
            temperature_sensor_in = sample;
            temp_data_ready = 1'b1;
            #1000;
            temp_data_ready = 1'b0;
            #1000;
        end
    endtask

    task push_light(input [7:0] sample);
        begin
            light_sensor_in = sample;
            light_data_ready = 1'b1;
            #1000;
            light_data_ready = 1'b0;
            #1000;
        end
    endtask

    initial begin
        #100;
        reset = 1'b1;
        #100;

        push_temperature(8'd1);
        push_temperature(8'd2);
        push_temperature(8'd3);
        push_temperature(8'd4);
        push_light(8'd5);
        push_light(8'd6);
        push_light(8'd7);
        push_light(8'd8);
        #2000;

        if (uut.window[0] !== 8'd1 || uut.window[1] !== 8'd2 ||
            uut.window[2] !== 8'd3 || uut.window[3] !== 8'd4 ||
            uut.window[4] !== 8'd5 || uut.window[5] !== 8'd6 ||
            uut.window[6] !== 8'd7 || uut.window[7] !== 8'd8) begin
            $display("WINDOW FAIL");
            $stop;
        end

        push_temperature(8'd9);
        push_light(8'd10);
        #2000;

        if (uut.window[0] !== 8'd2 || uut.window[1] !== 8'd3 ||
            uut.window[2] !== 8'd4 || uut.window[3] !== 8'd9 ||
            uut.window[4] !== 8'd6 || uut.window[5] !== 8'd7 ||
            uut.window[6] !== 8'd8 || uut.window[7] !== 8'd10) begin
            $display("WINDOW SHIFT FAIL");
            $stop;
        end

        $display("TEST PASS");
        $stop;
    end
endmodule
