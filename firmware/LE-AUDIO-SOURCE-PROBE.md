# LE Audio 单向麦克风实机验证

## 目标与当前边界

验收目标是同一台 Mac 与 Voice Puck 蓝牙连接后，系统音频输入列表中有 Voice Puck，输出列表中没有 Voice Puck，并能采集真实麦克风声音。使用 `tools/check-input-only.c` 检查 CoreAudio 端点，再用系统设置和录音核对实际设备身份及数据路径。

现有 ESP32-D0WD-V3 的 HFP 路线已实测产生一个输入和一个输出端点。仅把 Bluetooth Class of Device 改成 Microphone 并重新配对后仍如此，详见 `hfp-probe/INPUT-ONLY-EXPERIMENT.md`。乐鑫的原版 ESP32 蓝牙能力表也不支持 ESP-BLE-ISO / ESP-BLE-AUDIO，因此现有主控不能直接刷入 LE Audio 固件。

## 下一块验证硬件

候选是 **ESP32-S31 Function CoreBoard**：乐鑫提供现成开发板、板载麦克风和 USB 调试接口；ESP32-S31 的 ESP-IDF 文档列出 LE Audio / ISO 和 BAP Unicast Server 支持。先用板载麦克风验证 Mac 互操作性，再考虑把现有 INMP441 接入及重新设计小型外壳。开发板是实验候选，不是 V1 BOM 的采购承诺。

目标固件只声明 **BAP Unicast Server 的 Source ASE**（设备向 Mac 送音频），不声明 Sink ASE，也不启用 HFP 或其他可创建输出端点的音频服务。先从乐鑫 `bluetooth/esp_ble_audio/bap/unicast_server` 官方示例移植，确认示例中 Source/Sink ASE 数量、PACS 能力、LC3 编码和广告数据与目标一致。只修改角色声明并不能保证 macOS 建立输入设备；必须完成下述实机测试。

## 到板后验收顺序

1. 记录 ESP-IDF 版本、开发板版本和 Mac 的 macOS 版本。当前目标机实测为 macOS 27.0、Mac17,9、Apple N1 蓝牙控制器；`system_profiler SPBluetoothDataType` 的控制器服务包含 `LEA`。这只说明控制器报告 LEA 能力。
2. 编译并刷入官方 BAP Unicast Server 示例，先确认蓝牙广播、连接和 Source ASE 的实际配置；关闭 Sink ASE。记录串口日志。
3. 在 Mac 上忽略旧的 `Voice Puck V1` HFP 配对，再配对实验设备。区分旧 ESP32 和新开发板的蓝牙地址、服务和名称，避免把旧设备端点算入结果。
4. 检查「系统设置 → 声音」的输入与输出列表，并运行 `tools/check-input-only.c`。必须同时满足：至少一个目标输入端点、零个目标输出端点。
5. 用开发板板载麦克风录音，确认声音确实从新开发板传入，而非 Mac 内置麦克风或仅有同名虚拟端点。再测试断线重连后端点是否仍符合要求。
6. 如果 Mac 无法发现、配对或建立 Source 流，保存 macOS 蓝牙信息、CoreAudio 枚举和设备串口日志，再判断是广告/Profile、固件状态机还是主机互操作性问题；不要把控制器 `LEA` 标记当作兼容性通过。

## 参考资料

- [乐鑫 ESP32 BLE 功能概览](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/ble/overview.html)
- [乐鑫 ESP32-S31 LE Audio 支持状态](https://docs.espressif.com/projects/esp-idf/en/v6.1/esp32s31/api-guides/esp-ble-audio/ble-audio-feature-support-status.html)
- [乐鑫 ESP32-S31 Function CoreBoard](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s31/esp32-s31-function-coreboard-1/user_guide.html)
- [乐鑫 ESP-BLE-AUDIO API 与示例](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s31/api-reference/bluetooth/esp-ble-audio.html)
