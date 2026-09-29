# BOOT / F13 验证记录

日期：2026-09-29；设备：ESP32-D0WD-V3 / ESP32-WROOM-32 + INMP441；主机：当前配置中的 Mac；Typeless：v2.8.1。

固件代码提交：40e2248（后续提交仅补充文档）。PlatformIO 编译和刷入成功，Flash hash 校验通过。HID Report 的按下为 `00 00 68 00 00 00 00 00`，松开为八个零；0x68 是 F13，无修饰键。

## Mac 与 Typeless

- macOS IORegistry 将 Voice Puck V1 列为 Bluetooth HID 键盘（Generic Desktop / Keyboard，八字节输入报告），同时 AVFoundation 音频设备列表仍包含 Voice Puck V1。
- Typeless 设置实际显示 Fn、Right Cmd、F13 三条独立语音输入绑定，麦克风为“自动检测 (Voice Puck V1)”。F13 由用户按下 BOOT 录入。
- 用户验收原话：“已录入 F13，开始/结束和出字都正常”。听写出字结果由用户确认，未保存私人听写内容。

## 设备侧串口摘录

括号中的数字为启动后的毫秒数；这些日志证明设备侧发送及与 SCO 共存，不能单独证明 Typeless 出字。

```text
I (1157) BOOT_HID: HID registered status=0
I (1157) BOOT_HID: BOOT GPIO0 ready; shortcut F13, tap to toggle
I (26637) VOICE_PUCK: HFP connection state=3
I (26817) BOOT_HID: HID open status=0 state=0
I (26837) BOOT_HID: shortcut up: sent
I (147707) BOOT_HID: BOOT pressed: F13
I (147707) BOOT_HID: shortcut down: sent
I (147787) BOOT_HID: shortcut up: sent
I (150417) BOOT_HID: BOOT pressed: F13
I (150417) BOOT_HID: shortcut down: sent
I (150497) BOOT_HID: shortcut up: sent
I (150697) VOICE_PUCK: SCO audio state=3
I (150697) VOICE_PUCK: audio ready: mSBC 16 kHz
I (151187) BOOT_HID: BOOT pressed: F13
I (151197) BOOT_HID: shortcut down: sent
I (151287) BOOT_HID: shortcut up: sent
I (152827) BOOT_HID: BOOT pressed: F13
I (152847) BOOT_HID: shortcut down: sent
I (152937) BOOT_HID: shortcut up: sent
I (155437) BOOT_HID: BOOT pressed: F13
I (155457) BOOT_HID: shortcut down: sent
I (155547) BOOT_HID: shortcut up: sent
I (157837) VOICE_PUCK: SCO audio state=0
```

## 未覆盖与已知限制

本轮没有测试合盖、长时间稳定性、完整断线恢复或所有快捷键冲突。独立代码审阅确认：报告提交期间若断线，ESP-IDF 可能自动重连并发送缓存的 F13；该边界仍未解决。主机测试只覆盖应用按键消抖和重新武装逻辑，不覆盖蓝牙栈竞态。
