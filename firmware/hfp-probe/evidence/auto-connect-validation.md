# 上次设备自动重连实物验证

2026-09-30（Asia/Shanghai），ESP32-WROOM-32 + 本机已配对 Mac。

## 实现及本地检查

- 移除固件中固定的电脑蓝牙地址。HFP SLC 成功后写入 `voxu/last_peer` NVS；启动读取该地址，HID 跟随实际 HFP 主机。
- 从旧固件升级时无历史记录，串口输出 `no previous host; pair/connect from the computer once`。本机发起连接后输出 `save last connected host: ESP_OK`；同时观察到 HID 和 mSBC 音频连接。
- 两组主机 C 测试通过（重连策略、BOOT 消抖），PlatformIO / ESP-IDF 6.1.0 编译成功，并通过 USB 串口刷入，烧录校验成功。
- 最终固件源代码提交：`87f3b74`；固件 SHA-256：`e5b2827be2fba9d376e23c5929f325c606f62099229fbe60d34de3bc89e8a1c9`。

## 重启验证

通过串口 RTS/EN 复位；每轮均要求观察到读取 NVS、固件主动连接请求、HFP SLC 与 HID 全部成功，全程未手动点击连接。

1. 正常重启：487 ms 读取 NVS，1197 ms 主动发起连接，6567 ms HFP SLC 成功，6687 ms HID 成功。
2. 快速重启：2317 ms 出现 `HF Client found collision (ACL)`，底层未完成请求；61167 ms 触发 `HFP setup stalled for 60s; restarting to recover Bluetooth`。自动重启后 3697 ms HFP SLC 成功，5587 ms HID 成功。

3. 再次快速重启：同样触发超时自动恢复；恢复启动后 3097 ms HFP SLC 成功、5587 ms HID 成功。这轮后半程已关闭系统蓝牙设置窗口。三轮测试均通过，最终 macOS 确认 `connected=true paired=true`，服务为 `HFP HID ACL`。

旧固件/初版修复在快速重启碰撞后，曾持续 65 秒仍无 HFP/HID 连接。SDK 的连接队列会保持 busy，重复提交连接无法解除；当前固件只在尚未建立 HFP 且请求卡住 60 秒时自动重启恢复。普通失败回调后等待 5 秒再次连接；健康连接不会触发该超时恢复。

## 验证边界

本次使用同一台 Mac 验证持久存储和重启连接。切换到另一地址的目标选择有主机回归覆盖，未进行第二台实体电脑的配对验证。未验证整机断电、电脑关机/合盖恢复、长时间稳定性；RTS/EN 复位不能等同于断电测试。既有 HID 底层缓存报告边界不在本次修复范围。
