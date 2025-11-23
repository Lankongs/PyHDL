library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity Counter is
    Generic (
        WIDTH : INTEGER := 8
    );
    Port (
        clk : IN STD_LOGIC;
        q : OUT STD_LOGIC_VECTOR(WIDTH-1 downto 0)
    );
end Counter;

architecture Behavioral of Counter is
    signal val : UNSIGNED(WIDTH-1 downto 0);
begin

    process(all)
    begin
        q <= std_logic_vector(val);
    end process;

    process(clk)
    begin
        if falling_edge(clk) then
            val <= (val + 1);
        end if;
    end process;

end Behavioral;