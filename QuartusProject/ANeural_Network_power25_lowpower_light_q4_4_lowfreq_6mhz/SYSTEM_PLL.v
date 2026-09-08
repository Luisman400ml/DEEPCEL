module SYSTEM_PLL (
  input  wire areset,
  input  wire inclk0,
  output wire c0,
  output wire c1,
  output wire c2,
  output wire c3,
  output wire c4,
  output wire locked
);

wire [4:0] clk;

SYSTEM_PLL_altpll altpll_component (
  .areset(areset),
  .clk(clk),
  .inclk({1'b0, inclk0}),
  .locked(locked)
);

assign c0 = clk[0];
assign c1 = clk[1];
assign c2 = clk[2];
assign c3 = clk[3];
assign c4 = clk[4];

endmodule
