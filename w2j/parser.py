##############################
# w2j.parser
# 解析器，解析 html 源码
##############################

from datetime import datetime, timezone, timedelta
from os import link
from pathlib import Path
import re
import chardet
from html import unescape
from inscriptis import get_text
import html2text
from w2j import logger


RE_A_START = r'<a href="'
RE_A_END = r'">([^<]+)</a>'

# 附件内链
# 早期的链接没有双斜杠
# wiz:open_attachment?guid=8337764c-f89d-4267-bdf2-2e26ff156098
# 后期的链接有双斜杠
# wiz://open_attachment?guid=52935f17-c1bb-45b7-b443-b7ba1b6f854e
RE_OPEN_ATTACHMENT_HREF = r'wiz:/{0,2}(open_\w+)\?guid=([a-z0-9\-]{36})'
RE_OPEN_ATTACHMENT_OUTERHTML = RE_A_START + RE_OPEN_ATTACHMENT_HREF + RE_A_END

# 文档内链，只需要提取 guid 后面的部分即可
# wiz://open_document?guid=c6204f26-f966-4626-ad41-1b5fbdb6829e&amp;kbguid=&amp;private_kbguid=69899a48-dc52-11e0-892c-00237def97cc
RE_OPEN_DOCUMENT_HREF = r'wiz:/{0,2}(open_\w+)\?guid=([a-z0-9\-]{36})&amp;kbguid=&amp;private_kbguid=([a-z0-9\-]{36})'
RE_OPEN_DOCUMENT_OUTERHTML = RE_A_START + RE_OPEN_DOCUMENT_HREF + RE_A_END


# 图像文件在 body 中存在的形式，即使是在 .md 文件中，也依然使用这种形式存在
RE_IMAGE_OUTERHTML = r'<img .*?src="(index_files/[^"]+)"[^>]*>'


class WizInternalLink(object):
    """ 嵌入 html 正文中的为知笔记内部链接，可能是笔记，也可能是附件
    """
    # 原始链接的整个 HTML 内容，包括 <a href="link....">名称</a>
    outerhtml: str = None

    # 链接的 title
    title: str = None

    # 原始链接中的资源 guid，可能是 attachemnt 或者是 document
    guid: str = None

    # 值为 open_attachment 或者 open_document
    link_type: str = 'open_attachment'

    def __init__(self, outerhtml: str, guid: str, title: str, link_type: str) -> None:
        self.outerhtml = outerhtml
        self.guid = guid
        self.title = title
        self.link_type = link_type

    def __repr__(self) -> str:
        return f'<WizInternalLink {self.link_type}, {self.title}, {self.guid}>'


class WizImage(object):
    """ 在为知笔记文章中包含的本地图像

    在为知笔记中，本地图像不属于资源，也没有自己的 guid
    """
    # 原始图像的整个 HTML 内容，包括 <img src="index_files/name.jpg">
    outerhtml: str = None

    # 仅包含图像的 src 部分
    src: str = None

    # 图像文件的 Path 对象，在硬盘上的路径
    file: Path = None

    def __init__(self, outerhtml: str, src: str, note_extract_dir: Path, strict_check: bool = True) -> None:
        self.outerhtml = outerhtml
        self.src = src
        self.file = note_extract_dir.joinpath(src)

        if not self.file.exists():
            if strict_check:
                raise FileNotFoundError(f'找不到文件 {self.file}！')
            else:
                logger.warning(f'图片文件缺失: {self.file}，将跳过此图片。')

    def __repr__(self) -> str:
        return f'<WizImage {self.src}, {self.outerhtml}>'


