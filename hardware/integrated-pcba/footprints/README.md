# VOXU 封装交换库（工程草稿）

用途：导入嘉立创 EDA 专业版个人库后关联原理图。此目录采用 KiCad 封装交换格式；最终 PCB 在立创 EDA 专业版完成。文件可解析不等于可生产，须复核转换后铜皮、阻焊、钢网、编号和 3D。

`generate.py` 生成四种原厂专用封装：

- CP2102N QFN28：外围焊盘 0.95×0.30 mm，中心距 4.8 mm，中央铜 3.35×3.35 mm，钢网四个 1.2 mm 窗、1.5 mm 间距，阻焊扩展 0.06 mm。[Silicon Labs Rev1.5 图6.2](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf)。
- BQ24075 RGT0016C：中央铜 1.68×1.68 mm，钢网 1.55×1.55 mm，外围 0.6×0.24 mm、中心距2.8 mm；修正此前误用的 1.45 mm 通用中央焊盘。未放置开放的盘中孔。[TI 4222419/E 07/2025](https://www.ti.com/lit/ds/symlink/bq24075.pdf)。
- TPS63070 RNM0015A：非对称15脚；7/8及12/13成对桥接；7–13采用阻焊定义；9/10/11分窗钢网。需要检查转换后重复焊盘和独立钢网是否保留。[TI 4222000/B 03/2020](https://www.ti.com/lit/ds/symlink/tps63070.pdf)。
- XFL4020：焊盘0.98×3.4 mm、中心距2.37 mm。[Coilcraft 745-3](https://www.coilcraft.com/getmedia/50632d43-da1b-4cdb-8ab4-3029cab51df3/xfl4020.pdf)。电感为候选，成本和国内供货未锁定。

另外七种封装源自官方 KiCad 10.0.7 库，来源及改动记录在 `upstream.json`。原库许可证为 CC-BY-SA 4.0，附 KiCad 库例外：[许可证](https://www.kicad.org/libraries/license/)。USB屏蔽焊盘SH改为电路中的S1；开关金属固定脚及JST机械固定脚改为空编号，保持机械铜焊盘。其他几何未更改。

JST PH 3pin 定义为 1=BAT+、2=NTC、3=GND；并不声称通用在售电池线序符合。采购电池必须与此接口匹配。
