# INMP441 采音冒烟测试

此程序只验证麦克风 I²S 数据，尚无蓝牙功能。接线见项目根目录的 `WIRING.md`。

板型：30 针 ESP32-WROOM-32 DevKit V1 风格；D26=SCK、D25=WS、D33=SD、L/R=GND、VDD=3V3、GND=GND。

运行后串口每约 0.25 秒打印一次 `mean_abs` 和 `peak`。对着麦克风说话时，两者应明显高于安静状态。持续为 0、固定不变或只有极端值均需要检查接线与声道配置。

## 编译、刷入与查看串口

在此目录运行：

```sh
uvx --from platformio platformio run
uvx --from platformio platformio run -t upload --upload-port /dev/cu.usbserial-110
uvx --from platformio platformio device monitor --port /dev/cu.usbserial-110 --baud 115200
```

串口名称会随电脑和 USB 插拔变化；刷入前可用 `ls /dev/cu.usbserial*` 查看。退出串口监视器使用 `Ctrl+C`。工程通过 `sdkconfig.defaults` 将 Flash 容量设为实测的 4 MB。

## 2026-09-29 实机结果

ESP32-D0WD-V3 开发板编译和刷入成功。安静时 `mean_abs` 约 1–3 万；对模块说话或轻敲时最高达到 419437，`peak` 最高达到 1020352。重新刷入 4 MB 配置后，串口仍持续输出非零采样值。此测试确认采音数据会随声音变化，尚未验证录音回放、音质或蓝牙传输。
