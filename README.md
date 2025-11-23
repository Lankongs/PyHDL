✔ How to Run (使用方法)
1. VSCode 必須開在 PyHDL 的上一層

正確：

C:\Users\USER\Desktop> python -m litehdl.cli.main mymodule.lhd


錯誤（會找不到套件）：

C:\Users\USER\Desktop\PyHDL> python -m litehdl.cli.main mymodule.lhd


Python 要用上一層，才能找到 litehdl/ 這個 package。

2. 基本執行指令
python -m litehdl.cli.main <yourfile>.lhd


例如：

python -m litehdl.cli.main adder.lhd

3. 顯示轉出的 VHDL（verbose 模式）
python -m litehdl.cli.main adder.lhd -v

4. 輸出結果

執行後會在同一資料夾產生：

adder.vhd




---------English Version---------
# How to Run

1. VSCode must open the folder *above* PyHDL.
   Example:
       C:\Users\USER\Desktop> python -m litehdl.cli.main yourfile.lhd

2. Run the compiler:
       python -m litehdl.cli.main file.lhd

3. Show generated VHDL:
       python -m litehdl.cli.main file.lhd -v