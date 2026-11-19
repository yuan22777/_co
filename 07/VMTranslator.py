import os
import sys

# 定義 VM 指令類型常數
C_ARITHMETIC = "C_ARITHMETIC"
C_PUSH = "C_PUSH"
C_POP = "C_POP"
C_LABEL = "C_LABEL"
C_GOTO = "C_GOTO"
C_IF = "C_IF"
C_FUNCTION = "C_FUNCTION"
C_RETURN = "C_RETURN"
C_CALL = "C_CALL"


class Parser:
    """負責讀取單一 .vm 檔案，過濾註解與空白，並拆解每行指令。"""

    def __init__(self, file_path):
        self.commands = []
        self.current_command = ""
        self.current_index = -1

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                # 去除 // 註解與前後空白
                clean_line = line.split("//")[0].strip()
                if clean_line:
                    self.commands.append(clean_line)

    def has_more_commands(self):
        return self.current_index + 1 < len(self.commands)

    def advance(self):
        self.current_index += 1
        self.current_command = self.commands[self.current_index]

    def command_type(self):
        parts = self.current_command.split()
        cmd = parts[0]
        if cmd in ["add", "sub", "neg", "eq", "gt", "lt", "and", "or", "not"]:
            return C_ARITHMETIC
        elif cmd == "push":
            return C_PUSH
        elif cmd == "pop":
            return C_POP
        elif cmd == "label":
            return C_LABEL
        elif cmd == "goto":
            return C_GOTO
        elif cmd == "if-goto":
            return C_IF
        elif cmd == "function":
            return C_FUNCTION
        elif cmd == "return":
            return C_RETURN
        elif cmd == "call":
            return C_CALL
        else:
            raise ValueError(f"未知的指令: {self.current_command}")

    def arg1(self):
        c_type = self.command_type()
        if c_type == C_RETURN:
            raise ValueError("C_RETURN 不應該呼叫 arg1()")
        parts = self.current_command.split()
        if c_type == C_ARITHMETIC:
            return parts[0]
        return parts[1]

    def arg2(self):
        c_type = self.command_type()
        if c_type not in [C_PUSH, C_POP, C_FUNCTION, C_CALL]:
            raise ValueError(f"{c_type} 不應該呼叫 arg2()")
        parts = self.current_command.split()
        return int(parts[2])


