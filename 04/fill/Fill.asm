// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Fill.asm

// Runs an infinite loop that listens to the keyboard input.
// When a key is pressed (any key), the program blackens the screen,
// i.e. writes "black" in every pixel;
// the screen should remain fully black as long as the key is pressed. 
// When no key is pressed, the program clears the screen, i.e. writes
// "white" in every pixel;
// the screen should remain fully clear as long as no key is pressed.


(LOOP)
    @KBD
    D=M          // 讀鍵盤
    @BLACK
    D;JNE        // 有按鍵 → BLACK
    @WHITE
    0;JMP        // 沒按鍵 → WHITE

// 填黑螢幕
(BLACK)
    @SCREEN
    D=A
    @addr
    M=D          // addr = SCREEN 起始位址

(BLACK_LOOP)
    @addr
    A=M
    M=-1         // 寫入黑色

    @addr
    M=M+1        // addr++

    @KBD
    D=A
    @addr
    D=M-D
    @LOOP
    D;JEQ        // 如果 addr == KBD → 回到 LOOP
    @BLACK_LOOP
    0;JMP

// 清螢幕
(WHITE)
    @SCREEN
    D=A
    @addr
    M=D          // addr = SCREEN 起始位址

(WHITE_LOOP)
    @addr
    A=M
    M=0          // 寫入白色

    @addr
    M=M+1        // addr++

    @KBD
    D=A
    @addr
    D=M-D
    @LOOP
    D;JEQ        // 如果 addr == KBD → 回到 LOOP
    @WHITE_LOOP
    0;JMP

