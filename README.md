沒問題，這是更新後的 **LiteHDL 語言規格書 (v1.3)**。

此版本正式納入了 **二維陣列 (Arrays/Memories)** 的定義語法，完善了設計暫存器堆 (Register File) 與記憶體 (RAM/ROM) 的能力。

-----

# LiteHDL 語言規格書 (v1.3)

## 1\. 總覽 (Overview)

LiteHDL 是一個為了簡化 FPGA/ASIC 設計而生的 DSL。

  * **核心哲學：** 讓硬體描述像 Python 一樣簡潔，編譯為標準 VHDL。
  * **實作機制：** 前處理 $\rightarrow$ AST 解析 $\rightarrow$ VHDL 生成。

## 2\. 模組與參數 (Module & Parameters)

```python
module ModuleName(
    PARAM_1 = default_val,  # Generics
    WIDTH = 32
):
    pass
```

## 3\. 介面與訊號 (I/O & Signals)

### 3.1 I/O 區塊定義

使用 `in:` 與 `out:` 區塊來分組宣告。

```python
in:
    clk: bit
    addr: u[8]
out:
    data: u[16]
```

### 3.2 內部訊號與資料型別

直接宣告於模組本體。

| LiteHDL 語法 | VHDL 對應型別 | 說明 |
| :--- | :--- | :--- |
| `bit` | `std_logic` | 單一訊號 |
| `u[N]` | `unsigned(N-1 downto 0)` | 無號整數 (算術用) |
| `s[N]` | `signed(N-1 downto 0)` | 有號整數 |
| `v[N]` | `std_logic_vector(N-1 downto 0)` | 純位元向量 (匯流排用) |

### 3.3 [新增] 陣列與記憶體 (Arrays)

使用 **巢狀下標** 來定義二維陣列。

  * **語法：** `name: type[Width][Depth]`
  * **行為：** Transpiler 會自動生成對應的 `type` 定義與 `signal` 宣告。

| LiteHDL 寫法 | VHDL 對應結構 |
| :--- | :--- |
| `regs: v[32][16]` | `type t_regs is array (0 to 15) of std_logic_vector(31 downto 0);`<br>`signal regs : t_regs;` |
| `mem: u[8][256]` | `type t_mem is array (0 to 255) of unsigned(7 downto 0);`<br>`signal mem : t_mem;` |

## 4\. 邏輯區塊 (Logic Blocks)

### 4.1 循序邏輯 (`sync`)

  * **語法：** `sync(clock, reset_condition):`
  * **修飾符：** 使用 `~` 表示 Active Low 或 Falling Edge。
  * **自動轉型：** `if en:` 會自動轉譯為 `if en = '1' then`。

<!-- end list -->

```python
sync(clk, ~rst_n):
    if rst_n:
        # Reset Logic
    else:
        # Clock Edge Logic
```

### 4.2 組合邏輯 (`comb`)

  * **語法：** `comb:`
  * **行為：** 轉譯為 `process(all)`，立即生效賦值。

## 5\. 運算與賦值 (Operations)

  * **算術/邏輯：** `+`, `-`, `*`, `&`, `and`, `or`, `not`。
  * **比較：** `==`, `!=`, `>`, `<`。
  * **切片 (Slicing)：** `sig[High:Low]` (包含頭尾)。
  * **陣列存取：** `mem[addr]` (讀取/寫入)。

## 6\. 層次化設計 (Hierarchy)

直接實例化模組。

```python
u_ram = RamModule(WIDTH=32, clk=sys_clk, ...)
```

-----

## 7\. 黃金範例：暫存器堆 (Register File)

這個範例展示了新的陣列語法與讀寫邏輯。

```python
module RegFile(WIDTH=32, DEPTH=32):
    
    in:
        clk:    bit
        rst_n:  bit
        w_en:   bit
        w_addr: u[5] # 32 words need 5 bits
        w_data: v[WIDTH]
        r_addr: u[5]

    out:
        r_data: v[WIDTH]

    # 定義暫存器陣列 (32 bit 寬, 32 words 深)
    regs: v[WIDTH][DEPTH]

    # 讀取邏輯 (非同步讀取)
    comb:
        r_data = regs[r_addr]

    # 寫入邏輯 (同步寫入, Active Low Reset)
    sync(clk, ~rst_n):
        if rst_n:
            # 這裡可以選擇是否要重置整個陣列，或不重置
            # 為了合成效率，通常 RegFile 不做硬體 Reset
            pass 
        else:
            if w_en:
                regs[w_addr] = w_data
```
