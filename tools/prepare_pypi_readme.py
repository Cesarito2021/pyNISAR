"""Resolve README links in release distributions so PyPI can render the figures."""
from pathlib import Path
import re
p=Path('README.md')
s=p.read_text(encoding='utf-8')
base='https://github.com/Cesarito2021/pyNISAR/blob/v0.1.0a1/'
raw='https://raw.githubusercontent.com/Cesarito2021/pyNISAR/v0.1.0a1/'
s=re.sub(r'src="(docs/[^\"]+)"',lambda m:'src="'+raw+m[1]+'"',s)
s=re.sub(r'!\[([^\]]*)\]\((docs/[^)]+)\)',lambda m:'!['+m[1]+']('+raw+m[2]+')',s)
s=re.sub(r'\]\(((?:docs/|examples/)[^)]+|LICENSE|CITATION.cff)\)',lambda m:']('+base+m[1]+')',s)
s=re.sub(r'href="(LICENSE)"',lambda m:'href="'+base+m[1]+'"',s)
p.write_text(s,encoding='utf-8')
