module neuron #(
  parameter INPUT_SIZE= 8
)(
input clk,
input reset,
input signed [7:0] inputs[0:INPUT_SIZE-1],
input signed [7:0] weights[0:INPUT_SIZE-1],
input signed [7:0] bias,
output reg signed [7:0] out
);

integer i;
reg signed [15:0] sum;

always@(posedge clk) begin 
   if(!reset) begin
      out<=0;
   end else begin
	    sum = bias;
	    for (i=0;i<INPUT_SIZE; i= i+1) begin
	    sum=sum +(inputs[i]*weights[i]>>>4);
	    end 
		//Relu Activation 
	   out<=(sum>0)?sum[7:0]: 8'd0;
   end
 end
endmodule
