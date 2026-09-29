# ESP32 + INMP441 接线（USB 供电原型）

适用范围：已识别为 `ESP32-D0WD-V3` 的原版 ESP32 开发板，配六引脚 `SCK/WS/L/R/SD/VDD/GND` 标识的 INMP441 模块。2026-09-29 的开发板照片显示板载 `ESP32-WROOM-32` 模组、30 针 DevKit V1 风格排针及 `D26/D25/D33/3V3/GND` 丝印。该布局中 `D26/D25/D33` 分别对应芯片 `GPIO26/GPIO25/GPIO33`。照片没有拍到已连接的跳线和麦克风板，**当前实际接线尚未视觉核验**。

| INMP441 模块丝印 | 接到 ESP32 开发板 | 作用 |
| --- | --- | --- |
| `VDD` 或 `VCC` | `3V3` | 麦克风供电；**不可接 5V/VIN** |
| `GND` | `GND` | 共地 |
| `SCK`、`BCLK` 或 `BCK` | 板上 `D26`（GPIO26） | ESP32 输出 I²S 位时钟 |
| `WS`、`LRCLK` 或 `LRC` | 板上 `D25`（GPIO25） | ESP32 输出左右声道选择时钟 |
| `SD`、`DOUT` 或 `DATA` | 板上 `D33`（GPIO33） | 麦克风输出数据，ESP32 输入（DIN） |
| `L/R` 或 `SEL` | `GND` | 选择左声道；固件也必须读取左声道 |

在照片所示方向（USB-C 接口朝左）中，`D26`、`D25`、`D33` 是上侧排针连续的三个标号；`3V3` 与旁边的 `GND` 在下侧排针靠 USB-C 接口的一端。按**丝印文字**找针脚，不凭此描述盲数位置。模块 `VDD` 只能接下侧 `3V3`，不能接上侧的 `VIN`。

```text
ESP32 3V3   ─── INMP441 VDD
ESP32 GND   ─── INMP441 GND ─┐
                              └── INMP441 L/R
ESP32 D26   ─── INMP441 SCK
ESP32 D25   ─── INMP441 WS
ESP32 D33   ◀── INMP441 SD
```

INMP441 本身是 I²S 从设备：ESP32 产生 SCK 和 WS，麦克风在 SD 上送出音频。单麦接左声道时，固件应设置匹配的左声道接收和 I²S 标准格式；INMP441 输出 24 位有符号数据，通常放在 32 位时隙内。它不需要单独连接 MCLK，也不使用 ESP32 的模拟 ADC 引脚。

## 接线和首次上电

1. 先拔掉开发板 USB 电源。按**板上丝印**找 `3V3`、`GND`、`D26`、`D25`、`D33`，不要把 `VIN`、`VN` 或 `VP` 当作 3.3 V。
2. 先接 `GND` 和 `VDD`，再接三个 I²S 信号，最后把 `L/R` 接到 `GND`。使用短线，避免松动或相邻针脚短路。
3. 有万用表时，通电前检查 `3V3` 与 `GND` 没有短路；USB 供电后测模块 `VDD` 对 `GND` 约为 3.3 V。此阶段不要再接电池或外部电源。
4. 第一次先运行只采集 I²S 的测试固件，确认说话时采样值会变化，再接入 HFP 链路。若一直是 0 或静音，先核对 `L/R` 与固件声道选择、`SD` 方向和 `SCK/WS` 接线。

模块若多出 `CHIPEN` 等引脚、或丝印与上表不同，先按该模块的原理图核对，不要直接套用此表。

## 依据

- [TDK INMP441 数据手册](https://product.tdk.com/system/files/dam/doc/product/sw_piezo/mic/mems-mic/data_sheet/inmp441.pdf)：供电范围、SCK/WS/SD/L/R 定义、左声道选择与 24 位 I²S 数据。
- [乐鑫 ESP32 I²S 文档](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/i2s.html)：主机输出 BCLK/WS、接收 DIN 以及标准 I²S 配置。
- [ESP32 DevKit V1 引脚映射参考](https://github.com/wokwi/wokwi-boards/blob/main/boards/esp32-devkit-v1/board.json)：`D26→GPIO26`、`D25→GPIO25`、`D33→GPIO33`；以实物丝印定位。
