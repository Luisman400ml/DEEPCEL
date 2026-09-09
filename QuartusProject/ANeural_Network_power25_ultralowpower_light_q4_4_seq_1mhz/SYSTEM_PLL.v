module SYSTEM_PLL (
  input  wire areset,
  input  wire inclk0,
  output wire c0,
  output wire c1,
  output wire locked
);

wire [1:0] clk;

SYSTEM_PLL_altpll altpll_component (
  .areset(areset),
  .clk(clk),
  .inclk({1'b0, inclk0}),
  .locked(locked)
);

assign c0 = clk[0];
assign c1 = clk[1];

endmodule