class CodeWriter:
    """負責將解析後的 VM 指令翻譯成 Hack 組合語言並寫入 .asm 檔案。"""

    def __init__(self, output_path):
        self.file = open(output_path, "w", encoding="utf-8")
        self.current_vm_filename = ""
        self.current_function_name = "null"
        self.label_counter = 0

    def set_file_name(self, vm_file_path):
        """通知 CodeWriter 目前正在翻譯哪一個 .vm 檔（用於 static 變數命名）"""
        base = os.path.basename(vm_file_path)
        self.current_vm_filename = os.path.splitext(base)[0]

    def write_init(self):
        """寫入啟動碼 (Bootstrap Code)：SP=256 並呼叫 Sys.init"""
        self._write("// Bootstrap code")
        self._write("@256")
        self._write("D=A")
        self._write("@SP")
        self._write("M=D")
        self.write_call("Sys.init", 0)

    def write_arithmetic(self, command):
        self._write(f"// {command}")
        if command in ["add", "sub", "and", "or"]:
            self._pop_d()
            self._write("A=A-1")
            if command == "add":
                self._write("M=D+M")
            elif command == "sub":
                self._write("M=M-D")
            elif command == "and":
                self._write("M=D&M")
            elif command == "or":
                self._write("M=D|M")
        elif command in ["neg", "not"]:
            self._write("@SP")
            self._write("A=M-1")
            if command == "neg":
                self._write("M=-M")
            elif command == "not":
                self._write("M=!M")
        elif command in ["eq", "gt", "lt"]:
            true_label = f"TRUE_{self.label_counter}"
            end_label = f"END_{self.label_counter}"
            self.label_counter += 1

            jump_cmd = {"eq": "JEQ", "gt": "JGT", "lt": "JLT"}[command]

            self._pop_d()
            self._write("A=A-1")
            self._write("D=M-D")
            self._write(f"@{true_label}")
            self._write(f"D;{jump_cmd}")
            self._write("@SP")
            self._write("A=M-1")
            self._write("M=0")  # False = 0
            self._write(f"@{end_label}")
            self._write("0;JMP")
            self._write(f"({true_label})")
            self._write("@SP")
            self._write("A=M-1")
            self._write("M=-1")  # True = -1
            self._write(f"({end_label})")

    def write_push_pop(self, command_type, segment, index):
        seg_map = {"local": "LCL", "argument": "ARG", "this": "THIS", "that": "THAT"}

        if command_type == C_PUSH:
            self._write(f"// push {segment} {index}")
            if segment == "constant":
                self._write(f"@{index}")
                self._write("D=A")
                self._push_d()
            elif segment in seg_map:
                self._write(f"@{seg_map[segment]}")
                self._write("D=M")
                self._write(f"@{index}")
                self._write("A=D+A")
                self._write("D=M")
                self._push_d()
            elif segment == "temp":
                self._write(f"@{5 + index}")
                self._write("D=M")
                self._push_d()
            elif segment == "pointer":
                target = "THIS" if index == 0 else "THAT"
                self._write(f"@{target}")
                self._write("D=M")
                self._push_d()
            elif segment == "static":
                self._write(f"@{self.current_vm_filename}.{index}")
                self._write("D=M")
                self._push_d()

        elif command_type == C_POP:
            self._write(f"// pop {segment} {index}")
            if segment in seg_map:
                self._write(f"@{seg_map[segment]}")
                self._write("D=M")
                self._write(f"@{index}")
                self._write("D=D+A")
                self._write("@R13")
                self._write("M=D")
                self._pop_d()
                self._write("@R13")
                self._write("A=M")
                self._write("M=D")
            elif segment == "temp":
                self._pop_d()
                self._write(f"@{5 + index}")
                self._write("M=D")
            elif segment == "pointer":
                target = "THIS" if index == 0 else "THAT"
                self._pop_d()
                self._write(f"@{target}")
                self._write("M=D")
            elif segment == "static":
                self._pop_d()
                self._write(f"@{self.current_vm_filename}.{index}")
                self._write("M=D")

    def write_label(self, label):
        self._write(f"// label {label}")
        self._write(f"({self.current_function_name}${label})")

    def write_goto(self, label):
        self._write(f"// goto {label}")
        self._write(f"@{self.current_function_name}${label}")
        self._write("0;JMP")

    def write_if(self, label):
        self._write(f"// if-goto {label}")
        self._pop_d()
        self._write(f"@{self.current_function_name}${label}")
        self._write("D;JNE")

    def write_function(self, function_name, num_vars):
        self._write(f"// function {function_name} {num_vars}")
        self.current_function_name = function_name
        self._write(f"({function_name})")
        for _ in range(num_vars):
            self._write("@0")
            self._write("D=A")
            self._push_d()

    def write_call(self, function_name, num_args):
        self._write(f"// call {function_name} {num_args}")
        return_label = f"{function_name}$ret.{self.label_counter}"
        self.label_counter += 1

        # 1. push return-address
        self._write(f"@{return_label}")
        self._write("D=A")
        self._push_d()

        # 2. push LCL, ARG, THIS, THAT
        for seg in ["LCL", "ARG", "THIS", "THAT"]:
            self._write(f"@{seg}")
            self._write("D=M")
            self._push_d()

        # 3. ARG = SP - n - 5
        self._write("@SP")
        self._write("D=M")
        self._write(f"@{num_args + 5}")
        self._write("D=D-A")
        self._write("@ARG")
        self._write("M=D")

        # 4. LCL = SP
        self._write("@SP")
        self._write("D=M")
        self._write("@LCL")
        self._write("M=D")

        # 5. goto f
        self._write(f"@{function_name}")
        self._write("0;JMP")

        # 6. (return-address)
        self._write(f"({return_label})")

    def write_return(self):
        self._write("// return")
        # endFrame (R13) = LCL
        self._write("@LCL")
        self._write("D=M")
        self._write("@R13")
        self._write("M=D")

        # retAddr (R14) = *(endFrame - 5)
        self._write("@5")
        self._write("A=D-A")
        self._write("D=M")
        self._write("@R14")
        self._write("M=D")

        # *ARG = pop()
        self._pop_d()
        self._write("@ARG")
        self._write("A=M")
        self._write("M=D")

        # SP = ARG + 1
        self._write("@ARG")
        self._write("D=M+1")
        self._write("@SP")
        self._write("M=D")

        # 還原 THAT, THIS, ARG, LCL
        for offset, seg in [(1, "THAT"), (2, "THIS"), (3, "ARG"), (4, "LCL")]:
            self._write("@R13")
            self._write("D=M")
            self._write(f"@{offset}")
            self._write("A=D-A")
            self._write("D=M")
            self._write(f"@{seg}")
            self._write("M=D")

        # goto retAddr
        self._write("@R14")
        self._write("A=M")
        self._write("0;JMP")

    def close(self):
        self.file.close()

    # --- 內部輔助方法 ---
    def _write(self, instruction):
        self.file.write(instruction + "\n")

    def _push_d(self):
        self._write("@SP")
        self._write("A=M")
        self._write("M=D")
        self._write("@SP")
        self._write("M=M+1")

    def _pop_d(self):
        self._write("@SP")
        self._write("AM=M-1")
        self._write("D=M")


