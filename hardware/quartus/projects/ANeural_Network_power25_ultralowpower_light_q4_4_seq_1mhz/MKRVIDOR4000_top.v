/*
 * Minimal MKR Vidor 4000 top for the DEEPCEL temperature/light neural network.
 *
 * The SAMD21 talks to the FPGA through the same JTAG register interface used by
 * the stable designs. Unused board peripherals are held static or tri-stated so
 * they do not add avoidable switching activity to this low-power variant.
 */

module MKRVIDOR4000_top
(
  input         iCLK,
  input         iRESETn,
  input         iSAM_INT,
  output        oSAM_INT,

  output        oSDRAM_CLK,
  output [11:0] oSDRAM_ADDR,
  output [1:0]  oSDRAM_BA,
  output        oSDRAM_CASn,
  output        oSDRAM_CKE,
  output        oSDRAM_CSn,
  inout  [15:0] bSDRAM_DQ,
  output [1:0]  oSDRAM_DQM,
  output        oSDRAM_RASn,
  output        oSDRAM_WEn,

  inout         bMKR_AREF,
  inout  [6:0]  bMKR_A,
  inout  [14:0] bMKR_D,

  inout         bPEX_RST,
  inout         bPEX_PIN6,
  inout         bPEX_PIN8,
  inout         bPEX_PIN10,
  input         iPEX_PIN11,
  inout         bPEX_PIN12,
  input         iPEX_PIN13,
  inout         bPEX_PIN14,
  inout         bPEX_PIN16,
  inout         bPEX_PIN20,
  input         iPEX_PIN23,
  input         iPEX_PIN25,
  inout         bPEX_PIN28,
  inout         bPEX_PIN30,
  input         iPEX_PIN31,
  inout         bPEX_PIN32,
  input         iPEX_PIN33,
  inout         bPEX_PIN42,
  inout         bPEX_PIN44,
  inout         bPEX_PIN45,
  inout         bPEX_PIN46,
  inout         bPEX_PIN47,
  inout         bPEX_PIN48,
  inout         bPEX_PIN49,
  inout         bPEX_PIN51,

  inout         bWM_PIO1,
  inout         bWM_PIO2,
  inout         bWM_PIO3,
  inout         bWM_PIO4,
  inout         bWM_PIO5,
  inout         bWM_PIO7,
  inout         bWM_PIO8,
  inout         bWM_PIO18,
  inout         bWM_PIO20,
  inout         bWM_PIO21,
  inout         bWM_PIO27,
  inout         bWM_PIO28,
  inout         bWM_PIO29,
  inout         bWM_PIO31,
  input         iWM_PIO32,
  inout         bWM_PIO34,
  inout         bWM_PIO35,
  inout         bWM_PIO36,
  input         iWM_TX,
  inout         oWM_RX,
  inout         oWM_RESET,

  output [2:0]  oHDMI_TX,
  output        oHDMI_CLK,
  inout         bHDMI_SDA,
  inout         bHDMI_SCL,
  input         iHDMI_HPD,

  input  [1:0]  iMIPI_D,
  input         iMIPI_CLK,
  inout         bMIPI_SDA,
  inout         bMIPI_SCL,
  inout  [1:0]  bMIPI_GP,

  output        oFLASH_SCK,
  output        oFLASH_CS,
  inout         oFLASH_MOSI,
  inout         iFLASH_MISO,
  inout         oFLASH_HOLD,
  inout         oFLASH_WP
);

wire wNN_CLK;
wire wJTAG_CLK;

wire [7:0] to_arduino_prediction_temperature;
wire [7:0] to_arduino_prediction_light;
wire from_arduino_temp_ready;
wire from_arduino_light_ready;
wire [7:0] from_arduino_temperature_sensor;
wire [7:0] from_arduino_light_sensor;
wire [127:0] from_arduino_data;

