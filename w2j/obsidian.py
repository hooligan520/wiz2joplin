##############################
# w2j.obsidian
#
# 处理 Obsidian 相关
##############################

import sqlite3
import yaml
import re
from pathlib import Path
from typing import Optional
from datetime import datetime

from w2j import logger
from w2j.wiz import WizDocument, WizAttachment, WizImage, WizInternalLink, WizTag, WizStorage
from w2j.parser import convert_obsidian_body


class ObsidianConvertUtil:
    """ 处理 Obsidian 转换的中间过程
    """
    conn: sqlite3.Connection
    db_file: Path

    CREATE_SQL = """
        CREATE TABLE note (
            note_guid TEXT NOT NULL,
            file_path TEXT NOT NULL,
            title TEXT NOT NULL,
            location TEXT NOT NULL,
            created_time INTEGER NOT NULL,
            modified_time INTEGER NOT NULL,
            PRIMARY KEY (note_guid)
        );
        CREATE INDEX idx_file_path ON note (file_path);
    """

    def __init__(self, db_file: Path) -> None:
        self.db_file = db_file
        self.init_db()

    def init_db(self):
        """ 创建数据库
        """
        # 确保数据库文件所在目录存在
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_file)
        test_table = "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?;"
        
        table_exists = self.conn.execute(test_table, ('note', )).fetchone()[0]
        logger.info(f'表 note 是否存在: {table_exists}')
        if not table_exists:
            self.conn.executescript(self.CREATE_SQL)
            self.conn.commit()

    def close(self):
        self.conn.close()

    def is_note_migrated(self, guid: str) -> bool:
        """ 检查笔记是否已迁移
        """
        sql = 'SELECT count(*) FROM note WHERE note_guid=?;'
        count = self.conn.execute(sql, (guid, )).fetchone()[0]
        return count > 0

    def add_note(self, document: WizDocument, file_path: Path) -> None:
        """ 记录已迁移的笔记
        """
        sql = 'INSERT INTO note (note_guid, file_path, title, location, created_time, modified_time) VALUES (?, ?, ?, ?, ?, ?);'
        self.conn.execute(sql, (
            document.guid,
            str(file_path),
            document.title,
            document.location,
            document.created,
            document.modified
        ))
        self.conn.commit()


