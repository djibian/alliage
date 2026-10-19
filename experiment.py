#!/usr/bin/env python3
"""Create isolated Quarto proposal variants from a strictly resolved HTML selection."""
from __future__ import annotations
import argparse, difflib, hashlib, html, json, os, re, shutil, subprocess, sys, tempfile
from html.parser import HTMLParser
from pathlib import Path
from resolve_source import LocalizationError, locate, expected_source_from_url, git

class RenderError(Exception):
    pass

class Node:
    def __init__(self, tag, attrs=()):
        self.tag, self.attrs, self.children, self.parts = tag, dict(attrs), [], []
    def all_text(self):
        return ''.join(part.all_text() if isinstance(part, Node) else part for part in self.parts)
    def descendants(self):
        yield self
        for child in self.children:
            yield from child.descendants()

class ParsedHtml(HTMLParser):
    VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node('root')
        self.stack = [self.root]
    def handle_starttag(self, tag, attrs):
        child = Node(tag, attrs)
        self.stack[-1].children.append(child)
        self.stack[-1].parts.append(child)
        if tag not in self.VOID:
            self.stack.append(child)
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)
    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break
    def handle_data(self, data):
        self.stack[-1].parts.append(data)

def parse_html(source: str):
    parser = ParsedHtml()
    parser.feed(source)
    return parser.root

def css_target(root: Node, path: str):
    """Supported CSS subset: #id > tag:nth-of-type(n) > ..."""
    parts = [part.strip() for part in path.split('>')]
    if not parts or not re.fullmatch(r'#[\w\-]+', parts[0]):
        raise RenderError('CSS_PATH_UNSUPPORTED')
    found = [node for node in root.descendants() if node.attrs.get('id') == parts[0][1:]]
    if len(found) != 1:
        raise RenderError('CSS_ID_MISSING_OR_AMBIGUOUS')
    node = found[0]
    for part in parts[1:]:
        match = re.fullmatch(r'([a-z][a-z0-9-]*)(?::nth-of-type\(([1-9][0-9]*)\))?', part)
        if not match:
            raise RenderError('CSS_PATH_UNSUPPORTED: '+part)
        tag, index = match.group(1), int(match.group(2) or 1)
        children = [c for c in node.children if c.tag == tag]
        if index > len(children) or (match.group(2) is None and len(children) != 1):
            raise RenderError('CSS_TARGET_NOT_FOUND_OR_AMBIGUOUS: '+part)
        node = children[index-1]
    return node

def canonical_text(text: str):
    return re.sub(r'\s+', ' ', text).strip()

def text_in_html(html_file: Path, capture: dict):
    dom = parse_html(html_file.read_text(encoding='utf-8'))
    return canonical_text(css_target(dom, capture['dom']['cssPath']).all_text())

def visible_text(html_file: Path):
    dom = parse_html(html_file.read_text(encoding='utf-8'))
    body = [n for n in dom.descendants() if n.tag == 'body']
    if len(body) != 1:
        raise RenderError('HTML_BODY_MISSING')
    def collect(node):
        if node.tag in ('script','style','noscript','svg','template'):
            return ''
        return ''.join(collect(p) if isinstance(p, Node) else p for p in node.parts)
    return canonical_text(collect(body[0]))

def run_quarto(root: Path, relative: str):
    try:
        result = subprocess.run(['quarto','render',relative,'--profile','eleve','--to','html'],
                                cwd=root, text=True, capture_output=True, timeout=180)
    except (FileNotFoundError, subprocess.TimeoutExpired) as err:
        raise RenderError(f'QUARTO_NOT_AVAILABLE: {err}') from err
    if result.returncode:
        raise RenderError('QUARTO_RENDER_FAILED: '+(result.stdout+'\n'+result.stderr)[-3000:])
    html = root/'dist'/'eleve'/Path(relative).with_suffix('.html')
    if not html.is_file():
        raise RenderError('HTML_NOT_FOUND: '+str(html))
    return html

def copy_project_subset(repo: Path, dest: Path, rel: str):
    files = ['_quarto.yml','_quarto-eleve.yml','_quarto-professeur.yml',
             'publication/quarto/tim.css', 'publication/odt/tim-reference.odt',
             'publication/odt/semantic-odt.lua', rel]
    assets = (repo/rel).parent/'assets'
    if assets.is_dir():
        files += [str(path.relative_to(repo)) for path in assets.rglob('*') if path.is_file()]
    for name in files:
        src = repo/name
        if src.is_symlink():
            raise LocalizationError('UNSAFE_SOURCE', 'Symbolic link not allowed: '+name)
        if src.is_file():
            target = dest/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
        elif name in ('_quarto.yml','_quarto-eleve.yml','publication/quarto/tim.css',rel):
            raise LocalizationError('REQUIRED_FILE_MISSING', name)

