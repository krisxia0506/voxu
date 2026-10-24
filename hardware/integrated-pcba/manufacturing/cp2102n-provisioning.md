# CP2102N 配置与装配交付要求

状态：待执行的工艺要求，不是已经验证的烧录包。尚无可交付的 `.configuration`、烧录日志或实物测量；不要将此文档作为烧录完成证明。

## 本板所需设置

U3 为 CP2102N-A02-GQFN28R，15 脚 CHR0 接 USB_ALLOW_500，通过 R20/Q4 拉低充电器 CHG_INHIBIT；R21 将未驱动的 USB_ALLOW_500 拉低。因此不能假定原厂默认配置即可允许充电。PCB 的 Type-C 同时连接 U3 的 USB 数据与电源，可用它进行配置，无须新增焊线。

使用 Silicon Labs Xpress Configurator 创建对应型号工程：启用 Battery Charging；按 500 mA 档配置 CHREN 为 Push-Pull/High、CHR0 为 Push-Pull/High、CHR1 为 Open Drain/Low。USB Power Mode 为 Bus-Powered；Max Power 为 500 mA（USB 描述符原始字节 0xFA；若界面单位是 mA，填写 500）。不要启用配置锁定。UART 与自动下载需要保留 TXD/RXD、DTR/RTS 的串口功能。

原厂默认 Max Power 是 100 mA，不能沿用。有关电流状态和挂起行为，依据 [CP2102N 数据手册 Rev 1.5 §4.3.4、§4.5、§5.1](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf)。本板 USB 总电流预算由充电限流约 338–445 mA 加 USB 桥等负载组成，仍需实测。

## 烧录文件与记录

配置器导出 `.configuration` 后，记录工具版本、芯片型号、文件 SHA-256 和设备序列号。原厂 AN721 支持 `cp210xsmt` 对 CP2102N 进行写入及校验；下列命令仅在已生成并审阅配置文件后执行，当前仓库没有该文件：

```text
cp210xsmt --device-count 1 --set-and-verify-config VOXU-A2-CP2102N.configuration
cp210xsmt --device-count 1 --reset
cp210xsmt --device-count 1 --verify-config VOXU-A2-CP2102N.configuration
```

保留默认唯一序列号，不批量复制序列号；失败时记录错误，不盲目重复写入。工具对已编程器件有约束，应先读取现有状态。依据 [AN721 Rev 1.5 §4.1](https://www.silabs.com/documents/public/application-notes/AN721.pdf)。

## 本项目验收步骤

1. 首次配置时关闭系统运行开关，以降低未配置状态的负载。通过 Type-C 连接电脑，先确认 U3 枚举及供电正常。
2. 写入配置、重连后读回，检查 Max Power 和充电检测设置。保留原始校验日志。
3. 普通电脑端口：检查未配置/未获授权时 CHG_INHIBIT 保持高；正常枚举授权后拉低；挂起时关闭充电输入。记录 VBUS 总电流和 CHR0 电平。
4. 专用充电器：检查识别后的充电通路；总电流不能因为端口允许更高电流而超过本板限流设计。
5. 接合格的带保护与 NTC 电池后验证充电、开关机、USB 插拔及下载。ESP32 应用固件是另一份烧录文件，两项分别留记录。

## 嘉立创服务核查（2026-10-24）

登录的 [SMT 下单页](https://www.jlc-smt.com/order)提供“贴装后烧录”，提示需要芯片型号、烧录接口与定义、正反面图片和程序文件；标价 50 元基础工程费 + 40 元/小时。它不证明嘉立创已接受 CP2102N/Xpress Configurator 工艺，也不构成此订单最终报价。当前尚未选择实际 PCB 订单，因此服务未生效、未提交。

制造审核时须核定 CP2102N 配置与 ESP32 固件烧录是否都能承接，不能把普通贴片费用理解为包含这两项。若由用户收板后通过 USB 配置，可免工厂烧录服务，但需要用户明确选择该交付方式；当前没有改变“厂家装配成品”的目标。