SYSTEM_PLL PLL_inst(
  .areset(1'b0),
  .inclk0(iCLK),
  .c0(wNN_CLK),
  .c1(wJTAG_CLK),
  .locked()
);

eco_nn_top uut(
  .clk(wNN_CLK),
  .reset(iRESETn),
  .temperature_sensor_in(from_arduino_temperature_sensor),
  .light_sensor_in(from_arduino_light_sensor),
  .temp_data_ready(from_arduino_temp_ready),
  .light_data_ready(from_arduino_light_ready),
  .prediction_temperature(to_arduino_prediction_temperature),
  .prediction_light(to_arduino_prediction_light)
);

jtag_interface #(
  .REGISTER_SIZE(32),
  .NUMBER_OF_REGISTERS(4)
) interfacejtag(
  .iMAIN_CLK(wJTAG_CLK),
  .iDATA({64'b0, {24'b0, to_arduino_prediction_light}, {24'b0, to_arduino_prediction_temperature}}),
  .oDATA(from_arduino_data)
);

assign from_arduino_temperature_sensor = from_arduino_data[7:0];
assign from_arduino_light_sensor = from_arduino_data[39:32];
assign from_arduino_temp_ready = from_arduino_data[64];
assign from_arduino_light_ready = from_arduino_data[96];

assign oSAM_INT = 1'b0;

assign oSDRAM_CLK = 1'b0;
assign oSDRAM_ADDR = 12'd0;
assign oSDRAM_BA = 2'd0;
assign oSDRAM_CASn = 1'b1;
assign oSDRAM_CKE = 1'b0;
assign oSDRAM_CSn = 1'b1;
assign bSDRAM_DQ = 16'bz;
assign oSDRAM_DQM = 2'b11;
assign oSDRAM_RASn = 1'b1;
assign oSDRAM_WEn = 1'b1;

assign bMKR_AREF = 1'bz;
assign bMKR_A = 7'bz;
assign bMKR_D = 15'bz;

assign bPEX_RST = 1'bz;
assign bPEX_PIN6 = 1'bz;
assign bPEX_PIN8 = 1'bz;
assign bPEX_PIN10 = 1'bz;
assign bPEX_PIN12 = 1'bz;
assign bPEX_PIN14 = 1'bz;
assign bPEX_PIN16 = 1'bz;
assign bPEX_PIN20 = 1'bz;
assign bPEX_PIN28 = 1'bz;
assign bPEX_PIN30 = 1'bz;
assign bPEX_PIN32 = 1'bz;
assign bPEX_PIN42 = 1'bz;
assign bPEX_PIN44 = 1'bz;
assign bPEX_PIN45 = 1'bz;
assign bPEX_PIN46 = 1'bz;
assign bPEX_PIN47 = 1'bz;
assign bPEX_PIN48 = 1'bz;
assign bPEX_PIN49 = 1'bz;
assign bPEX_PIN51 = 1'bz;

assign bWM_PIO1 = 1'bz;
assign bWM_PIO2 = 1'bz;
assign bWM_PIO3 = 1'bz;
assign bWM_PIO4 = 1'bz;
assign bWM_PIO5 = 1'bz;
assign bWM_PIO7 = 1'bz;
assign bWM_PIO8 = 1'bz;
assign bWM_PIO18 = 1'bz;
assign bWM_PIO20 = 1'bz;
assign bWM_PIO21 = 1'bz;
assign bWM_PIO27 = 1'bz;
assign bWM_PIO28 = 1'bz;
assign bWM_PIO29 = 1'bz;
assign bWM_PIO31 = 1'bz;
assign bWM_PIO34 = 1'bz;
assign bWM_PIO35 = 1'bz;
assign bWM_PIO36 = 1'bz;
assign oWM_RX = 1'bz;
assign oWM_RESET = 1'bz;

assign oHDMI_TX = 3'b000;
assign oHDMI_CLK = 1'b0;
assign bHDMI_SDA = 1'bz;
assign bHDMI_SCL = 1'bz;

assign bMIPI_SDA = 1'bz;
assign bMIPI_SCL = 1'bz;
assign bMIPI_GP = 2'bzz;

assign oFLASH_SCK = 1'b0;
assign oFLASH_CS = 1'b1;
assign oFLASH_MOSI = 1'bz;
assign iFLASH_MISO = 1'bz;
assign oFLASH_HOLD = 1'bz;
assign oFLASH_WP = 1'bz;

endmodule