def validate_options(options, old):
    if not 1 <= len(options) <= 5:
        raise LocalizationError('INVALID_OPTIONS','Entre 1 et 5 propositions requises.')
    parsed, labels = [], set()
    for item in options:
        if '=' not in item:
            raise LocalizationError('INVALID_OPTION','Format NOM=texte requis.')
        name, new = item.split('=',1)
        if (not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,24}',name) or name in labels
                or not new or new == old or len(new) > 150 or any(x in new for x in '\r\n\x00\\`*_{}[]<>|')):
            raise LocalizationError('INVALID_OPTION', f'Variante invalide: {name}')
        labels.add(name)
        parsed.append((name,new))
    return parsed

def replace_dom_text(capture, new):
    data = capture['dom']['blockText'].encode('utf-16-le')
    a,b = capture['dom']['startUtf16'],capture['dom']['endUtf16']
    return canonical_text(data[:a*2].decode('utf-16-le')+new+data[b*2:].decode('utf-16-le'))

def prepare(repo: Path, out: Path, capture: dict, options: list[str], guard_files: list[Path],
            expected_commit: str | None, render: bool):
    repo = repo.expanduser().resolve(strict=True)
    out = out.expanduser().absolute()
    if out.exists() or out.is_symlink():
        raise LocalizationError('OUTPUT_EXISTS', 'Le dossier de sortie existe déjà : '+str(out))
    parent = out.parent.resolve()
    if repo == parent or repo in parent.parents :
        raise LocalizationError('OUTPUT_INSIDE_REPO', 'Dossier de sortie dans ou englobant le dépôt source.')
    relative = expected_source_from_url(capture['page']['url'])
    resolved = locate(repo, relative, capture, expected_commit)
    if git(repo, 'status','--porcelain'):
        raise LocalizationError('DIRTY_REPOSITORY', 'Le dépôt contient des changements locaux.')
    old = resolved['source']['exact']
    choices = validate_options(options, old)
    guards = []
    for path in guard_files:
        guard = json.loads(path.read_text(encoding='utf-8'))
        guarded_anchor = locate(repo, relative, guard, resolved['source']['commit'])
        guards.append((guard, guarded_anchor))
    start, end = resolved['source']['start_utf8'],resolved['source']['end_utf8_exclusive']
    data = (repo/relative).read_bytes()
    if data[start:end] != old.encode('utf-8'):
        raise LocalizationError('ANCHOR_DRIFT','Les octets sources ont changé.')
    for _, anchor in guards:
        a,b = anchor['source']['start_utf8'],anchor['source']['end_utf8_exclusive']
        if start < b and a < end:
            raise LocalizationError('GUARD_OVERLAP','Ancre de protection recouvrant la cible.')
    if render and not shutil.which('quarto'):
        raise RenderError('QUARTO_MISSING: Quarto absent, ne pas affirmer que le rendu est vérifié.')
    parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.pedagolab-stage-',dir=parent))
    try:
        original = stage/'original'
        copy_project_subset(repo,original,relative)
        html_original = run_quarto(original,relative) if render else None
        if html_original:
            observed = text_in_html(html_original,capture)
            if observed != canonical_text(capture['dom']['blockText']):
                raise RenderError('ORIGINAL_HTML_MISMATCH: '+observed)
            for guard,_ in guards:
                if text_in_html(html_original,guard) != canonical_text(guard['dom']['blockText']):
                    raise RenderError('GUARD_ORIGINAL_HTML_MISMATCH')
        results = []
        for name,new in choices:
            dest = stage/'variantes'/name
            copy_project_subset(repo,dest,relative)
            changed = data[:start]+new.encode('utf-8')+data[end:]
            dest_file = dest/relative
            dest_file.write_bytes(changed)
            if dest_file.read_bytes() != changed:
                raise LocalizationError('PATCH_MISMATCH','Écriture de variante incorrecte.')
            diff = ''.join(difflib.unified_diff(data.decode('utf-8').splitlines(keepends=True),
                                                changed.decode('utf-8').splitlines(keepends=True),
                                                fromfile='a/'+relative,tofile='b/'+relative))
            diff_file = stage/'comparaisons'/f'{name}.patch'
            diff_file.parent.mkdir(parents=True,exist_ok=True)
            diff_file.write_text(diff,encoding='utf-8')
            html_new = run_quarto(dest,relative) if render else None
            verified = False
            if html_new and html_original:
                expected_target = replace_dom_text(capture,new)
                observed_target = text_in_html(html_new,capture)
                if observed_target != expected_target:
                    raise RenderError(f'RENDER_TARGET_MISMATCH ({name}): {observed_target} != {expected_target}')
                for guard,_ in guards:
                    if text_in_html(html_new,guard) != canonical_text(guard['dom']['blockText']):
                        raise RenderError(f'RENDER_GUARD_CHANGED ({name})')
                all_before,all_after = visible_text(html_original),visible_text(html_new)
                source_block = canonical_text(capture['dom']['blockText'])
                if all_before.count(source_block) != 1:
                    raise RenderError(f'RENDER_AMBIGUOUS_BLOCK ({name})')
                if all_after != all_before.replace(source_block,expected_target,1):
                    raise RenderError(f'RENDER_OTHER_TEXT_CHANGED ({name})')
                verified = True
            results.append({'option':name, 'replacement':new,
                            'patched_qmd_sha256':hashlib.sha256(changed).hexdigest(),
                            'diff':f'comparaisons/{name}.patch',
                            'qmd':f'variantes/{name}/{relative}',
                            'html':f'variantes/{name}/dist/eleve/{Path(relative).with_suffix(".html")}' if html_new else None,
                            'render_verified':verified})
        report = {'schema':'pedagolab.experiment.v0',
                  'status':'RENDER_VERIFIED_LOCAL' if render else 'SOURCE_VARIANTS_CREATED',
                  'production_write':False,'publication':'NOT_PUBLISHED',
                  'source':{k:resolved['source'][k] for k in ('path','commit','git_blob','sha256')},
                  'selection':{'line':resolved['source']['line'],'start_utf8':start,
                               'end_utf8_exclusive':end, 'exact':old,'css_path':capture['dom']['cssPath']},
                  'provenance':{'published_html_revision_verified':False,
                                'local_render_of_git_source_verified':bool(render)},
                  'guard_count':len(guards),'options':results}
        (stage/'rapport.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        if render:
            frames = [('Original', 'original/dist/eleve/'+str(Path(relative).with_suffix('.html')))]
            frames += [(item['option'], item['html']) for item in results]
            panels = ''.join('<section><h2>'+html.escape(title)+'</h2><iframe src="'+html.escape(path, quote=True)+'" title="'+html.escape(title, quote=True)+'"></iframe></section>' for title,path in frames)
            page = ('<!doctype html><html lang="fr"><meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width,initial-scale=1">'
                    '<title>Alliage — comparaison locale</title><style>'
                    'body{font:16px system-ui,sans-serif;margin:1rem;background:#f8f8f8;color:#222}'
                    '.panels{display:grid;grid-template-columns:repeat('+str(len(frames))+',minmax(280px,1fr));gap:1rem}'
                    'section{min-width:0}iframe{width:100%;height:75vh;background:white;border:1px solid #bbb}'
                    '@media(max-width:1000px){.panels{grid-template-columns:1fr}}'
                    '</style><h1>Comparaison de variantes — local uniquement</h1>'
                    '<p>Aucune version n’a été acceptée ni publiée. Ouvrir chaque page directement pour tester ses interactions.</p>'
                    '<div class="panels">'+panels+'</div></html>')
            (stage/'comparaison.html').write_text(page,encoding='utf-8')
        (stage/'README.txt').write_text('EXPÉRIMENTAL. Ne pas publier ce dossier.\n'
                                        'Les HTML sont dans variantes/<NOM>/dist/eleve/.../activite.html.\n'
                                        'Les différences sont dans comparaisons/ et le bilan est rapport.json.\n',encoding='utf-8')
        os.replace(stage,out)
        return report
    except Exception:
        shutil.rmtree(stage,ignore_errors=True)
        raise

def main():
    parser = argparse.ArgumentParser(description='Créer et rendre des variantes Quarto isolées.')
    parser.add_argument('--repo',required=True,type=Path)
    parser.add_argument('--selection',required=True,type=Path)
    parser.add_argument('--guard',action='append',default=[],type=Path)
    parser.add_argument('--option',action='append',required=True,help='NOM=nouvelle rédaction')
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--expect-commit')
    parser.add_argument('--render',action='store_true')
    args = parser.parse_args()
    try:
        capture=json.loads(args.selection.read_text(encoding='utf-8'))
        report=prepare(args.repo,args.out,capture,args.option,args.guard,args.expect_commit,args.render)
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return 0
    except (LocalizationError,RenderError,KeyError,ValueError,OSError,json.JSONDecodeError) as exc:
        reason=exc.reason if isinstance(exc,LocalizationError) else type(exc).__name__
        print(json.dumps({'status':'REFUSED','reason':reason,'detail':str(exc)},ensure_ascii=False,indent=2),file=sys.stderr)
        return 2

if __name__=='__main__':
    sys.exit(main())
