"""HTML to Markdown converter for flomo content.

Handles flomo's rich text format including:
- Bold (<strong>, <b>)
- Italic (<em>, <i>)
- Highlight/Background color (<mark>, <span style="background-color">)
- Underline (<u>, <span style="text-decoration: underline">)
- Unordered lists (<ul><li>)
- Ordered lists (<ol><li>)
- Images (<img>)
- Links (<a href>)
- Bidirectional links (@ mentions, converted to [[link]] format)
- Line breaks (<br>, <p>)
"""

import re
from typing import Optional, Tuple
from html.parser import HTMLParser


class HTMLToMarkdownConverter(HTMLParser):
    """Convert flomo HTML content to Markdown format."""

    def __init__(self, preserve_images: bool = True, image_dir: Optional[str] = None,
                 convert_bilinks_to_wikilinks: bool = False):
        """Initialize the converter.

        Args:
            preserve_images: Whether to include image references in output
            image_dir: Directory for downloaded images (for future use)
            convert_bilinks_to_wikilinks: Convert flomo @ bidirectional links to [[wikilink]] format
        """
        super().__init__()
        self.result = []
        self.list_stack = []  # Stack of list types: 'ul' or 'ol'
        self.list_counters = []  # Counter for ordered lists
        self.preserve_images = preserve_images
        self.image_dir = image_dir
        self.in_pre = False
        self.in_code = False
        self.convert_bilinks_to_wikilinks = convert_bilinks_to_wikilinks
        self._current_link_is_bilink = False  # Track if current link is a bidirectional link

    def handle_starttag(self, tag: str, attrs: list) -> None:
        """Handle opening tags."""
        attrs_dict = dict(attrs)

        if tag == 'p':
            # Paragraph - add newline before (if not at start)
            if self.result:
                self.result.append('\n')
        elif tag == 'br':
            self.result.append('\n')
        elif tag in ('strong', 'b'):
            self.result.append('**')
        elif tag in ('em', 'i'):
            self.result.append('*')
        elif tag == 'mark':
            # Highlight - use ==text== syntax (Obsidian compatible)
            self.result.append('==')
        elif tag == 'u':
            # Underline - use HTML underline tag (Markdown doesn't have native support)
            self.result.append('<u>')
        elif tag == 's' or tag == 'del':
            # Strikethrough
            self.result.append('~~')
        elif tag == 'code':
            self.in_code = True
            self.result.append('`')
        elif tag == 'pre':
            self.in_pre = True
            self.result.append('\n```\n')
        elif tag == 'span':
            # Check for inline styles
            style = attrs_dict.get('style', '')
            if 'background-color' in style or 'background' in style:
                # Highlight with background color - treat as highlight
                self.result.append('==')
            elif 'text-decoration: underline' in style:
                self.result.append('<u>')
            elif 'font-weight: bold' in style or 'font-weight:bold' in style:
                self.result.append('**')
            elif 'font-style: italic' in style or 'font-style:italic' in style:
                self.result.append('*')
        elif tag == 'a':
            # Link - check if it's a bidirectional link (@ mention)
            href = attrs_dict.get('href', '')
            self._current_link_is_bilink = False

            if href:
                # Check if this is a flomo bidirectional link
                # Patterns: flomo://memo/SLUG, @ mention links, or internal memo references
                is_bilink = self._is_bidirectional_link(href, attrs_dict)

                if is_bilink and self.convert_bilinks_to_wikilinks:
                    # Convert to Obsidian wikilink format
                    self._current_link_is_bilink = True
                    self.result.append('[[')
                    self._current_link_href = href
                    # Note: We'll capture the link text in handle_data
                    # and close with ]] in handle_endtag
                else:
                    # Regular link
                    self.result.append('[')
                    self._current_link_href = href
            else:
                self._current_link_href = None
        elif tag == 'img':
            # Image
            if self.preserve_images:
                src = attrs_dict.get('src', '')
                alt = attrs_dict.get('alt', 'image')
                if src:
                    self.result.append(f'![{alt}]({src})')
        elif tag == 'ul':
            self.list_stack.append('ul')
            self.result.append('\n')
        elif tag == 'ol':
            self.list_stack.append('ol')
            self.list_counters.append(1)
            self.result.append('\n')
        elif tag == 'li':
            if self.list_stack:
                list_type = self.list_stack[-1]
                indent = '  ' * (len(self.list_stack) - 1)
                if list_type == 'ul':
                    self.result.append(f'{indent}- ')
                else:
                    counter = self.list_counters[-1]
                    self.result.append(f'{indent}{counter}. ')
                    self.list_counters[-1] = counter + 1
        elif tag == 'blockquote':
            self.result.append('\n> ')
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            level = int(tag[1])
            self.result.append('\n' + '#' * level + ' ')

    def handle_endtag(self, tag: str) -> None:
        """Handle closing tags."""
        if tag == 'p':
            self.result.append('\n')
        elif tag in ('strong', 'b'):
            self.result.append('**')
        elif tag in ('em', 'i'):
            self.result.append('*')
        elif tag == 'mark':
            self.result.append('==')
        elif tag == 'u':
            self.result.append('</u>')
        elif tag == 's' or tag == 'del':
            self.result.append('~~')
        elif tag == 'code':
            self.in_code = False
            self.result.append('`')
        elif tag == 'pre':
            self.in_pre = False
            self.result.append('\n```\n')
        elif tag == 'span':
            # Span doesn't need closing in our simple handling
            pass
        elif tag == 'a':
            if hasattr(self, '_current_link_href') and self._current_link_href:
                if self._current_link_is_bilink:
                    # Bidirectional link - use wikilink format
                    # Extract link text and use it as the note name
                    self.result.append(']]')
                else:
                    # Regular link
                    self.result.append(f']({self._current_link_href})')
                self._current_link_href = None
                self._current_link_is_bilink = False
        elif tag == 'ul':
            if self.list_stack:
                self.list_stack.pop()
        elif tag == 'ol':
            if self.list_stack:
                self.list_stack.pop()
            if self.list_counters:
                self.list_counters.pop()
        elif tag == 'li':
            self.result.append('\n')
        elif tag == 'blockquote':
            self.result.append('\n')
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.result.append('\n')

    def handle_data(self, data: str) -> None:
        """Handle text content."""
        # If we're inside a bidirectional link, strip @ prefix from the text
        # to avoid double-conversion later
        if hasattr(self, '_current_link_is_bilink') and self._current_link_is_bilink:
            # Strip @ prefix if present (flomo uses @ to denote bidirectional links)
            if data.startswith('@'):
                data = data[1:]
        self.result.append(data)

    def _is_bidirectional_link(self, href: str, attrs_dict: dict) -> bool:
        """Check if a link is a flomo bidirectional link (@ mention).

        flomo bidirectional links can appear as:
        - flomo://memo/SLUG (internal protocol)
        - Links with data-memo-slug or similar attributes
        - @ prefix in the link text
        - Links to other memos within flomo

        Args:
            href: The link href
            attrs_dict: Dictionary of HTML attributes

        Returns:
            True if this appears to be a bidirectional link
        """
        # Check for flomo internal protocol
        if href.startswith('flomo://'):
            return True

        # Check for data attributes that indicate memo references
        for attr in ['data-memo-slug', 'data-memo-id', 'data-bilink', 'data-reference']:
            if attr in attrs_dict:
                return True

        # Check for common internal memo link patterns
        # flomo may use relative links or special paths for memo references
        if '/memo/' in href or 'memo_slug=' in href:
            return True

        return False

    def get_markdown(self) -> str:
        """Get the converted Markdown string."""
        return ''.join(self.result)


