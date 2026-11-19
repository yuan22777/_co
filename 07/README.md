# Nand2Tetris VM Translator (Projects 07 & 08)

本專案實作了一個完整的 **VM 翻譯器（VM Translator）**，能夠將 Hack 虛擬機器語言（`.vm` 檔案）編譯成對應的 Hack 組合語言（`.asm` 檔案）。程式完整支援第七章的堆疊算術與記憶體存取，以及第八章的程式流程控制與函式呼叫機制。

---

## 一、 專案架構

程式採用模組化設計，主要分為三個核心部分（皆整合於 `VMTranslator.py` 中）：

* **`Parser`（語法解析器）**：負責讀取 `.vm` 原始碼，過濾註解（`//`）與多餘空白，並將每行指令拆解為指令類型（如 `C_PUSH`、`C_ARITHMETIC`、`C_CALL` 等）與對應參數（`arg1`、`arg2`）。
* **`CodeWriter`（程式碼生成器）**：將解析後的 VM 指令轉換為對應的 Hack 組合語言，包含算術邏輯運算、記憶體區段映射、條件跳轉標籤生成，以及函式呼叫框架（Stack Frame）的建立與還原。
* **`Main`（主控流程）**：自動判斷輸入路徑為「單一 `.vm` 檔案」或「包含多個 `.vm` 檔案的資料夾」，並在偵測到 `Sys.vm` 時自動於檔案開頭加入啟動碼（Bootstrap Code）。

---

## 二、 環境需求與執行方式

### 1. 環境需求
* Python 3.x（無須安裝任何第三方套件，僅使用內建的 `os` 與 `sys` 模組）
* Nand2Tetris 官方測試工具（`CPUEmulator`）

### 2. 執行指令

請在終端機（Terminal / PowerShell）中執行 `VMTranslator.py`，並傳入目標 `.vm` 檔案或資料夾路徑：

**情境 A：翻譯單一 `.vm` 檔案（適用於第 7 章所有測資，以及第 8 章無 `Sys.vm` 的測資）**
```bash
python VMTranslator.py 07/MemoryAccess/BasicTest/BasicTest.vm
```
----
## 三、 學習
#### 1.堆疊機（Stack Machine）的運作原理：
理解了虛擬機器如何不依賴通用暫存器，而是純粹透過堆疊指標（SP）的推進與彈出（Push / Pop）來完成所有的算術與邏輯運算。
#### 2.虛擬記憶體區段的映射（Memory Mapping）：
掌握了 local、argument、this、that 如何透過基底指標動態定址，以及 temp（RAM 5–12）、pointer（修改 THIS/THAT 位址）和 static（透過 檔名.索引 轉為全域變數符號）在底層 RAM 中的實際配置方式。
#### 3.系統啟動流程（Bootstrap Code）：
理解了電腦剛啟動時，如何透過一小段初始化組合語言設定堆疊起始位址（SP = 256）並呼叫進入點 Sys.init，進而帶動整個系統（包含 Main.main）的運作。