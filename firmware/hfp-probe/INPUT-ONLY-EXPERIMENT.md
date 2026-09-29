# 仅显示为输入设备：HFP 设备类别实验

## 目标与基线

目标：Voice Puck V1 保持蓝牙麦克风功能，在 macOS 音频输入列表出现，而在输出列表完全不出现。

基线固件使用 ESP32 Classic Bluetooth HFP HF。macOS CoreAudio 实测建立两个端点：一个 1 通道输入和一个 1 通道输出。硬件没有扬声器；固件丢弃 Mac→ESP32 的下行音频。

## 单变量实验

Bluetooth SIG 的 Class of Device 为 Audio/Video 主类别定义了 Microphone 子类别（minor = 4）。本分支在 HFP 初始化完成后调用 `esp_bt_gap_set_cod()`，仅把主/子设备类别改为 Audio/Video / Microphone；HFP 服务、音频回调和 I²S 处理不变。

固件编译、刷入成功。ESP32 启动日志报告 `set microphone Class of Device: ESP_OK`。重新连接后，macOS 仍建立 `Voice Puck V1` 输入和输出两个 CoreAudio 端点；蓝牙设置仍把设备类型显示为“免提设备”。这说明仅设置设备类别没有消除输出端点。

## 结论与后续

这个实验尚需在 macOS 忽略旧配对并重新配对后再复核一次，以排除配对缓存。当前结果不支持把 Class of Device 设置为 Microphone 作为解决办法；不要将这项改动合并到 V1 主线。

HFP 的 HF 角色是音频网关的远程输入和输出。若重新配对后仍出现输出，当前 ESP32 HFP 路线不能满足“系统仅显示输入”的验收条件。LE Audio 协议可以分别声明 Source 和 Sink，但乐鑫的 ESP32 支持表显示原版 ESP32 不支持 ESP-BLE-ISO / ESP-BLE-AUDIO；更换到支持 LE Audio 的芯片后，仍须在目标 Mac 上实测兼容性。另一方向是自定义无线传输加 Mac 端虚拟输入设备，但会增加 Mac 端软件。

## 资料

- [Bluetooth SIG Hands-Free Profile](https://www.bluetooth.com/specifications/specs/hands-free-profile-1-10/)
- [Bluetooth SIG Assigned Numbers：Class of Device](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Assigned_Numbers/out/en/index-en.html)
- [Bluetooth SIG Basic Audio Profile](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/BAP_v1.0/out/en/index-en.html)
- [乐鑫 ESP32 蓝牙 LE 支持表](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/ble/overview.html)
