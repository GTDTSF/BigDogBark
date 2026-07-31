# BigDogBark 桌宠 - 单文件打包指南

本文档将指导您如何使用 `Nuitka` 将基于 PySide6 的 Python 桌宠项目编译为运行效率极高的本地代码，并利用 `Enigma Virtual Box` 将其封包为一个无需安装任何环境、双击即开的独立单文件 `.exe`。

## 1. 环境与工具准备

### 1.1 安装 Nuitka 编译工具
在项目根目录下，确保已激活环境，并安装 Nuitka：
```bash
uv add nuitka
```
*(注：首次运行 Nuitka 时，它可能会提示自动下载 MinGW-w64 (GCC 编译器) 和 Ccache，请根据提示输入 `Yes` 允许下载。)*

### 1.2 下载 Enigma Virtual Box
前往官方页面下载并安装 Enigma Virtual Box（完全免费）：
👉 [https://www.enigmaprotector.com/cn/downloads.html](https://www.enigmaprotector.com/cn/downloads.html)

---

## 2. 第一阶段：使用 Nuitka 编译独立目录 (Standalone)

首先，我们需要用 Nuitka 将 Python 脚本编译为机器码，并收sheji1集所有必要的 DLL 和依赖放入一个独立的文件夹中。

请在项目根目录（`main.py` 所在目录）运行以下打包命令：

```bash
uv run nuitka --standalone --mingw64 --output-dir=dist --remove-output --no-prefer-source-code --show-scons --windows-console-mode=disable --enable-plugin=pyside6 --enable-plugin=anti-bloat --lto=yes --python-flag=no_docstrings --python-flag=no_asserts --include-data-dir=assets=assets main.py
```

### 核心参数解析 (针对本项目定制)
* `--output-dir=dist`：输出文件夹将生成在 `dist` 目录下。
* `--windows-console-mode=disable`：隐藏黑色控制台窗口，让桌宠变成纯粹的 GUI 应用。
* `--enable-plugin=pyside6`：**必须开启**，Nuitka 专门针对 Qt 框架的打包支持，处理内部依赖和 Qt 插件。
* `--include-data-dir=assets=assets`：**非常重要**，这会将包含 `idle.gif` 和 `walk.gif` 的 `assets` 素材文件夹一并完整拷贝到最终的打包目录中。

编译过程大概需要几分钟。完成后，您会得到一个 `dist/main.dist/` 文件夹。双击里面的 `main.exe`，如果桌宠正常出现且有动画，说明第一步大功告成！

---

## 3. 第二阶段：封装为单文件 EXE (Enigma Virtual Box)

`main.dist` 文件夹虽然可以脱离 Python 环境运行，但文件太碎。我们可以用 Enigma Virtual Box 将整个文件夹“压扁”成一个单一的 `.exe`。

### 操作步骤：
1. **打开 Enigma Virtual Box**。
2. **Enter Input File Name (输入文件)**：点击 `Browse...` 选择刚才生成的 `dist/main.dist/main.exe`。
3. **Enter Output File Name (输出文件)**：它会自动生成类似于 `main_boxed.exe` 的路径，您可以将名字改成 `BigDogBark.exe`。
4. **添加虚拟文件 (Files 选项卡)**：
   * 在左下角，点击 `Add -> Add Folder Recursive`（递归添加文件夹）。
   * 选中你的 `dist/main.dist/` 文件夹（包含素材和所有 dll 的那个目录）。
   * 弹出提示要求选择目标位置时，**保留默认的 `%DEFAULT FOLDER%`** 即可，点击 OK。
   * *(注意：如果您在这里看到了原本的 main.exe，这是正常的，无需剔除。)*
5. **打包设置优化 (Files Options 选项卡)**：
   * 勾选 `Compress Files`（压缩文件），这能大幅减小最终单文件的大小。
6. **开始打包**：点击右下角的 **`Process`** (或 `打包`) 按钮。

等待进度条跑完后，你就会在输出路径得到一个终极版的 `BigDogBark.exe`。
**这个单文件程序现在可以拷贝到任何 Windows 电脑上直接运行，自带绿幕狗狗和所有的 Python 运行库！**