def html_to_markdown(html_content: str, preserve_images: bool = True,
                      convert_bilinks_to_wikilinks: bool = False) -> str:
    """Convert flomo HTML content to Markdown.

    Args:
        html_content: HTML content from flomo
        preserve_images: Whether to include image references
        convert_bilinks_to_wikilinks: Convert @ bidirectional links to [[wikilink]] format

    Returns:
        Markdown formatted string
    """
    if not html_content:
        return ''

    converter = HTMLToMarkdownConverter(
        preserve_images=preserve_images,
        convert_bilinks_to_wikilinks=convert_bilinks_to_wikilinks
    )
    try:
        converter.feed(html_content)
        return converter.get_markdown().strip()
    except Exception:
        # Fallback: strip all tags if parsing fails
        return re.sub(r'<[^>]+>', '', html_content).strip()


def html_to_plain_text(html_content: str) -> str:
    """Convert HTML to plain text (strip all formatting).

    Args:
        html_content: HTML content from flomo

    Returns:
        Plain text string
    """
    if not html_content:
        return ''

    # Replace common block elements with newlines
    text = html_content
    for tag in ['<br>', '<br/>', '<br />', '</p>', '</div>', '</li>']:
        text = text.replace(tag, '\n')

    # Strip all remaining tags
    text = re.sub(r'<[^>]+>', '', text)

    # Clean up whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r' +', ' ', text)

    return text.strip()


