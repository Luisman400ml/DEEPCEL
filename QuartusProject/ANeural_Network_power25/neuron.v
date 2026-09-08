module neuron #(
  parameter INPUT_SIZE= 4
)(
input clk,
input reset,
input signed [15:0] inputs[0:INPUT_SIZE-1],
input signed [15:0] weights[0:INPUT_SIZE-1],
input signed [15:0] bias,
output reg signed [15:0] out
);

integer i;
reg signed [31:0] sum;

always@(posedge clk) begin 
   if(!reset) begin
      out<=0;
   end else begin
	    sum = bias;
	    for (i=0;i<INPUT_SIZE; i= i+1) begin
	    sum=sum +(inputs[i]*weights[i]>>>8);
	    end 
		//Relu Activation 
	   out<=(sum>0)?sum[15:0]: 16'd0;
   end
 end
endmodule