class ObsidianStorage:
    """ Obsidian 存储实现
    """
    vault_path: Path
    work_dir: Path
    cu: ObsidianConvertUtil
    enable_resume: bool

    def __init__(self, vault_path: Path, work_dir: Path, enable_resume: bool = False) -> None:
        self.vault_path = Path(vault_path).expanduser()
        if not self.vault_path.exists():
            self.vault_path.mkdir(parents=True)
        self.work_dir = work_dir
        self.enable_resume = enable_resume
        self.cu = ObsidianConvertUtil(self.work_dir.joinpath('w2o.sqlite'))

    def close(self):
        self.cu.close()

    def _sanitize_filename(self, filename: str) -> str:
        """ 清理文件名中的非法字符
        """
        # 移除或替换非法字符
        illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in illegal_chars:
            filename = filename.replace(char, '_')
        # 移除前后空格和点
        filename = filename.strip('. ')
        return filename

    def _get_note_file_path(self, document: WizDocument) -> Path:
        """ 获取笔记文件路径
        """
        # 处理 location: /My Notes/ -> My Notes/
        location_path = document.location.strip('/')
        if location_path:
            folder_path = self.vault_path / location_path
        else:
            folder_path = self.vault_path

        # 确保文件夹存在
        folder_path.mkdir(parents=True, exist_ok=True)

        # 文件名统一使用 {title}.md
        safe_title = self._sanitize_filename(document.title)
        file_path = folder_path / f'{safe_title}.md'
        return file_path

    def _get_attachments_dir(self, document: WizDocument) -> Path:
        """ 获取附件文件夹路径
        """
        note_file = self._get_note_file_path(document)
        # 附件文件夹：{title}.md_Attachments/
        attachments_dir = note_file.parent / f'{note_file.stem}.md_Attachments'
        return attachments_dir

    def _generate_front_matter(self, document: WizDocument) -> str:
        """ 生成 YAML Front Matter
        """
        front_matter = {
            'created': datetime.fromtimestamp(document.created / 1000).strftime('%Y-%m-%d %H:%M:%S'),
            'modified': datetime.fromtimestamp(document.modified / 1000).strftime('%Y-%m-%d %H:%M:%S'),
        }

        if document.url:
            front_matter['source_url'] = document.url

        if document.tags:
            front_matter['tags'] = [tag.name for tag in document.tags]

        return '---\n' + yaml.dump(front_matter, allow_unicode=True, default_flow_style=False) + '---\n\n'

    def _generate_tags_in_body(self, document: WizDocument) -> str:
        """ 在正文末尾生成标签
        """
        if not document.tags:
            return ''
        tags_str = ' '.join([f'#{tag.name}' for tag in document.tags])
        return f'\n\n{tags_str}\n'

    def _copy_attachment(self, attachment: WizAttachment, target_dir: Path) -> None:
        """ 复制附件到目标文件夹
        """
        if not attachment.file.exists():
            logger.warning(f'附件文件不存在: {attachment.file}')
            return

        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / attachment.name
        if target_file.exists():
            logger.info(f'附件已存在，跳过: {target_file}')
            return

        import shutil
        shutil.copy2(attachment.file, target_file)
        logger.info(f'复制附件: {attachment.name} -> {target_file}')

    def _copy_image(self, image: WizImage, target_dir: Path) -> None:
        """ 复制图片到目标文件夹
        """
        if not image.file.exists():
            logger.warning(f'图片文件不存在: {image.file}')
            return

        target_dir.mkdir(parents=True, exist_ok=True)
        # 获取图片文件名
        image_name = Path(image.src).name
        target_file = target_dir / image_name
        if target_file.exists():
            logger.info(f'图片已存在，跳过: {target_file}')
            return

        import shutil
        shutil.copy2(image.file, target_file)
        logger.info(f'复制图片: {image_name} -> {target_file}')

    def sync_note(self, document: WizDocument) -> None:
        """ 同步一篇笔记到 Obsidian
        """
        logger.info(f'正在处理笔记: {document.guid}|{document.document_type}|{document.title}')

        # 检查是否已迁移（仅在启用断点续传时）
        if self.enable_resume and self.cu.is_note_migrated(document.guid):
            logger.warning(f'笔记 {document.guid} |{document.title}| 已经迁移，跳过。')
            return

        # 获取文件路径
        note_file = self._get_note_file_path(document)
        attachments_dir = self._get_attachments_dir(document)

        # 复制附件
        for attachment in document.attachments:
            self._copy_attachment(attachment, attachments_dir)

        # 复制图片
        for image in document.images:
            self._copy_image(image, attachments_dir)

        # 转换内容
        body = convert_obsidian_body(
            document.body,
            document.is_markdown,
            document.internal_links,
            document.attachments,
            document.images,
            document.title
        )

        # 生成 Front Matter
        front_matter = self._generate_front_matter(document)

        # 生成标签（在正文末尾）
        tags_in_body = self._generate_tags_in_body(document)

        # 写入文件
        note_file.write_text(front_matter + body + tags_in_body, encoding='utf-8')

        # 设置文件时间戳
        import os
        created_time = document.created / 1000
        modified_time = document.modified / 1000
        os.utime(note_file, (created_time, modified_time))

        # 记录到数据库（仅在启用断点续传时）
        if self.enable_resume:
            self.cu.add_note(document, note_file)

        logger.info(f'笔记已保存: {note_file}')

    def sync_all(self, documents: list[WizDocument]) -> None:
        """ 同步所有笔记
        """
        logger.info(f'开始迁移 {len(documents)} 篇笔记到 Obsidian。')
        for document in documents:
            try:
                self.sync_note(document)
            except Exception as e:
                logger.error(f'迁移笔记失败 {document.guid}|{document.title}|: {e}')
                continue

    def sync_by_location(self, documents: list[WizDocument], location: str, with_children: bool = True) -> None:
        """ 同步指定 location 的笔记
        """
        locations = [location]
        if with_children:
            # 收集所有子 location
            for doc in documents:
                if doc.location.startswith(location) and doc.location != location:
                    if doc.location not in locations:
                        locations.append(doc.location)

        logger.info(f'处理以下 location： {locations}')
        waiting_for_sync = [doc for doc in documents if doc.location in locations]
        logger.info(f'有 {len(waiting_for_sync)} 篇笔记等待同步。')

        for document in waiting_for_sync:
            try:
                self.sync_note(document)
            except Exception as e:
                logger.error(f'迁移笔记失败 {document.guid}|{document.title}|: {e}')
                continue