def translate_file(vm_path, code_writer):
    parser = Parser(vm_path)
    code_writer.set_file_name(vm_path)

    while parser.has_more_commands():
        parser.advance()
        c_type = parser.command_type()

        if c_type == C_ARITHMETIC:
            code_writer.write_arithmetic(parser.arg1())
        elif c_type in [C_PUSH, C_POP]:
            code_writer.write_push_pop(c_type, parser.arg1(), parser.arg2())
        elif c_type == C_LABEL:
            code_writer.write_label(parser.arg1())
        elif c_type == C_GOTO:
            code_writer.write_goto(parser.arg1())
        elif c_type == C_IF:
            code_writer.write_if(parser.arg1())
        elif c_type == C_FUNCTION:
            code_writer.write_function(parser.arg1(), parser.arg2())
        elif c_type == C_CALL:
            code_writer.write_call(parser.arg1(), parser.arg2())
        elif c_type == C_RETURN:
            code_writer.write_return()


def main():
    if len(sys.argv) != 2:
        print("使用方式: python VMTranslator.py <檔案路徑.vm 或 資料夾路徑>")
        sys.exit(1)

    input_path = sys.argv[1].rstrip("/\\")
    vm_files = []
    need_bootstrap = False

    if os.path.isfile(input_path) and input_path.endswith(".vm"):
        vm_files.append(input_path)
        output_path = os.path.splitext(input_path)[0] + ".asm"
    elif os.path.isdir(input_path):
        for fname in os.listdir(input_path):
            if fname.endswith(".vm"):
                vm_files.append(os.path.join(input_path, fname))
        if not vm_files:
            print("錯誤：該資料夾內沒有找到任何 .vm 檔案")
            sys.exit(1)
        folder_name = os.path.basename(input_path)
        output_path = os.path.join(input_path, folder_name + ".asm")
        # 只有當資料夾內包含 Sys.vm 時才寫入 Bootstrap code
        # (這樣能同時相容沒有 Sys.vm 的測試資料夾)
        need_bootstrap = any(os.path.basename(f) == "Sys.vm" for f in vm_files)
    else:
        print("錯誤：請提供有效的 .vm 檔案或資料夾路徑")
        sys.exit(1)

    code_writer = CodeWriter(output_path)
    if need_bootstrap:
        code_writer.write_init()

    for vm_file in vm_files:
        translate_file(vm_file, code_writer)

    code_writer.close()
    print(f"翻譯完成！已輸出至: {output_path}")


if __name__ == "__main__":
    main()