def parse_wiz_html(note_extract_dir: Path, title: str, strict_check: bool = True) -> tuple[str, list[WizInternalLink], list[WizImage]]:
    """ 在为知笔记文档的 index.html 中搜索内链的附件和文档链接
    :param strict_check: 是否严格检查图片文件存在性，默认 True。设为 False 时，缺失图片只记录警告不中断
    """
    index_html = note_extract_dir.joinpath('index.html')
    if not index_html.is_file:
        raise FileNotFoundError(f'主文档文件不存在！ {index_html} |{title}|')
    html_body_bytes = index_html.read_bytes()
    # 早期版本的 html 文件使用的是 UTF-16 LE(BOM) 编码保存。最新的文件是使用 UTF-8(BOM) 编码保存。要判断编码进行解析
    enc = chardet.detect(html_body_bytes)
    html_body = html_body_bytes.decode(encoding=enc['encoding'])

    # 去掉换行符，早期版本的 html 文件使用了 \r\n 换行符，而且会切断 html 标记。替换掉换行符方便正则
    html_body = html_body.replace('\r\n', '')
    html_body = html_body.replace('\n', '')

    internal_links: list[WizInternalLink] = []

    open_attachments = re.finditer(RE_OPEN_ATTACHMENT_OUTERHTML, html_body, re.IGNORECASE)
    for open_attachement in open_attachments:
        link = WizInternalLink(
            open_attachement.group(0),
            open_attachement.group(2),
            open_attachement.group(3),
            open_attachement.group(1))
        internal_links.append(link)

    open_documents = re.finditer(RE_OPEN_DOCUMENT_OUTERHTML, html_body, re.IGNORECASE)
    for open_document in open_documents:
        link = WizInternalLink(
            open_document.group(0),
            open_document.group(2),
            open_document.group(4),
            open_document.group(1))
        internal_links.append(link)

    images: list[WizImage] = []
    image_match = re.finditer(RE_IMAGE_OUTERHTML, html_body, re.IGNORECASE)
    for image in image_match:
        img = WizImage(image.group(0), image.group(1), note_extract_dir, strict_check=strict_check)
        # 如果 strict_check=False 且文件不存在，WizImage 会记录警告但不抛出异常
        # 此时 img.file 不存在，我们只添加存在的图片
        if img.file.exists():
            images.append(img)
    return html_body, internal_links, images


def tots(dt: str):
    """ 转换本地时间到时间戳，数据库中记录的是东八区本地时间
    """
    return int(datetime.strptime(dt, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone(timedelta(hours=8))).timestamp()*1000)


def towizid(id: str) -> str:
    """ 从 joplin 的 id 格式转为 wiz 的 guid 格式
    """
    one = id[:8]
    two = id[8:12]
    three = id[12:16]
    four = id[16:20]
    five = id[20:]
    return '-'.join([one, two, three, four, five])


def tojoplinid(guid: str) -> str:
    """ 从 wiz 的 guid 格式转为 joplin 的 id 格式
    """
    return ''.join(guid.split('-'))


class JoplinInternalLink(object):
    """ 与 Wiz 内链不同，Joplin 内链包括 附件(链接到 resource)、图像(链接到 resource)、文档（链接到 note)
    """
    note_id: str
    resource_id: str

    # image / open_attachment / open_document
    link_type: str

    # 链接的 title
    title: str = None

    # 链接的整个文本内容，可能是 markdown 格式也可能是html格式，取决于 note_id 是何种格式
    outertext: str

    def __init__(self, note_id: str, resource_id: str, title: str, link_type: int, outertext:str='') -> None:
        self.note_id = note_id
        self.resource_id = resource_id
        self.title = title
        self.link_type = link_type
        self.outertext = outertext

    @property
    def id(self) -> str:
        return f'{self.note_id}-{self.resource_id}'


def gen_ilstr(is_markdown: bool, jil: JoplinInternalLink) -> str:
    """ 返回被替换的内链
    ilstr = internal link str
    """
    if is_markdown:
        body = f'[{jil.title}](:/{jil.resource_id})'
        if jil.link_type == 'image':
            return '!' + body
        return body
    if jil.link_type == 'image':
        return f'<img src=":/{jil.resource_id}" alt="{jil.title}">'
    return f'<a href=":/{jil.resource_id}">{jil.title}</a>'


def gen_end_ilstr(is_markdown: bool, jils: list[JoplinInternalLink]):
    """ 返回 body 底部要加入的内容
    ilstr = internal link str
    """
    if is_markdown:
        return '\n\n# 附件链接\n\n' + '\n'.join([ '- ' + gen_ilstr(is_markdown, jil) for jil in jils])
    body = ''.join([ f'<li>{gen_ilstr(is_markdown, jil)}</li>' for jil in jils])
    return f'<br><br><h1>附件链接</h1><ul>{body}</ul>'
    

def convert_joplin_body(body: str, is_markdown: bool, internal_links: list[JoplinInternalLink]) -> str:
    """ 将为知笔记中的 body 转换成 Joplin 内链
    """
    insert_to_end: list[JoplinInternalLink] = []
    for jil in internal_links:
        # 替换链接
        if jil.outertext:
            body = body.replace(jil.outertext, gen_ilstr(is_markdown, jil))
        # 所有的附件，需要在body 底部加入链接
        if jil.link_type == 'open_attachment':
            insert_to_end.append(jil)
    # 处理 markdown 转换
    if is_markdown:
        body = get_text(body)
    if insert_to_end:
        body += gen_end_ilstr(is_markdown, insert_to_end)
    return body


