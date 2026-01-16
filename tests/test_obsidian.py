from pathlib import Path
import tempfile
import shutil
import pytest

from w2j.obsidian import ObsidianStorage, ObsidianConvertUtil
from w2j.wiz import WizDocument, WizTag, WizAttachment, WizImage


@pytest.fixture
def temp_vault():
    """ 创建临时 Obsidian Vault
    """
    temp_dir = tempfile.mkdtemp()
    vault_path = Path(temp_dir) / 'test_vault'
    vault_path.mkdir()
    yield vault_path
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_work_dir():
    """ 创建临时工作目录
    """
    temp_dir = tempfile.mkdtemp()
    work_dir = Path(temp_dir)
    yield work_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def obsidian_storage(temp_vault, temp_work_dir):
    """ 创建 ObsidianStorage 实例
    """
    return ObsidianStorage(temp_vault, temp_work_dir)


@pytest.fixture
def sample_document():
    """ 创建示例文档
    """
    doc = WizDocument(
        guid='test-guid-123',
        title='测试笔记',
        location='/My Notes/',
        url='',
        created='2024-01-01 10:00:00',
        modified='2024-01-02 10:00:00',
        attachment_count=0,
        notes_dir=Path('/tmp'),
        documents_dir=Path('/tmp'),
        check_file=False
    )
    doc.body = '# 测试内容\n\n这是一篇测试笔记。'
    doc.is_markdown = True
    doc.tags = []
    doc.attachments = []
    doc.images = []
    doc.internal_links = []
    return doc


def test_obsidian_storage_init(obsidian_storage, temp_vault):
    """ 测试 ObsidianStorage 初始化
    """
    assert obsidian_storage.vault_path == temp_vault
    assert obsidian_storage.vault_path.exists()


def test_sanitize_filename(obsidian_storage):
    """ 测试文件名清理
    """
    assert obsidian_storage._sanitize_filename('test<file>.md') == 'test_file_.md'
    assert obsidian_storage._sanitize_filename('test:file.md') == 'test_file.md'
    assert obsidian_storage._sanitize_filename('  test.md  ') == 'test.md'


def test_get_note_file_path(obsidian_storage, sample_document):
    """ 测试获取笔记文件路径
    """
    file_path = obsidian_storage._get_note_file_path(sample_document)
    assert file_path.name == '测试笔记.md'
    assert file_path.parent.name == 'My Notes'
    assert file_path.parent.parent == obsidian_storage.vault_path


def test_get_attachments_dir(obsidian_storage, sample_document):
    """ 测试获取附件文件夹路径
    """
    attachments_dir = obsidian_storage._get_attachments_dir(sample_document)
    assert attachments_dir.name == '测试笔记.md_Attachments'
    assert attachments_dir.parent.name == 'My Notes'


def test_generate_front_matter(obsidian_storage, sample_document):
    """ 测试生成 Front Matter
    """
    front_matter = obsidian_storage._generate_front_matter(sample_document)
    assert '---' in front_matter
    assert 'created:' in front_matter
    assert 'modified:' in front_matter


def test_generate_front_matter_with_tags(obsidian_storage, sample_document):
    """ 测试生成带标签的 Front Matter
    """
    sample_document.tags = [
        WizTag('tag1', '标签1', '2024-01-01 10:00:00'),
        WizTag('tag2', '标签2', '2024-01-01 10:00:00')
    ]
    front_matter = obsidian_storage._generate_front_matter(sample_document)
    assert 'tags:' in front_matter
    assert '标签1' in front_matter
    assert '标签2' in front_matter


def test_generate_tags_in_body(obsidian_storage, sample_document):
    """ 测试生成正文中的标签
    """
    sample_document.tags = [
        WizTag('tag1', '标签1', '2024-01-01 10:00:00'),
        WizTag('tag2', '标签2', '2024-01-01 10:00:00')
    ]
    tags_str = obsidian_storage._generate_tags_in_body(sample_document)
    assert '#标签1' in tags_str
    assert '#标签2' in tags_str


def test_convert_util_init(temp_work_dir):
    """ 测试 ObsidianConvertUtil 初始化
    """
    db_file = temp_work_dir / 'w2o.sqlite'
    cu = ObsidianConvertUtil(db_file)
    assert cu.db_file == db_file
    assert db_file.exists()
    cu.close()


def test_convert_util_is_note_migrated(temp_work_dir, sample_document):
    """ 测试检查笔记是否已迁移
    """
    db_file = temp_work_dir / 'w2o.sqlite'
    cu = ObsidianConvertUtil(db_file)
    
    assert not cu.is_note_migrated(sample_document.guid)
    
    # 添加笔记记录
    note_file = temp_work_dir / 'test.md'
    cu.add_note(sample_document, note_file)
    
    assert cu.is_note_migrated(sample_document.guid)
    cu.close()


@pytest.mark.skip
def test_sync_note(obsidian_storage, sample_document, temp_vault):
    """ 测试同步笔记（需要实际的 WizNote 数据）
    """
    obsidian_storage.sync_note(sample_document)
    
    # 检查文件是否创建
    note_file = temp_vault / 'My Notes' / '测试笔记.md'
    assert note_file.exists()
    
    # 检查文件内容
    content = note_file.read_text(encoding='utf-8')
    assert '---' in content
    assert '测试内容' in content
    
    obsidian_storage.close()


def test_markdown_note_title_handling(obsidian_storage):
    """ 测试 Markdown 笔记的 title 处理
    """
    # Markdown 笔记的 title 已经去掉了 .md 后缀
    doc = WizDocument(
        guid='test-guid',
        title='测试笔记',  # 已经去掉了 .md
        location='/',
        url='',
        created='2024-01-01 10:00:00',
        modified='2024-01-01 10:00:00',
        attachment_count=0,
        notes_dir=Path('/tmp'),
        documents_dir=Path('/tmp'),
        check_file=False
    )
    doc.is_markdown = True
    
    file_path = obsidian_storage._get_note_file_path(doc)
    assert file_path.name == '测试笔记.md'


def test_non_markdown_note_title_handling(obsidian_storage):
    """ 测试非 Markdown 笔记的 title 处理
    """
    # 非 Markdown 笔记的 title 不带 .md 后缀
    doc = WizDocument(
        guid='test-guid',
        title='测试笔记',  # 不带 .md
        location='/',
        url='',
        created='2024-01-01 10:00:00',
        modified='2024-01-01 10:00:00',
        attachment_count=0,
        notes_dir=Path('/tmp'),
        documents_dir=Path('/tmp'),
        check_file=False
    )
    doc.is_markdown = False
    
    file_path = obsidian_storage._get_note_file_path(doc)
    assert file_path.name == '测试笔记.md'  # 统一添加 .md
