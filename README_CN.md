## 配置

| 型号      | XPS15-9570/MacBookPro15,1    | Version  | 10.15.5 19F101      |
| :-------- | :--------------------------- | :------- | :------------------ |
| Processor | Intel Core i5-8300H/i7-8750H | Graphics | UHD Graphics 630    |
| Memory    | Micron 2400MHz DDR4 8GB x2   | Disk     | Samsung PM961 512GB |
| Audio     | Realtek ALC298               | 网卡     | Dell Wireless 1830  |
| Display   | Sharp LQ156D1 UHD            | Monitor  | HKC GF40 FHD 144Hz  |

### 不工作的设备

- 独立显卡
- 雷电
- 指纹
- SD卡（可以试试 [Sinetek-rtsx](https://github.com/cholonam/Sinetek-rtsx)）
- 蓝牙可能不工作

## 安装

**请下载 [最新的 release](https://github.com/xxxzc/xps15-9570-macos/releases/latest).**

可以参考 [[EN] bavariancake/XPS9570-macOS](https://github.com/bavariancake/XPS9570-macOS) and [[CN] LuletterSoul/Dell-XPS-15-9570-macOS-Mojave](https://github.com/LuletterSoul/Dell-XPS-15-9570-macOS-Mojave) 的安装教程和一些常见问题的解决方法。但使用本库的配置遇到问题时，请在本库创建 issue。

### FHD内屏

如果你的笔记本内屏是1080p，你需要修改以下两个配置：

1. UIScale.
   - OC:  `NVRAM/Add/4D1EDE05-38C7-4A6A-9CC6-4BCCA8B38C14/UIScale`  -> `AQ==`
   - CLOVER: `BootGraphics/UIScale` -> `1`
2. dpcd-max-link-rate.
   - OC: `DeviceProperties/Add/PciRoot(0x0)/Pci(0x2,0x0)/dpcd-max-link-rate` -> `CgAAAA==`
   - CLOVER: `Devices/Properties/PciRoot(0x0)/Pci(0x2,0x0)/dpcd-max-link-rate` -> `CgAAAA==`

### DW1820a

如果你使用 DW1820a，请在 config.plist 中找到 `#PciRoot(0x0)/Pci(0x1c,0x0)/Pci(0x0,0x0)` 并将前缀的“#”删除。

参考 [THE Solution:Dell DW1820A](https://www.tonymacx86.com/threads/the-solution-dell-dw1820a-broadcom-bcm94350zae-macos-15.288026/)

## 安装后

### 静默启动

默认下开机参数中有 `-v` ，会在启动过程中打印 logs 到屏幕上，删除它以关闭啰嗦模式：

```python
python3 update.py --set bootarg--v
```

### 耳机

耳机在电池模式下有几率在使用一段时间后产生杂音，请下载 [ComboJack](https://github.com/hackintosh-stuff/ComboJack/tree/master/ComboJack_Installer) 并运行其中的 install.sh 安装该耳机守护进程。

### 睡眠和唤醒

1. 请运行以下指令以保证正常睡眠：

```shell
sudo pmset -a hibernatemode 0
sudo pmset -a autopoweroff 0
sudo pmset -a standby 0
sudo pmset -a proximitywake 0
```

或者执行  `python3 update.py --fixsleep`。

2. 除了“当显示器关闭时，防止电脑自动进入睡眠”是可选的外，请关闭设置-节能器里的所有其他选项。

### 三码

请使用你自己的三码 SN, MLB (可以使用 [MacInfoPkg](https://github.com/acidanthera/MacInfoPkg) 或 Clover Configurator 或 [Hackintool](https://www.tonymacx86.com/threads/release-hackintool-v2-8-6.254559/) 生成新的) 或者：

```sh
python3 update.py --gen # 生成并使用新的 SN, MLB and SmUUID
```

如果你需要使用 OpenCore 启动 Windows，请使用 Windows 的 UUID：在 Windows 的 CMD 中运行 `wmic csproduct get UUID` 即可得到该 UUID。

运行 `python3 update.py --set sn=xxx mlb=yyy smuuid=zzz` 即可设置三码。

### 平滑字体

如果你的内屏是1080p，或者使用1080p的显示器，请运行以下指令以启动字体平滑：

```
defaults write -g CGFontRenderingFontSmoothingDisabled -bool NO
```

### CLOVER主题

可以使用如下执行设置 CLOVER 的主题为 [themes](https://sourceforge.net/p/cloverefiboot/themes/ci/master/tree/themes/) 中的某个主题（xxx 为主题名）：

```sh
python3 update.py --set theme=xxx # will download if not exist
```

### NTFS写入

你需要将 `UUID=xxx none ntfs rw,auto,nobrowse` 添加到 `/etc/fstab` 中，**xxx** 为你的 NTFS 分区的 UUID。

如果你的 NTFS 分区装有 Windows，你需要先在 Windows 的 powershell 上运行 `powercfg -h off` 关闭 Windows 的休眠。

### 触摸板单双击延迟

- 关闭拖拽或者使用三指拖拽可以避免单击的延迟
- 关闭智能缩放可以避免双击的延迟

参考 [is-it-possible-to-get-rid-of-the-delay-between-right-clicking-and-seeing-the-context-menu](https://apple.stackexchange.com/a/218181)

## 感谢

- [acidanthera](https://github.com/acidanthera) 提供绝大部分的驱动
- [alexandred](https://github.com/alexandred) 提供 VoodooI2C
- [headkaze](https://github.com/headkaze) 提供非常有用的 [Hackintool](https://www.tonymacx86.com/threads/release-hackintool-v2-8-6.254559/)
- [daliansky](https://github.com/daliansky) 提供非常详尽的 OpenCore 补丁教程 [OC-little](https://github.com/daliansky/OC-little/) 以及最新的解决方法 [XiaoMi-Pro-Hackintosh](https://github.com/daliansky/XiaoMi-Pro-Hackintosh) [黑果小兵的部落阁](https://blog.daliansky.net/)
- [RehabMan](https://github.com/RehabMan) 提供的热补丁 [hotpatches](https://github.com/RehabMan/OS-X-Clover-Laptop-Config/tree/master/hotpatch) 和热补丁教程
- [knnspeed](https://www.tonymacx86.com/threads/guide-dell-xps-15-9560-4k-touch-1tb-ssd-32gb-ram-100-adobergb.224486) 提供的 Combojack 和描述详尽的热补丁以及 USB-C 热插拔解决方法
- [bavariancake](https://github.com/bavariancake/XPS9570-macOS) and [LuletterSoul](https://github.com/LuletterSoul/Dell-XPS-15-9570-macOS-Mojave) 提供的详尽的安装教程