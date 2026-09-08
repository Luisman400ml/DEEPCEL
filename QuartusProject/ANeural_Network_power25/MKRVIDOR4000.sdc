# Active subset of ../../MKRVIDOR4000/vidor_s.sdc for the temperature design.
# FPGA.cpp uses a 12 MHz JTAG SPI clock; the original template assumed 10 MHz.
create_clock -name altera_reserved_tck -period 83.333 [get_ports {altera_reserved_tck}]
create_clock -name iCLK -period 20.833 [get_ports {iCLK}]
derive_pll_clocks
# Quartus 25.1 removes auto_generated from the original PLL hierarchy.
create_generated_clock -name oSDRAM_CLK -source [get_pins {PLL_inst|altpll_component|pll1|clk[3]}] [get_ports {oSDRAM_CLK}]
derive_clock_uncertainty
set_clock_groups -asynchronous -group [get_clocks {altera_reserved_tck}]
# No MIPI receiver, SDRAM controller, Nios or AES instance is present here.
# The resampled JTAG clock still needs a separate CDC/timing review.
