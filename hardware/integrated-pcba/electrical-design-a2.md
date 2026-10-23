# A2 整板电气设计草稿

状态：可审阅电气源文件；不是生产版，不能上传为实际 SMT 订单。

## 当前文件

- `schematic/mainboard.kicad_sch`：64 个器件的整板电气草稿，内嵌符号。
- `schematic/mainboard-circuit.json`：引脚、网络及候选封装的机器可读清单。
- `schematic/mainboard-bom-draft.csv`：逐器件设计清单；未完成料号、封装和采购资格核定，不是采购 BOM。
- `schematic/mainboard.py`：生成以上文件。
- `schematic/check_mainboard.py`：连接约束、供电公差和下载逻辑检查。
- `schematic/electrical-checks.json`：计算结果和明确的未完成项。

## 与 A1 的变化

保留 ESP32-WROOM-32E、BQ24075、TPS63070；麦克风改为 SPH0655LM4H-1-8，使用 GPIO26/33，GPIO25 悬空。增加单 USB-C、ESD、关机域缓冲、下载互锁和板载开关的逐引脚连接。

CH340C 暂不进入本版整板草稿，USB 桥候选改为 CP2102N-A02-GQFN28。理由是其内置 BC1.2 检测及充电电流状态输出，可用于处理普通电脑 USB 端口、挂起和专用充电器。此替换尚未通过采购价格比较，不宣称成本低于 CH340C；CH340C 加外部检测电路的完整成本才是有效比较对象。旧有四颗芯片 ¥40.62/板不再是本草稿的核心器件价格。

## USB 与充电控制

CP2102N 必须先通过 Silicon Labs 工具启用 Battery Charging，并配置 CHR0 对应 GPIO 为原厂要求的输出模式，USB Max Power 描述符应与 500mA 预算一致。普通 UART 固件烧录不能代替这一步。具体可导入的配置文件、初始化操作和实物行为尚未验证，列为生产阻断项。

未取得 500mA 授权时不开放 BQ24075 输入：EN2 接 USB_3V3，EN1 由 10k 上拉，二者为高即 Standby。CHR0 有效时通过 Q4 拉低 EN1，进入 ILIM 可编程限流模式。这样不使用 BQ 固定 500mA 档再额外叠加 USB 桥耗电，也不使用其 100mA 档叠加桥耗电。

- R_ILIM=3.9kΩ/1%，按原厂 K_ILIM=1330..1720AΩ，限流约 338..445mA。
- 给 USB 桥、缓冲、上拉及检测等另留 50mA 设计额度，合计上界约 495mA。CP2102N 数据手册只给工作电流典型值，50mA 是待实测的设计额度，不是原厂保证值。
- R_ISET=8.66kΩ/1%，原厂 K_ISET=797..975AΩ，对应充电电流约 91..114mA；最大电阻未越过 8.9kΩ 推荐上界。
- TS 接电池真实 10k NTC，禁止装固定电阻冒充电芯温度。
- TMR 悬空使用默认安全计时；SYSOFF 接地。运行开关只控制稳压 EN，关机不切断充电通路。
- 受保护电池在 USB 枚举前、挂起和峰值负载时供电；不能承诺未插电池的所有启动工况。
- USB VBUS sense 分压按电阻公差及 150µA 输入漏电作下限检查；USB 插拔瞬态、掉电过程及挂起电流仍需验证。

## 跨电源域与下载

三个相同 SN74LVC2G125DCUR 避免引入多种缓冲料号。U4/U5 用系统 3V3，处理 USB TX/DTR/RTS；U6 用 USB_3V3，处理 ESP TX。器件须保留 Ioff 特性，不能用无断电高阻规格的廉价型号替代。

USB 不在时由 Q1/OE 上拉关闭系统侧缓冲，系统 RX/DTR/RTS 回到高电平。Q2/Q3 采用交叉发射极下载互锁，两路同时拉低时不会持续复位。没有采用直接把 USB 域 RTS/DTR 接到未供电 ESP32 的做法。

