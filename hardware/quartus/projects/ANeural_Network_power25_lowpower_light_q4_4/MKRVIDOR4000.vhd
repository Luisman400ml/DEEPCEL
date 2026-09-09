Library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;


entity incrementation is 
    port(
	     clk: in std_logic;
	     from_arduino_data: in unsigned(31 downto 0);  --valore di temperatura letta dal SAMD21
		  to_arduino_data: out unsigned(31 downto 0)   --valore di tempeeratura incrementata dall'FPGA
		  );
end entity incrementation;


architecture behavior of incrementation is 

begin
  process(clk)
  begin
      if rising_edge(clk) then
		   to_arduino_data <= from_arduino_data + 100 ; --increment of temperature
		end if;
 end process;
end architecture;

		  