# Voice Puck V1：Mac HFP 采音验证

此工程是原版 ESP32 + INMP441 的单机验证固件。它把 D26/D25/D33 上的 I²S 麦克风采样转换成 16 位单声道 PCM，并通过 Bluetooth Classic HFP HF 的 HCI 音频路径送给 Mac。另通过 Bluetooth Classic HID 键盘服务，把 BOOT（GPIO0）映射为一次 `F13` 快捷键。没有电池管理、扬声器或自动静音。

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

固件记住最后一次成功建立 HFP 服务连接的设备地址，并保存在 NVS 中。后续开机直接连接该设备，失败或断线后等待 5 秒重试；连接进行中或已连接时不重复请求。没有历史记录时等待电脑首次配对/连接，成功后自动记住它。已有配对信息保留，但升级前没有保存的历史连接顺序不会凭空推断。

## 2026-09-29 实测

- ESP32-D0WD-V3 / ESP32-WROOM-32 与 INMP441 的 I²S 采样正常；HFP 服务连接成功，Mac 将设备列为 1 声道输入，同时也列出一个无实际扬声器的输出端点。
- Mac 默认输入选为 `Voice Puck V1` 后，SCO 接通并协商为 mSBC 16 kHz；测试结束时连接仍在。
- MacBook Pro 扬声器播放 1 kHz、3 秒测试音，同时用 Mac 的 `Voice Puck V1` 输入录制 9 秒。录音的 1 kHz 分量在播放前后约 0–2，播放期间约 147–163（16 位 PCM 幅度单位）。这验证了声音从 INMP441 经 ESP32、HFP 回到 Mac 的完整路径。
- 原始测试音为 [1khz-test-tone.wav](evidence/1khz-test-tone.wav)，蓝牙麦克风实际录音为 （实录音频已移除，仅保留测量记录）。

上述初始 HFP 测试尚未验证 Typeless 听写；后续 BOOT/F13 验证见下文。合盖场景、长时间稳定性、长期重连稳定性和语音音质评估仍未完成。测试固件会在 Mac 仍选择该设备输入时持续通过蓝牙发送音频。

## BOOT 触发 Typeless（按一下开始，再按一下结束）

正常启动后按 BOOT；不要在上电或按 EN 复位时按住 BOOT，否则会进入下载模式。EN 是复位键，不能用作业务按键。无需添加按钮模块或更改麦克风接线。

- 每次有效按下发送 `F13`（单键，无修饰键），80 ms 后释放全部按键。长按不重复发送；松开 BOOT 本身不发送第二次快捷键。
- GPIO0 使用上拉输入，30 ms 消抖。应用已知 HID 未连接时不缓存 BOOT 事件；连接时先释放全部键，必须先松开再按。
- 使用现有 Classic 蓝牙栈，同时提供 HFP 音频与 HID 键盘。HFP 连上后向同一设备尝试连接 HID；日志 `HID open status=0 state=0` 表示 HID 已连接。
- 串口 `BOOT pressed`、`shortcut down: sent`、`shortcut up: sent` 只能证明设备侧按键与发送，仍须在 Mac/Typeless 确认快捷键与听写结果。
- 连接目标跟随最后一次成功的 HFP 连接；当前实物测试仍以 Mac 为主，不保证其他系统兼容、休眠恢复或量产重连可靠性。

### Typeless 设置与验收

1. 刷入后连接 `Voice Puck V1`。如果 Mac 缓存了旧设备的 HFP 服务，可能需要移除该蓝牙设备并重新配对，才能枚举新增的 HID 键盘。
2. Typeless 设置 → 快捷键 → 语音输入 → **添加另一个**，按一次 BOOT，确认录入 `F13`。保留原有 Fn/其他绑定。F13 不在 MacBook 内建键盘上，由 ESP32 发送；是否接受以当前 Typeless 实测为准。
3. 麦克风选择 `Voice Puck V1`（或自动检测且当前系统输入为该设备），输出仍使用 Mac 扬声器。
4. 在测试文本框中按 BOOT，确认开始录音；说一句测试语，再按 BOOT，确认停止并输出文字。连续重复，并长按 BOOT 检查没有多次切换。
5. 同时确认串口 HFP/SCO 仍连接、普通键盘没有修饰键残留。

