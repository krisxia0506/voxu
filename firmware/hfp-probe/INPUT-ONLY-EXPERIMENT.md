# 仅显示为输入设备：HFP 设备类别实验

## 目标与基线

目标：Voice Puck V1 保持蓝牙麦克风功能，在 macOS 音频输入列表出现，而在输出列表完全不出现。

基线固件使用 ESP32 Classic Bluetooth HFP HF。macOS CoreAudio 实测建立两个端点：一个 1 通道输入和一个 1 通道输出。硬件没有扬声器；固件丢弃 Mac→ESP32 的下行音频。

## 单变量实验

Bluetooth SIG 的 Class of Device 为 Audio/Video 主类别定义了 Microphone 子类别（minor = 4）。本分支在 HFP 初始化完成后调用 `esp_bt_gap_set_cod()`，仅把主/子设备类别改为 Audio/Video / Microphone；HFP 服务、音频回调和 I²S 处理不变。

固件编译、刷入成功。ESP32 启动日志报告 `set microphone Class of Device: ESP_OK`。保留旧配对时，macOS 仍建立 `Voice Puck V1` 输入和输出两个 CoreAudio 端点；蓝牙设置仍把设备类型显示为“免提设备”。

随后分别清除 Mac 配对和 ESP32 NVS 中的旧密钥，并用 macOS `IOBluetoothDevicePair` 对同一设备地址重新配对。原版固件的 Class of Device 实测为 `0x240408`（Audio/Video，Hands-free 子类别）；实验固件重新配对并连接后为 `0x280410`（Audio/Video，Microphone 子类别）。macOS 蓝牙系统信息也显示 `device_minorType: Microphone`，证明类别修改确实生效。与此同时，CoreAudio 仍列出 `Voice Puck V1` 的一个 1 通道输入端点和一个 1 通道输出端点；Mac 默认输出保持为内置扬声器。重新配对排除了旧缓存因素。

实验结束后，已刷回主线 HFP 固件并保持新配对：Class of Device 恢复为 `0x240408`，Mac 再次列出输入和输出，默认输入为 Voice Puck V1、默认输出为 MacBook Pro 扬声器。

## 结论与后续

实验已经完成。把 Class of Device 设置为 Microphone 能改变蓝牙设备类别，但不能消除 HFP 在 macOS 上的输出端点；不要将这项改动作为“仅输入”解决方案合并到 V1 主线。

HFP 的 HF 角色是音频网关的远程输入和输出。本次实测表明当前 ESP32 HFP 路线不能满足“系统仅显示输入”的验收条件。LE Audio 协议可以分别声明 Source 和 Sink，但乐鑫的 ESP32 支持表显示原版 ESP32 不支持 ESP-BLE-ISO / ESP-BLE-AUDIO；更换到支持 LE Audio 的芯片后，仍须在目标 Mac 上实测兼容性。另一方向是自定义无线传输加 Mac 端虚拟输入设备，但会增加 Mac 端软件。

## 资料

- [Bluetooth SIG Hands-Free Profile](https://www.bluetooth.com/specifications/specs/hands-free-profile-1-10/)
- [Bluetooth SIG Assigned Numbers：Class of Device](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Assigned_Numbers/out/en/index-en.html)
- [Bluetooth SIG Basic Audio Profile](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/BAP_v1.0/out/en/index-en.html)
- [乐鑫 ESP32 蓝牙 LE 支持表](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/ble/overview.html)
