"""Run only the original body-data readers and HTML renderer, never transports."""
import ast
from pathlib import Path
import re
from types import SimpleNamespace
import pandas

FUNCTIONS = {
    'chave', 'ler_sequencias', 'adicionar_labs', 'gerar_html',
}
CONSTANTS = {
    'ARQUIVOS_SEQ', 'TITULO', 'SUBTITULO', 'AREA_MACRO', 'SUB_AREA',
}


def load_aulas(data_dir):
    data_dir = Path(data_dir).resolve()
    source = data_dir / 'disparar_emails.py'
    tree = ast.parse(source.read_text(encoding='utf-8-sig'), filename=str(source))

    def local_path(filename):
        path = (data_dir / filename).resolve()
        if path.parent != data_dir or path.suffix not in {'.xlsx', '.xlsb'}:
            raise ValueError('Arquivo de dados fora da pasta de aulas práticas')
        return path

    def read_excel(filename, **kwargs):
        return pandas.read_excel(local_path(filename), **kwargs)

    namespace = {
        're': re,
        'pd': SimpleNamespace(read_excel=read_excel),
        'os': SimpleNamespace(path=SimpleNamespace(exists=lambda name: local_path(name).is_file())),
        'print': lambda *args, **kwargs: None,
    }
    functions = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in CONSTANTS:
                    namespace[target.id] = ast.literal_eval(node.value)
        elif isinstance(node, ast.FunctionDef) and node.name in FUNCTIONS:
            functions.append(node)
    if {n.name for n in functions} != FUNCTIONS or not CONSTANTS <= namespace.keys():
        raise ValueError('As funções ou configurações esperadas não estão no gerador original')
    module = ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[]))
    exec(compile(module, str(source), 'exec'), namespace)
    polos = namespace['ler_sequencias']()
    namespace['adicionar_labs'](polos)

    for polo in polos.values():
        polo['label'] = polo['nome']
        polo['polo_count'] = 1
        polo['_render'] = namespace['gerar_html']
    return dict(sorted(polos.items(), key=lambda item: item[1]['label']))


def render_aulas(model):
    return model['_render'](model)