Typeless 当前版本最多接受三个键；本固件只发一个 F13。快捷键降低常见冲突概率，不保证与用户自定义绑定绝对无冲突。固件只发送快捷键，不保存“正在听写”的状态；实际开始/结束由 Typeless 决定。

### 本地按键回归测试

从仓库根目录执行：

```sh
cc -std=c11 -Wall -Wextra -Werror -Ifirmware/hfp-probe/src \
  firmware/hfp-probe/tests/boot_button_test.c firmware/hfp-probe/src/boot_button.c \
  -o /tmp/voxu-boot-test && /tmp/voxu-boot-test
```

覆盖接触抖动、长按不重复、第二次按下、启动时按住、断线重连时按住和计时器回绕。此测试不能替代硬件 HID/HFP 共存与 Typeless 验证。

### 已知断线边界

报告提交期间若突然断线，ESP-IDF 的 Classic HID 栈可能缓存报告并在自动重连后发送，产生一次额外 F13。本单机验证固件暂不保证此窗口内不会额外触发。应用连接状态检查与重连后释放不能撤销底层已经发出的事件；量产前需专门验证并解决此边界，不能把上述主机消抖测试当作完整重连保证。

## 2026-09-29 BOOT / F13 实物验收

- 最新测试固件使用 **单键 F13**，不带 Control / Option / Shift / Command。五键组合被当前 Typeless 的“三个或更少的键”限制拒绝，最终使用单键方案。
- Mac 已枚举 `Voice Puck V1` 的 Bluetooth HID 键盘；Typeless 设置实际显示新增的 `F13`，原 Fn 和 Right Cmd 绑定保留，麦克风自动检测为 `Voice Puck V1`。
- 用户实物确认：“已录入 F13，开始/结束和出字都正常”。
- 串口观察到多次 `BOOT pressed: F13`，每次都有 `shortcut down: sent` 与 `shortcut up: sent`；SCO 为 mSBC 16 kHz 时仍能发送按键。
- 验证的是本机原型的正常连接路径；已知断线边界仍未解决，长时间稳定性未测。
- 精简证据：[boot-f13-validation.md](evidence/boot-f13-validation.md)。

## 开机自动连接

上一次连接的电脑蓝牙开启且在范围内时，外设启动后读取 NVS 中保存的地址，主动连接 HFP，再连接同一设备的 HID 键盘。电脑暂不可用时，每次连接失败回调后等待 5 秒继续尝试；蓝牙栈自身的连接超时不包含在这 5 秒内。手动断开也会重新连接，需停止使用时关闭外设电源。

如果底层连接请求 60 秒仍无完成回调（实测快速重启可能发生 ACL 碰撞），外设自动重启以清除蓝牙栈卡住的请求，再从 NVS 读取目标继续连接；正常已连接状态不会触发该恢复。

首次使用或从旧固件升级后，先在电脑上连接一次，以建立“上一次设备”的记录。需要换电脑时，断开原电脑后由新电脑发起配对/连接，HFP 服务成功连接才覆盖记录；未完成配对或失败的连接不会覆盖目标。没有写死任何电脑地址，也不会任意选择配对列表中的设备。

本地重连状态回归：

```sh
cc -std=c11 -Wall -Wextra -Werror -Ifirmware/hfp-probe/src \
  firmware/hfp-probe/tests/hfp_reconnect_test.c firmware/hfp-probe/src/hfp_reconnect.c \
  -o /tmp/voxu-reconnect-test && /tmp/voxu-reconnect-test
```

覆盖初始化前禁连、无历史记录时等待配对、切换到最新连接设备、相同设备不重复写入、就绪后立即连接、异步连接期间禁止重复请求、失败/断线延迟重试、请求卡住超时恢复、正常连接不重启和计时器回绕。实物连接证据另行记录；这些主机测试不证明 Mac 休眠恢复或长期稳定性。
