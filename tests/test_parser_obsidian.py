from pathlib import Path
import pytest

from w2j.parser import convert_obsidian_body
from w2j.wiz import WizInternalLink, WizAttachment, WizImage


@pytest.fixture
def sample_attachments(tmp_path):
    """ 示例附件列表
    """
    attachments_dir = tmp_path / 'attachments'
    attachments_dir.mkdir()
    # 创建模拟附件文件
    (attachments_dir / '{att-guid-1}test.pdf').touch()
    (attachments_dir / '{att-guid-2}document.docx').touch()
    
    return [
        WizAttachment('att-guid-1', 'doc-guid', 'test.pdf', '2024-01-01 10:00:00', attachments_dir, check_file=False),
        WizAttachment('att-guid-2', 'doc-guid', 'document.docx', '2024-01-01 10:00:00', attachments_dir, check_file=False),
    ]


@pytest.fixture
def sample_images(tmp_path):
    """ 示例图片列表
    """
    note_extract_dir = tmp_path / 'note_extract'
    index_files_dir = note_extract_dir / 'index_files'
    index_files_dir.mkdir(parents=True)
    # 创建模拟图片文件
    (index_files_dir / 'image1.jpg').touch()
    (index_files_dir / 'image2.png').touch()
    
    return [
        WizImage('<img src="index_files/image1.jpg">', 'index_files/image1.jpg', note_extract_dir),
        WizImage('<img src="index_files/image2.png">', 'index_files/image2.png', note_extract_dir),
    ]


def test_convert_document_link():
    """ 测试文档链接转换
    """
    body = '这是一个<a href="wiz://open_document?guid=123&amp;kbguid=&amp;private_kbguid=456">目标笔记</a>链接。'
    internal_links = [
        WizInternalLink(
            '<a href="wiz://open_document?guid=123&amp;kbguid=&amp;private_kbguid=456">目标笔记</a>',
            '123',
            '目标笔记',
            'open_document'
        )
    ]
    
    result = convert_obsidian_body(body, False, internal_links, [], [], 'test')
    assert '[[目标笔记]]' in result


def test_convert_attachment_link(sample_attachments):
    """ 测试附件链接转换
    """
    body = '这是一个<a href="wiz://open_attachment?guid=att-guid-1">附件</a>链接。'
    internal_links = [
        WizInternalLink(
            '<a href="wiz://open_attachment?guid=att-guid-1">附件</a>',
            'att-guid-1',
            '附件',
            'open_attachment'
        )
    ]
    
    result = convert_obsidian_body(body, False, internal_links, sample_attachments, [], 'test')
    assert '![[test.pdf]]' in result


def test_convert_image_link(sample_images):
    """ 测试图片链接转换
    """
    body = '这是一张图片：<img src="index_files/image1.jpg">'
    
    result = convert_obsidian_body(body, False, [], [], sample_images, 'test')
    assert '![[image1.jpg]]' in result


def test_preserve_external_links():
    """ 测试保持外部链接不变
    """
    body = '这是一个外部链接：<a href="https://example.com">示例</a>'
    
    result = convert_obsidian_body(body, False, [], [], [], 'test')
    # 外部链接应该保持为 Markdown 格式
    assert 'example.com' in result.lower() or '示例' in result


def test_all_notes_conversion():
    """ 测试所有笔记都进行 HTML 到 Markdown 转换
    """
    # 为知笔记中所有内容都是 HTML 格式存储，无论标题是否以 .md 结尾
    body = '<h1>标题</h1><p>这是 <strong>内容</strong>。</p>'
    
    # 测试标题以 .md 结尾的笔记
    result1 = convert_obsidian_body(body, True, [], [], [], 'test')
    # HTML 应该被转换为 Markdown 格式
    assert '标题' in result1
    assert '内容' in result1
    # HTML 标签应该被移除
    assert '<h1>' not in result1
    assert '<p>' not in result1
    
    # 测试标题不以 .md 结尾的笔记（现在也会转换）
    result2 = convert_obsidian_body(body, False, [], [], [], 'test')
    # HTML 也应该被转换为 Markdown 格式
    assert '标题' in result2
    assert '内容' in result2
    # HTML 标签应该被移除
    assert '<h1>' not in result2
    assert '<p>' not in result2


def test_multiple_links_conversion(sample_attachments):
    """ 测试多个链接转换
    """
    body = '链接1：<a href="wiz://open_document?guid=doc1&amp;kbguid=&amp;private_kbguid=kb1">文档1</a>，链接2：<a href="wiz://open_attachment?guid=att-guid-1">附件</a>'
    internal_links = [
        WizInternalLink(
            '<a href="wiz://open_document?guid=doc1&amp;kbguid=&amp;private_kbguid=kb1">文档1</a>',
            'doc1',
            '文档1',
            'open_document'
        ),
        WizInternalLink(
            '<a href="wiz://open_attachment?guid=att-guid-1">附件</a>',
            'att-guid-1',
            '附件',
            'open_attachment'
        )
    ]
    
    result = convert_obsidian_body(body, False, internal_links, sample_attachments, [], 'test')
    assert '[[文档1]]' in result
    assert '![[test.pdf]]' in result
