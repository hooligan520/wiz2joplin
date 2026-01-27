# 从 WizNote 迁移到 Joplin 或 Obsidian

## 注意事项

wiz2joplin 仅在 wizNote for Mac 2.8.7 版本上测试过。据我所知，macOS 和 Windows 版本的 wizNote 文件夹结构可能不同。

如果您能为 Windows 版本的 wizNote 提供 pull request，我相信这对很多人都会有帮助。

## 依赖要求

- Python 3.9
- macOS Catalina 或更高版本
- wizNote for Mac 2.8.7 (2020.8.20 10:28)
- ![wiznote for macOS](wiznoteformac.png)

## 安装

您可以使用 pip 安装此工具：

```bash
python -m venv ~/w2j/venv
source ~/w2j/venv/bin/activate
pip install w2j
```

或者，您可以使用打包的 setup 脚本安装：

```bash
python -m venv ~/w2j/venv
source ~/w2j/venv/bin/activate
python setup.py install
```

## 使用方法

### 迁移到 Joplin

如果您的 WizNote 用户 ID 是 `youremail@yourdomain.com`，Joplin Web Clipper 的 token 是 `aa630825022a340ecbe5d3e2f25e5f6a`，并且 Joplin 运行在同一台计算机上，您可以按以下方式使用 wiz2joplin。

将所有文档从 wizNote 迁移到 Joplin：

``` shell
w2j --target joplin -o ~/w2j -w ~/.wiznote -u youremail@yourdomain.com -t aa630825022a340ecbe5d3e2f25e5f6a -a
```

将 WizNote 中 `/My Notes/reading/` 位置及其所有子目录的文档迁移到 Joplin：

``` shell
w2j --target joplin -o ~/w2j -w ~/.wiznote -u youremail@yourdomain.com -t aa630825022a340ecbe5d3e2f25e5f6a -l '/My Note/reading/' -r
```

### 迁移到 Obsidian

将所有文档从 WizNote 迁移到 Obsidian：

``` shell
w2j --target obsidian --obsidian-vault ~/Documents/ObsidianVault -o ~/w2o -w ~/.wiznote -u youremail@yourdomain.com -a
```

将 WizNote 中 `/My Notes/reading/` 位置及其所有子目录的文档迁移到 Obsidian：

``` shell
w2j --target obsidian --obsidian-vault ~/Documents/ObsidianVault -o ~/w2o -w ~/.wiznote -u youremail@yourdomain.com -l '/My Note/reading/' -r
```

**注意**：迁移到 Obsidian 时：

- 笔记以 Markdown 文件（`.md`）格式导出到指定的 Vault 路径
- 附件保存到 `{笔记名}.md_Attachments/` 文件夹中
- 内部链接转换为 Obsidian 格式（文档链接为 `[[笔记标题]]`，附件/图片链接为 `![[附件名]]`）
- 标签同时添加到 Front Matter 和正文中（`#标签` 格式）
- 文件时间戳（创建/修改时间）会被保留

使用 `w2j --help` 查看 w2j 的使用说明：

```text
用法: w2j [-h] --output OUTPUT --wiz-dir WIZNOTE_DIR --wiz-user
           WIZNOTE_USER_ID [--target {joplin,obsidian}]
           [--joplin-token JOPLIN_TOKEN] [--joplin-host JOPLIN_HOST]
           [--joplin-port JOPLIN_PORT] [--obsidian-vault OBSIDIAN_VAULT]
           [--location LOCATION] [--location-children] [--all]

从 WizNote 迁移到 Joplin 或 Obsidian。

可选参数:
  -h, --help            显示帮助信息并退出
  --output, -o OUTPUT   解压 WizNote 文件和日志文件的输出目录。
                        例如 ~/wiz2joplin_output 或
                        C:\Users\zrong\wiz2joplin_output
  --wiz-dir, -w WIZNOTE_DIR
                        设置 WizNote 的数据目录。例如 ~/.wiznote 或
                        C:\Program Files\WizNote
  --wiz-user, -u WIZNOTE_USER_ID
                        设置您的 WizNote 用户 ID（登录邮箱）。
  --target {joplin,obsidian}
                        目标平台：joplin 或 obsidian（默认：joplin）
  --joplin-token, -t JOPLIN_TOKEN
                        设置访问 Joplin Web Clipper 服务的授权令牌。
                        当 --target=joplin 时必需
  --joplin-host, -n JOPLIN_HOST
                        设置您的 Joplin Web Clipper 服务的主机地址，
                        默认为 127.0.0.1
  --joplin-port, -p JOPLIN_PORT
                        设置您的 Joplin Web Clipper 服务的端口，
                        默认为 41184
  --obsidian-vault OBSIDIAN_VAULT
                        设置 Obsidian Vault 路径。当 --target=obsidian 时必需
  --location, -l LOCATION
                        转换 WizNote 的位置，例如 /My Notes/。如果使用
                        --all 参数，则跳过 --location 参数。
  --location-children, -r
                        与 --location 参数一起使用，转换 --location 的所有子位置。
  --all, -a             转换 WizNote 的所有文档。
```

## 日志文件

请查看 --output 目录下的 `w2j.log` 日志文件以检查转换状态。

## 源码分析相关文章

- [从 WizNote 为知笔记到 Joplin（上）](https://blog.zengrong.net/post/wiznote2joplin1/)
- [从 WizNote 为知笔记到 Joplin（下）](https://blog.zengrong.net/post/wiznote2joplin2/)
- [WizNote 为知笔记 macOS 本地文件夹分析](https://blog.zengrong.net/post/analysis-of-wiznote/)
- [使用腾讯云对象存储(COS)实现Joplin同步](https://blog.zengrong.net/post/joplin-sync-use-cos/)
- [配置 Joplin Server 实现同步](https://blog.zengrong.net/post/joplin-server-config/)

## 贡献者

- [zrong](https://github.com/zrong) - 原始项目作者，实现了从 WizNote 到 Joplin 的迁移功能
- [hooligan520](https://github.com/hooligan520) - 添加了 Obsidian 迁移支持和断点续传功能

**本项目从 [zrong/wiz2joplin](https://github.com/zrong/wiz2joplin) fork 而来，在原有基础上增加了对 Obsidian 的支持。**