def convert_obsidian_body(
    body: str,
    is_markdown: bool,
    internal_links: list,
    attachments: list,
    images: list,
    note_title: str
) -> str:
    """ 将为知笔记中的 body 转换成 Obsidian 格式
    """
    # 创建附件和图片的映射（guid -> 文件名）
    attachment_map: dict[str, str] = {att.guid: att.name for att in attachments}
    image_map: dict[str, str] = {img.src: Path(img.src).name for img in images}

    # 处理内部链接
    for wil in internal_links:
        if not wil.outerhtml:
            continue

        if wil.link_type == 'open_document':
            # 文档链接转换为双向链接 [[笔记标题]]
            obsidian_link = f'[[{wil.title}]]'
            body = body.replace(wil.outerhtml, obsidian_link)
        elif wil.link_type == 'open_attachment':
            # 附件链接转换为 ![[附件名]]
            attachment_name = attachment_map.get(wil.guid, wil.title)
            obsidian_link = f'![[{attachment_name}]]'
            body = body.replace(wil.outerhtml, obsidian_link)

    # 处理图片（在 HTML 中的图片标签）
    for image in images:
        if image.outerhtml:
            image_name = Path(image.src).name
            obsidian_link = f'![[{image_name}]]'
            body = body.replace(image.outerhtml, obsidian_link)

    # 根据笔记类型选择不同的 HTML 转 Markdown 方法
    if is_markdown:
        # .md 结尾的笔记：为知笔记把每一行 Markdown 都包裹在 <p> 或 <div> 标签中
        # 直接提取标签内容，避免产生多余空行
        # 移除HTML注释
        body = re.sub(r'<!--.*?-->', '', body, flags=re.DOTALL)

        # 检查是使用 <p> 标签还是 <div> 标签
        p_count = body.count('<p>')
        div_count = body.count('<div')

        # 如果有 <p> 标签，优先使用 <p>；否则使用 <div>
        if p_count > 0:
            pattern = r'<p>(.*?)</p>'
        else:
            pattern = r'<div[^>]*>(.*?)</div>'

        matches = re.findall(pattern, body, flags=re.DOTALL)

        lines = []
        for match in matches:
            # 移除 <br> 和 <br/> 标签
            text = re.sub(r'<br\s*/?>', '', match)
            # 移除其他HTML标签（如 <span>）
            text = re.sub(r'<[^>]+>', '', text)
            # 解码 HTML 实体
            text = unescape(text)
            # 替换不间断空格 (\xa0) 为普通空格
            text = text.replace('\xa0', ' ')
            # 移除行尾空白
            text = text.rstrip()

            # 如果内容为空，说明是原始 Markdown 中的空行（通常是 <p><br></p> 或 <div><br></div>）
            if not text:
                lines.append('')
            else:
                lines.append(text)

        body = '\n'.join(lines)
    else:
        # 非 .md 结尾的笔记：使用 html2text 转换
        h = html2text.HTML2Text()
        h.ignore_links = False  # 保留链接
        h.ignore_images = False  # 保留图片
        h.body_width = 0  # 禁用自动换行
        body = h.handle(body)

        # 修复标题格式：html2text 在处理嵌套标签时会将标题标记和文本分成两行
        # 例如 "# \n\n标题文本" -> "# 标题文本"
        body = re.sub(r'^(#{1,6})\s*\n+', r'\1 ', body, flags=re.MULTILINE)

        # 限制连续换行符为最多2个（即最多一个空行）
        body = re.sub(r'\n{3,}', '\n\n', body)

        # 对于新版编辑器的笔记，移除大部分单行空行（保留有意义的段落分隔）
        # 新版编辑器会为每个文本块（<div>）添加空行，导致过多空行
        lines = body.split('\n')
        result_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            result_lines.append(line)

            # 如果当前行非空，且下一行是空行
            if line.strip() and i + 1 < len(lines) and not lines[i + 1].strip():
                # 检查空行后面是否还有内容
                if i + 2 < len(lines) and lines[i + 2].strip():
                    next_line = lines[i + 2].strip()
                    # 如果下一行不是标题、列表、引用等特殊格式，跳过空行
                    if not (next_line.startswith('#') or
                           next_line.startswith('-') or
                           next_line.startswith('*') or
                           next_line.startswith('>') or
                           next_line.startswith('```') or
                           next_line.startswith('|')):
                        # 跳过这个单空行
                        i += 1
            i += 1

        body = '\n'.join(result_lines)

        # 移除行尾空白
        body = '\n'.join(line.rstrip() for line in body.split('\n'))

    # 处理外部链接：保持原样（不转换 http/https 链接）
    # 外部链接在 Markdown 中已经是标准格式，不需要额外处理

    return body