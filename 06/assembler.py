import os
import sys


class HackAssembler:

  def __init__(self):
    # 1. 初始化符號表 (Symbol Table) 與內建符號
    self.symbol_table = {
        "SP": 0,
        "LCL": 1,
        "ARG": 2,
        "THIS": 3,
        "THAT": 4,
        "SCREEN": 16384,
        "KBD": 24576,
    }
    # 加入 R0 ~ R15
    for i in range(16):
      self.symbol_table[f"R{i}"] = i

    # 自訂變數的起始 RAM 位址
    self.next_variable_address = 16

    # 2. C-指令對照表 (comp, dest, jump)
    self.comp_table = {
        # a = 0
        "0": "0101010",
        "1": "0111111",
        "-1": "0111010",
        "D": "0001100",
        "A": "0110000",
        "!D": "0001101",
        "!A": "0110001",
        "-D": "0001111",
        "-A": "0110011",
        "D+1": "0011111",
        "A+1": "0110111",
        "D-1": "0001110",
        "A-1": "0110010",
        "D+A": "0000010",
        "D-A": "0010011",
        "A-D": "0000111",
        "D&A": "0000000",
        "D|A": "0010101",
        # a = 1
        "M": "1110000",
        "!M": "1110001",
        "-M": "1110011",
        "M+1": "1110111",
        "M-1": "1110010",
        "D+M": "1000010",
        "D-M": "1010011",
        "M-D": "1000111",
        "D&M": "1000000",
        "D|M": "1010101",
    }

    self.dest_table = {
        None: "000",
        "M": "001",
        "D": "010",
        "MD": "011",
        "A": "100",
        "AM": "101",
        "AD": "110",
        "AMD": "111",
    }

    self.jump_table = {
        None: "000",
        "JGT": "001",
        "JEQ": "010",
        "JGE": "011",
        "JLT": "100",
        "JNE": "101",
        "JLE": "110",
        "JMP": "111",
    }

  def clean_lines(self, raw_lines):
    """去除註解與多餘空白"""
    cleaned = []
    for line in raw_lines:
      # 去除 // 之後的註解
      comment_idx = line.find("//")
      if comment_idx != -1:
        line = line[:comment_idx]
      # 去除所有空白字元 (包含換行、縮排、指令內空白)
      line = "".join(line.split())
      if line:
        cleaned.append(line)
    return cleaned

  def first_pass(self, lines):
    """第一階段：記錄所有標籤 (L-instruction) 的 ROM 位址"""
    rom_address = 0
    instructions = []
    for line in lines:
      if line.startswith("(") and line.endswith(")"):
        label = line[1:-1]
        self.symbol_table[label] = rom_address
      else:
        instructions.append(line)
        rom_address += 1
    return instructions

  def translate_a_instruction(self, instruction):
    """翻譯 A-指令 (@value 或 @symbol)"""
    symbol = instruction[1:]
    if symbol.isdigit():
      address = int(symbol)
    else:
      if symbol not in self.symbol_table:
        self.symbol_table[symbol] = self.next_variable_address
        self.next_variable_address += 1
      address = self.symbol_table[symbol]

    # 轉換為 16-bit 二進位，最高位固定為 0
    return f"0{address:015b}"

  def translate_c_instruction(self, instruction):
    """翻譯 C-指令 (dest=comp;jump)"""
    dest = None
    jump = None
    comp = instruction

    # 拆解 dest
    if "=" in comp:
      dest, comp = comp.split("=", 1)

    # 拆解 jump
    if ";" in comp:
      comp, jump = comp.split(";", 1)

    # 查表組合 16-bit 機器碼: 111 + comp(7) + dest(3) + jump(3)
    comp_bits = self.comp_table[comp]
    dest_bits = self.dest_table[dest]
    jump_bits = self.jump_table[jump]

    return f"111{comp_bits}{dest_bits}{jump_bits}"

  def assemble(self, raw_lines):
    """執行完整組譯流程"""
    cleaned_lines = self.clean_lines(raw_lines)
    instructions = self.first_pass(cleaned_lines)

    binary_output = []
    for inst in instructions:
      if inst.startswith("@"):
        binary_output.append(self.translate_a_instruction(inst))
      else:
        binary_output.append(self.translate_c_instruction(inst))

    return binary_output


def main():
  if len(sys.argv) != 2:
    print("使用方式: python assembler.py <檔案名稱.asm>")
    sys.exit(1)

  input_path = sys.argv[1]
  if not input_path.endswith(".asm"):
    print("錯誤：輸入檔案必須是 .asm 副檔名")
    sys.exit(1)

  output_path = os.path.splitext(input_path)[0] + ".hack"

  with open(input_path, "r", encoding="utf-8") as f:
    raw_lines = f.readlines()

  assembler = HackAssembler()
  machine_code = assembler.assemble(raw_lines)

  with open(output_path, "w", encoding="utf-8") as f:
    for line in machine_code:
      f.write(line + "\n")

  print(f"組譯完成！輸出檔案：{output_path}")


if __name__ == "__main__":
  main()