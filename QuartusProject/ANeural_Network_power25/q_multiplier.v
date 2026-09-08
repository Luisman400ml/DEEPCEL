module q_multiplier(
input   signed  [15:0] a, //Q8.8 format
input   signed  [15:0] b, //Q8.8 format
output  signed  [15:0] product

);

wire signed [31:0] product_temp;
assign product_temp = a*b;
assign product = product_temp[23:8]; // reprendre le produit au format Q8.8

endmodule
