"""Approved CLFT text replaces prose without replacing the email artwork."""
import base64
import hashlib
from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from preview_AGENDA_FAST_TRACK_INFRA_2026 import render_fast_track


class EmailDocument(HTMLParser):
    def __init__(self):
        super().__init__()
        self.words, self.images, self.links, self.tables = [], [], [], []

    def handle_data(self, data):
        self.words.append(data)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'img':
            self.images.append(attrs)
        elif tag == 'a':
            self.links.append(attrs['href'])
        elif tag == 'table':
            self.tables.append(attrs)


class FastTrackTemplateTests(unittest.TestCase):
    def test_clft_text_deadline_links_and_existing_visual_shell(self):
        root = Path(__file__).resolve().parents[1]
        raw = render_fast_track(root)
        document = EmailDocument()
        document.feed(raw.decode('utf-8'))
        text = ' '.join(' '.join(document.words).split())
        for passage in (
            '20/11/2026, sem prorrogações', 'Como será a análise dos seus checklists', '(CL-INSUMOS)',
            'O que fazer se o checklist for reprovado', '(CL – REVENUE SHARE)', 'Passo a passo',
            '25 banquetas', 'a lista individualizada dos insumos pendentes que você precisa adquirir.',
            'Confira a aba "Iniciados".', 'Mais > Atualizar Dados', 'alvará de funcionamento',
            'licença sanitária', 'comprimento × largura', 'Ambiente que ainda não existe:',
            'Ambientes compartilhados:', 'Conclua e sincronize.', 'Depois do envio',
            'Links úteis (é preciso estar logado no PAD)', 'Trate como prioridade máxima.',
            'Auditoria de Infraestrutura e Acadêmica',
        ):
            self.assertIn(passage, text)
        self.assertNotIn('31/08', text)
        self.assertNotIn('Público', text, 'PDF classification footer is not email prose')
        self.assertEqual(document.links, [
            'https://kroton.service-now.com/pad?id=kb_article&sys_id=82004983471b3654602eab32036d432d',
            'https://kroton.service-now.com/pad?id=kb_article&sys_id=2fd9f1c487d0fa50cf44cbf30cbb35f4',
        ])
        self.assertEqual([hashlib.sha256(base64.b64decode(image['src'].split(',', 1)[1])).hexdigest()
                          for image in document.images], [
            '7164cc24c78afcf36c8dda40ac29235c0795c957b87877c4f9f13f956c34b0bc',
            '1a2ddcd18628770230f1c04e71c567445203491d98f2609d39e92a9103cab696',
        ])
        self.assertEqual(document.tables[1]['width'], '680')
        self.assertIn("font-family:'Segoe UI',Arial,sans-serif", document.tables[1]['style'])
        with TemporaryDirectory() as folder:
            target = Path(folder) / 'fluxos/AGENDA_FAST_TRACK_INFRA_2026/modelo_email.html'
            target.parent.mkdir(parents=True)
            target.write_bytes(raw)
            self.assertEqual(render_fast_track(folder), raw, 'static preview still needs no spreadsheets')


if __name__ == '__main__':
    unittest.main()
