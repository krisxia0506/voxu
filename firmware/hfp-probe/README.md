# Voice Puck V1：Mac HFP 采音验证

此工程是原版 ESP32 + INMP441 的单机验证固件。它把 D26/D25/D33 上的 I²S 麦克风采样转换成 16 位单声道 PCM，并通过 Bluetooth Classic HFP HF 的 HCI 音频路径送给 Mac。当前没有按键、电池管理、扬声器、自动静音或 Typeless 控制。

## 本机编译与刷入

在本目录运行：

```sh
uvx --from platformio platformio run
uvx --from platformio platformio run -t upload --upload-port /dev/cu.usbserial-110
uvx --from platformio platformio device monitor --port /dev/cu.usbserial-110 --baud 115200
```

USB 串口名称可能变化。接线沿用项目根目录的 `WIRING.md`。首次配对后，Mac 应在“系统设置 → 声效 → 输入”列出 `Voice Puck V1`；只有选择或实际打开这个输入设备时，SCO 音频连接才会保持。日志中的 `HFP=1, SCO=1, codec=mSBC` 表示当前已接通宽带语音链路。

### macOS 同时显示输入与输出

当前固件使用 Bluetooth Classic HFP（免提/耳机协议）。实测 macOS 为 `Voice Puck V1` 建立了一个输入端点和一个输出端点。硬件只有 INMP441 麦克风，没有扬声器；`incoming_audio()` 收到的 Mac→设备音频会直接丢弃，因此选择这个输出端点不会发声。HFP 本身按双向音频设备工作，单纯在固件中丢弃下行数据无法让 macOS 隐藏输出端点。

使用本验证固件时，Mac 的输入可选 `Voice Puck V1`，输出应选“MacBook Pro 扬声器”或用户实际使用的扬声器。如果成品要求系统里只出现输入设备，就需要改用经目标 Mac 验证的单向音频传输方案；这不属于当前 ESP32 HFP 固件的小改动。

**此验证工程只针对当前这台 Mac。** `src/main.c` 中的 `test_mac` 是本机 Classic 蓝牙地址，开机扫描到它后主动发起 HFP 服务连接。换另一台 Mac 前须更改此地址；正式固件应改为通用配对与已绑定设备重连逻辑。首次配对时也可能需要由 Mac 发起配对。

## 2026-09-29 实测

- ESP32-D0WD-V3 / ESP32-WROOM-32 与 INMP441 的 I²S 采样正常；HFP 服务连接成功，Mac 将设备列为 1 声道输入，同时也列出一个无实际扬声器的输出端点。
- Mac 默认输入选为 `Voice Puck V1` 后，SCO 接通并协商为 mSBC 16 kHz；测试结束时连接仍在。
- MacBook Pro 扬声器播放 1 kHz、3 秒测试音，同时用 Mac 的 `Voice Puck V1` 输入录制 9 秒。录音的 1 kHz 分量在播放前后约 0–2，播放期间约 147–163（16 位 PCM 幅度单位）。这验证了声音从 INMP441 经 ESP32、HFP 回到 Mac 的完整路径。
- 原始测试音为 [1khz-test-tone.wav](evidence/1khz-test-tone.wav)，蓝牙麦克风实际录音为 [mac-1khz-loopback.wav](evidence/mac-1khz-loopback.wav)。

尚未验证 Typeless 听写、合盖场景、长时间稳定性、重连恢复和语音音质。测试固件会在 Mac 仍选择该设备输入时持续通过蓝牙发送音频。