## 稳压与音频

TPS63070 固定强制 PWM（PS/SYNC=GND），以降低轻载 PFM 对音频的干扰；待测待机耗电可能高于 PFM。反馈 470k/150k，考虑 1% 参考和电阻误差计算约 3.224..3.391V，在 ESP32 与 SPH0655 供电范围内。此计算未包括纹波和负载瞬态。

滤波按原厂 1.5µH、输入 2×10µF+近端10µF、输出3×22µF+近端10µF 的参考组合。采购替换必须检查直流偏压下的有效电容和电感饱和电流，不能只按标称容量、封装及价格选件。RNM 是非对称 15 引脚封装，不能套用通用 QFN。

SPH0655LM4H-1-8 / C22376158：1 DATA=MIC_SD，2 SELECT=GND，3 GND，4 CLOCK=MIC_BCLK，5 VDD=3V3。C4 为近端 100nF，DATA 保留 100k 下拉。SELECT 接地，数据下降沿更新、上升沿采样；ESP32 I2S0 使用 PDM-to-PCM、LEFT 槽、16kHz、128 倍抽取，得到 2.048MHz 时钟。GPIO25 已标注不连接。封装声孔 0.65mm，在厂家推荐的 0.6–1.0mm 范围内；钢网、DFM 及实物效果仍需核定。

## 生产阻断项

1. CP2102N-A02-GQFN28R C964632 已找到目录库存和参考价；包装后缀确认、BCD 初始化和 USB 描述符尚未完成生产核定。
2. 新电池供应商型号、充放电能力、NTC曲线、插头极性未知。J2 当前1=正极、2=NTC、3=负极仅是设计定义，不是某个在售电池的接线声明。
3. 全部 64 个封装已绑定，采购候选表覆盖全部位号；器件数据手册、装配工艺与精确采购后缀的最终核定仍待完成。
4. 已完成 45 × 37 mm 双层 PCB 和原生 DRC（141 项、0 问题），213 个连接引脚与电气清单一致。Gerber 界面曾显示成功，但本地 ZIP 未取得；DFM、钢网和制造文件独立审核仍待完成。DRC 不等于生产或功能验证。
5. 一块成品实际价格必须用最终设计在嘉立创匹配；不把64个器件当作64种收费料，也不把计算器的25种假设延用到本版。

## 原厂依据

- [BQ24075 数据手册 SLUS810N](https://www.ti.com/lit/ds/symlink/bq24075.pdf)：引脚表、EN1/EN2模式表、电气特性中的K_ILIM和K_ISET。网页转文本有行错位，已用原PDF文本复核，特别是10/11脚OUT。
- [TPS63070 SLVSC58B](https://www.ti.com/lit/ds/symlink/tps63070.pdf)：引脚表、9.2.1参考BOM、9.2.2反馈与LC选择。
- [CP2102N](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf)：2.3 VBUS检测分压、4.3.4 BCD、5.1 QFN28引脚。
- [SN74LVC2G125](https://www.ti.com/lit/ds/symlink/sn74lvc2g125.pdf)：DCU引脚、Ioff断电高阻。
- [ESP32-WROOM-32E/32UE](https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32e_esp32-wroom-32ue_datasheet_en.pdf)：引脚及供电要求。
- [INMP441 商品及原厂规格书入口](https://item.szlcsc.com/6315022.html)：DS-INMP441-00 Rev1.1，表1/6、图14/15；原TDK旧PDF路径已重定向，使用该入口提供的原厂PDF核对。

- [SPH0655LM4H-1 Rev D](https://atta.szlcsc.com/upload/public/pdf/source/20250721/5475C98035E60ADDD1C93C8246A1E933.pdf)：供电、时钟模式、引脚、底部声孔及启动时序。
