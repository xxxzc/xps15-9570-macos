## 配置

| 型号   | XPS15-9570/MacBookPro15,1    | 版本   | 10.15.6 19G73       |
| :----- | :--------------------------- | :----- | :------------------ |
| 处理器 | Intel Core i5-8300H/i7-8750H | 图形   | UHD Graphics 630    |
| 内存   | Micron 2400MHz DDR4 8GB x2   | 硬盘   | Samsung PM961 512GB |
| 声卡   | Realtek ALC298               | 网卡   | Dell Wireless 1830  |
| 内屏   | Sharp LQ156D1 UHD            | 显示器 | HKC GF40 FHD 144Hz  |

### 不工作的设备

- 独立显卡
- 雷电
- 指纹
- SD卡（可以试试 [Sinetek-rtsx](https://github.com/cholonam/Sinetek-rtsx)）
- 蓝牙可能不工作（[解释](https://github.com/xxxzc/xps15-9570-macos/issues/26)）

## 安装

**请下载 [最新的 release](https://github.com/xxxzc/xps15-9570-macos/releases/latest).**

请尽量避免使用 *Clover Configurator* 或者 *OC Configurator* 打开配置文件，建议直接使用代码编辑器打开。

如果你修改了ACPI/Kexts/Drivers，你可以运行 `python3 update.py --sync` 将这些修改应用到 OC 和 CLOVER，它会自动更新这些信息到 config.plist。

可以参考 [[EN] bavariancake/XPS9570-macOS](https://github.com/bavariancake/XPS9570-macOS) and [[CN] LuletterSoul/Dell-XPS-15-9570-macOS-Mojave](https://github.com/LuletterSoul/Dell-XPS-15-9570-macOS-Mojave) 的安装教程和一些常见问题的解决方法。但使用本库的配置遇到问题时，请在本库创建 issue。

### Big Sur

最新 release 的 OpenCore 可以安装或者 OTA 到 Big Sur 公测版。**但是**安装到 SM961/PM961 很有可能失败，我尝试了各种姿势都没用，请自负风险。

**对于 4K 内屏用户**，目前你需要先运行 `python3 update.py --bigsur` 来修改你的内屏 EDID 使内屏运行于 48Hz 否则内屏在 Big Sur 上将点不亮。不用担心，它只是在 config.plist 文件中使用 `AAPL00,override-no-connect` 属性覆盖 EDID，随时可以去除。

### FHD内屏

如果你的笔记本内屏是1080p，你需要修改以下两个配置（不要使用 plist 编辑器）：

- 找到 `uiscale`，CLOVER 将值修改为 `1` ，OC 修改为 `AQ==`
- 找到 `dpcd-max-link-rate`，将值修改为 `CgAAAA==`

或者运行 `python3 update.py --display fhd`。

## 安装后

### 静默启动

默认下开机参数中有 `-v` ，会在启动过程中打印 logs 到屏幕上，删除它以关闭啰嗦模式：

```python
python3 update.py --set bootarg--v
```

### 耳机

耳机在电池模式下有几率在使用一段时间后产生杂音，请下载 [ComboJack](https://github.com/hackintosh-stuff/ComboJack/tree/master/ComboJack_Installer) 并运行其中的 install.sh 安装该耳机守护进程。

### 睡眠和唤醒

请运行以下指令以保证正常睡眠：

```shell
sudo pmset -a hibernatemode 0
sudo pmset -a autopoweroff 0
sudo pmset -a standby 0
sudo pmset -a proximitywake 0
```

或者执行  `python3 update.py --fixsleep`。

请将除了“当显示器关闭时，防止电脑自动进入睡眠”是可选的外，请关闭设置-节能器里的所有其他选项。

### 三码

请使用你自己的三码（SN，MLB 和 SmUUID），你可以复制一份 [smbios.plist](./smbios.plist)，将其中的 `sn mlb smuuid` 修改为你自己的，然后运行 `python3 update.py --smbios xxx.plist`，`xxx.plist` 为你的 smbios plist 文件。

如果你没有三码，你可以运行 `python3 update.py --gen` 来生成一份新的三码，会自动保存到 `gen_smbios.plist` 和 config 中。

建议你使用 Windows 的 UUID 作为 SmUUID，特别是如果你需要使用 OpenCore 启动 Windows：在 Windows 的 CMD 中运行 `wmic csproduct get UUID` 即可得到该 UUID。

### 平滑字体

如果你的内屏是1080p，或者使用1080p的显示器，请运行以下指令以启动字体平滑：

```
defaults write -g CGFontRenderingFontSmoothingDisabled -bool NO
```

### CLOVER主题

可以使用如下执行设置 CLOVER 的主题为 [themes](https://sourceforge.net/p/cloverefiboot/themes/ci/master/tree/themes/) 中的某个主题（xxx 为主题名）：

```sh
python3 update.py --set theme=xxx
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