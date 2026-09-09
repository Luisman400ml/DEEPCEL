// Minimal PLL wrapper for the DEEPCEL ultra-low-power variant.
// Input clock is 48 MHz from the MKR Vidor system clock.
// clk[0] = 1 MHz for the neural-network sequencer.
// clk[1] = 120 MHz for the existing JTAG register interface.

module SYSTEM_PLL_altpll
(
    input        areset,
    output [1:0] clk,
    input  [1:0] inclk,
    output       locked
) /* synthesis synthesis_clearbox=1 */;

    reg pll_lock_sync;
    wire [1:0] wire_pll1_clk;
    wire wire_pll1_fbout;
    wire wire_pll1_locked;

    initial begin
        pll_lock_sync = 1'b0;
    end

    always @(posedge wire_pll1_locked or posedge areset) begin
        if (areset) begin
            pll_lock_sync <= 1'b0;
        end else begin
            pll_lock_sync <= 1'b1;
        end
    end

    cyclone10lp_pll pll1
    (
        .activeclock(),
        .areset(areset),
        .clk(wire_pll1_clk),
        .clkbad(),
        .fbin(wire_pll1_fbout),
        .fbout(wire_pll1_fbout),
        .inclk(inclk),
        .locked(wire_pll1_locked),
        .phasedone(),
        .scandataout(),
        .scandone(),
        .vcooverrange(),
        .vcounderrange(),
        .clkswitch(1'b0),
        .configupdate(1'b0),
        .pfdena(1'b1),
        .phasecounterselect(3'b000),
        .phasestep(1'b0),
        .phaseupdown(1'b0),
        .scanclk(1'b0),
        .scanclkena(1'b1),
        .scandata(1'b0)
    );

    defparam
        pll1.bandwidth_type = "auto",
        pll1.clk0_divide_by = 48,
        pll1.clk0_duty_cycle = 50,
        pll1.clk0_multiply_by = 1,
        pll1.clk0_phase_shift = "0",
        pll1.clk1_divide_by = 2,
        pll1.clk1_duty_cycle = 50,
        pll1.clk1_multiply_by = 5,
        pll1.clk1_phase_shift = "0",
        pll1.compensate_clock = "clk0",
        pll1.inclk0_input_frequency = 20833,
        pll1.operation_mode = "normal",
        pll1.pll_type = "auto",
        pll1.self_reset_on_loss_lock = "off",
        pll1.lpm_type = "cyclone10lp_pll";

    assign clk = wire_pll1_clk;
    assign locked = wire_pll1_locked & pll_lock_sync;

endmodule
