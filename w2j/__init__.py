##############################
# w2j =  Wiznote to Joplin
#
# https://github.com/zrong/wiz2joplin
##############################

import logging
import os
import sys
from pathlib import Path
import argparse

__autho__ = 'zrong'
__version__ = '0.4'

work_dir = Path.cwd()
logger = logging.Logger('w2j')
log_file = work_dir.joinpath('w2j.log')
log_handler = logging.FileHandler(log_file)
log_handler.setFormatter(logging.Formatter('{asctime} - {funcName} - {message}', style='{'))
# logger.addHandler(logging.StreamHandler(sys.stderr))
logger.addHandler(log_handler)


# 只在非测试模式下解析参数
if os.environ.get('W2J_TEST_MODE') != '1':
    # 自定义 HelpFormatter 以支持中文
    class ChineseHelpFormatter(argparse.RawDescriptionHelpFormatter):
        def add_usage(self, usage, actions, groups, prefix=None):
            if prefix is None:
                prefix = '用法: '
            return super().add_usage(usage, actions, groups, prefix)
    
    parser = argparse.ArgumentParser('w2j', description='从 WizNote 迁移到 Joplin 或 Obsidian。', formatter_class=ChineseHelpFormatter, add_help=False)
    parser._optionals.title = '可选参数'
    parser.add_argument('-h', '--help', action='help', help='显示帮助信息并退出')
    parser.add_argument('--output', '-o', type=str, metavar='OUTPUT', required=True, help='解压 WizNote 文件和日志文件的输出目录。例如 ~/wiz2joplin_output 或 C:\\Users\\zrong\\wiz2joplin_output')
    parser.add_argument('--wiz-dir', '-w', type=str, metavar='WIZNOTE_DIR', required=True, help='设置 WizNote 的数据目录。例如 ~/.wiznote 或 C:\\Program Files\\WizNote')
    parser.add_argument('--wiz-user', '-u', type=str, metavar='WIZNOTE_USER_ID', required=True, help='设置您的 WizNote 用户 ID（登录邮箱）。')
    parser.add_argument('--target', type=str, choices=['joplin', 'obsidian'], default='joplin', help='目标平台：joplin 或 obsidian（默认：joplin）')
    parser.add_argument('--joplin-token', '-t', type=str, metavar='JOPLIN_TOKEN', help='设置访问 Joplin Web Clipper 服务的授权令牌。当 --target=joplin 时必需')
    parser.add_argument('--joplin-host', '-n', type=str, metavar='JOPLIN_HOST', default='127.0.0.1', help='设置您的 Joplin Web Clipper 服务的主机地址，默认为 127.0.0.1')
    parser.add_argument('--joplin-port', '-p', type=int, metavar='JOPLIN_PORT', default=41184, help='设置您的 Joplin Web Clipper 服务的端口，默认为 41184')
    parser.add_argument('--obsidian-vault', type=str, metavar='OBSIDIAN_VAULT', help='设置 Obsidian Vault 路径。当 --target=obsidian 时必需')
    parser.add_argument('--enable-resume', action='store_true', help='启用断点续传功能。启用后，已迁移的笔记将被跳过，避免重复处理。默认关闭。')
    parser.add_argument('--location', '-l', type=str, metavar='LOCATION', help='转换 WizNote 的位置，例如 /My Notes/。如果使用 --all 参数，则跳过 --location 参数。')
    parser.add_argument('--location-children', '-r', action='store_true', help='与 --location 参数一起使用，转换 --location 的所有子位置。')
    parser.add_argument('--all', '-a', action='store_true', help='转换 WizNote 的所有文档。')
    args = parser.parse_args()
else:
    args = None


from . import wiz
from . import joplin
from . import adapter

__all__ = ['wiz', 'joplin', 'adapter']


def main() -> None:
    if args is None:
        print('此模块正在测试模式下导入。')
        return
    if args.location is None and args.all == False:
        print('请设置 --location 参数指定 WizNote 的位置，或使用 --all 参数转换所有文档！')
        return
    wiznote_dir = Path(args.wiz_dir).expanduser()
    if not wiznote_dir.exists():
        print(f'WizNote 目录 {wiznote_dir} 不存在！')
        return
    output_dir = Path(args.output).expanduser()
    if not output_dir.exists():
        output_dir.mkdir()
    logger.removeHandler(log_file)
    newlog_file = output_dir.joinpath('w2j.log')
    print(f'请查看 [{newlog_file.resolve()}] 以检查转换状态。')
    logger.addHandler(logging.FileHandler(newlog_file))

    ws = wiz.WizStorage(args.wiz_user, wiznote_dir, is_group_storage=False, work_dir=output_dir)

    if args.target == 'obsidian':
        # Obsidian 迁移
        if not args.obsidian_vault:
            print('错误：当 --target=obsidian 时，必须提供 --obsidian-vault 参数')
            return
        vault_path = Path(args.obsidian_vault).expanduser()
        ad = adapter.ObsidianAdapter(ws, vault_path, work_dir=output_dir, enable_resume=args.enable_resume)
        try:
            if args.all:
                ad.sync_all()
            else:
                ad.sync_note_by_location(args.location, args.location_children)
        finally:
            ad.close()
    else:
        # Joplin 迁移（默认）
        if not args.joplin_token:
            print('错误：当 --target=joplin 时，必须提供 --joplin-token 参数')
            return
        jda = joplin.JoplinDataAPI(
            host=args.joplin_host,
            port=args.joplin_port,
            token=args.joplin_token
        )
        ad = adapter.JoplinAdapter(ws, jda, work_dir=output_dir)
        if args.all:
            ad.sync_all()
        else:
            ad.sync_note_by_location(args.location, args.location_children)