def extract_images_from_html(html_content: str) -> list:
    """Extract image URLs from HTML content.

    Args:
        html_content: HTML content from flomo

    Returns:
        List of image URLs
    """
    if not html_content:
        return []

    # Find all img tags
    img_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
    matches = re.findall(img_pattern, html_content, re.IGNORECASE)
    return matches


def extract_links_from_html(html_content: str) -> list:
    """Extract links from HTML content.

    Args:
        html_content: HTML content from flomo

    Returns:
        List of (text, href) tuples
    """
    if not html_content:
        return []

    # Find all a tags
    link_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>'
    matches = re.findall(link_pattern, html_content, re.IGNORECASE)
    return matches


def extract_bilinks_from_html(html_content: str) -> list:
    """Extract bidirectional links (@ mentions) from HTML content.

    flomo bidirectional links appear as:
    - <a href="flomo://memo/SLUG">@reference</a>
    - Links with data-memo-slug attribute
    - @ prefixed text in links

    Args:
        html_content: HTML content from flomo

    Returns:
        List of (text, href, slug) tuples for bidirectional links
    """
    if not html_content:
        return []

    bilinks = []

    # Pattern 1: flomo:// protocol links
    flomo_pattern = r'<a[^>]+href=["\']flomo://memo/([^"\']+)["\'][^>]*>([^<]*)</a>'
    for match in re.finditer(flomo_pattern, html_content, re.IGNORECASE):
        slug = match.group(1)
        text = match.group(2)
        bilinks.append((text, f'flomo://memo/{slug}', slug))

    # Pattern 2: Links with data-memo-slug attribute
    data_attr_pattern = r'<a[^>]+data-memo-slug=["\']([^"\']+)["\'][^>]*>([^<]*)</a>'
    for match in re.finditer(data_attr_pattern, html_content, re.IGNORECASE):
        slug = match.group(1)
        text = match.group(2)
        bilinks.append((text, f'memo:{slug}', slug))

    # Pattern 3: @ prefixed text in links (common pattern for mentions)
    at_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>@([^<]+)</a>'
    for match in re.finditer(at_pattern, html_content, re.IGNORECASE):
        href = match.group(1)
        text = match.group(2)
        bilinks.append((f'@{text}', href, text))

    return bilinks


def convert_at_mentions_to_wikilinks(text: str) -> str:
    """Convert @ mentions in plain text to Obsidian [[wikilink]] format.

    This handles the case where @ mentions appear as plain text without HTML links.

    Args:
        text: Text that may contain @ mentions

    Returns:
        Text with @ mentions converted to [[wikilink]] format
    """
    if not text:
        return text

    # Pattern: @ followed by word characters, Chinese characters, or slug-like strings
    # Handles: @note-name, @笔记名称, @NoteTitle
    pattern = r'@([\w\u4e00-\u9fff\-_]+(?:/[\w\u4e00-\u9fff\-_]+)*)'

    def replace_mention(match):
        mention = match.group(1)
        return f'[[{mention}]]'

    return re.sub(pattern, replace_mention, text)
