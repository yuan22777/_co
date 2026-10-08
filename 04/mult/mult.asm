// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Mult.asm

// Multiplies R0 and R1 and stores the result in R2.
// (R0, R1, R2 refer to RAM[0], RAM[1], and RAM[2], respectively.)

// Multiplies R0 and R1 and stores the result in R2.
// (R0, R1, R2 refer to RAM[0], RAM[1], and RAM[2], respectively.)

    // 1. 初始化結果 R2 = 0
    @R2
    M=0

(LOOP)
    // 2. 檢查乘數 R1 是否已經減到 0
    @R1
    D=M
    @END
    D;JEQ    // 若 R1 == 0，代表加法已完成，跳轉到 END

    // 3. 累加：R2 = R2 + R0
    @R0
    D=M
    @R2
    M=D+M    // 將 R0 的值加進 R2

    // 4. 遞減乘數：R1 = R1 - 1
    @R1
    M=M-1

    // 5. 跳回迴圈開頭繼續
    @LOOP
    0;JMP

(END)
    // 6. 無限迴圈（防止 CPU 繼續執行未知的記憶體區塊）
    @END
    0;JMP