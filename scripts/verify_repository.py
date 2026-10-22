"""Check public documentation links and shared design-token readability (stdlib only)."""
from pathlib import Path
import json
import re
import sys
import unicodedata
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def luminance(color):
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in channels]
    return sum(a * b for a, b in zip(linear, (.2126, .7152, .0722)))


def anchors(text):
    found = set(re.findall(r'<a\s+(?:id|name)=["\']([^"\']+)', text))
    counts = {}
    for heading in re.findall(r'^#{1,6}\s+(.+)$', text, re.M):
        slug = ''.join(c for c in heading.lower().strip() if c in '-_ ' or unicodedata.category(c)[0] in 'LN')
        slug = slug.replace(' ', '-')
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        found.add(slug + (f'-{count}' if count else ''))
    return found


def main():
    errors = []
    token_file = ROOT / 'tokens/design-tokens.json'
    tokens = json.loads(token_file.read_text(encoding='utf-8-sig'))
    palettes = tokens['themes']
    if set(palettes['light']) != set(palettes['dark']):
        errors.append('Light/dark semantic roles differ')
    required = {'background', 'surface', 'foreground', 'muted', 'border', 'accent',
                'accent_active', 'selected_background', 'selected_foreground',
                'input_background', 'hover', 'disabled', 'success', 'warning', 'error', 'focus'}
    for mode, colors in palettes.items():
        if set(colors) != required:
            errors.append(f'{mode}: missing/unexpected color roles')
        for key, value in colors.items():
            if not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
                errors.append(f'{mode}.{key}: invalid RGB color')
        pairs = [('foreground', 'surface'), ('foreground', 'background'), ('muted', 'surface'),
                 ('selected_foreground', 'selected_background'), ('success', 'surface'),
                 ('warning', 'surface'), ('error', 'surface')]
        for foreground, background in pairs:
            a, b = sorted((luminance(colors[foreground]), luminance(colors[background])))
            ratio = (b + .05) / (a + .05)
            if ratio < 4.5:
                errors.append(f'{mode}: {foreground}/{background} contrast {ratio:.2f} < 4.5')
    for role in ('body', 'small', 'heading'):
        for unit in ('tk_points', 'android_sp'):
            if tokens['typography'][role][unit] <= 0:
                errors.append(f'{role}.{unit}: non-positive font size')

    documents = [ROOT / name for name in ('README.md', 'AGENTS.md', 'CHANGELOG.md',
                  'VALIDATION.md', 'THIRD_PARTY_NOTICES.md')]
    for folder in ('docs', 'components', 'examples', 'references', 'tokens', 'apps', 'packaging'):
        documents.extend(path for path in (ROOT / folder).rglob('*.md')
                         if not {'build', '.gradle'}.intersection(path.relative_to(ROOT).parts))
    checked = 0
    for doc in documents:
        text = doc.read_text(encoding='utf-8-sig')
        # Code snippets may contain illustrative Markdown syntax, not real navigation.
        text = re.sub(r'^```[^\n]*\n.*?^```\s*$', '', text, flags=re.M | re.S)
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
            target = target.split(' "', 1)[0].strip('<>')
            url = urlsplit(target)
            if url.scheme or url.netloc:
                continue
            path = (doc.parent / unquote(url.path)).resolve() if url.path else doc
            checked += 1
            if not path.exists():
                errors.append(f'{doc.relative_to(ROOT)}: missing {target}')
            elif url.fragment and path.suffix == '.md':
                if unquote(url.fragment) not in anchors(path.read_text(encoding='utf-8-sig')):
                    errors.append(f'{doc.relative_to(ROOT)}: missing anchor {target}')
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(f'PASS: {len(documents)} Markdown documents, {checked} local links, shared tokens and text contrast.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
