"""Regressões pequenas da integração gerencial, sem bases pessoais."""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from http.client import HTTPConnection
import json
import threading
import unittest

from openpyxl import Workbook, load_workbook

from gerencial import FIELDS, load_directory, recipients, review_recipients, support_contacts
from preview_AGENDA_SEMANAL_AUDITORIAS import load_mari, review_mari
from preview_AGENDA_AUDITORIA_E_SITUACAO_REGULARIZACAO_DOS_POLOS import load_consolidado
from preview_server import make_server


class GerencialTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / 'databases/09-11-26'
        self.data.mkdir(parents=True)
        book = Workbook()
        ws = book.active
        ws.title = 'Export'
        ws.append(['NOME UNIDADE SISTEMA', 'GESTOR DE POLO / DIRETOR UNIDADE',
                   'EMAIL GESTOR PRISMA / EMAIL DIRETOR DE UNIDADE', 'GER. COM. / GER. NEG.',
                   'CONSULTOR DE INFRA', 'AUDITOR ACADEMICO', 'GRUPO ECONOMICO'])
        ws.append(['Polo A', 'Gestor A', 'gestor@example.test', 'Negócios', 'Infra', 'Auditor ativo', 'GE-A'])
        ws.append(['Polo B', 'Gestor A', 'gestor@example.test', 'Negócios', 'Infra', 'Desligado', 'GE-B'])
        ws.append(['Polo C', 'Homônimo', 'outro@example.test', None, None, None, 'GE-C'])
        ws.append(['Filtros aplicados: filtro de exportação'])
        auditors = book.create_sheet('AUDITORES')
        auditors.append(['NOME', 'EMAIL'])
        auditors.append(['Auditor ativo', 'ativo@example.test'])
        auditors.append(['Auditor novo', 'novo@example.test'])
        book.save(self.data / 'auditoria-base-gerencial.xlsx')
        book.close()
        book = Workbook()
        book.active.title = 'Export'
        book.active.append(['Nome', 'Cargo', 'E-mail', 'Telefone', 'Canal'])
        book.active.append(['NEGOCIOS', 'Gerente de negócios', 'negocios@example.test', '', ''])
        book.active.append(['Infra', 'Infraestrutura', 'infra@example.test', '', ''])
        book.save(self.data / 'auditoria-base-gerencial-contatos.xlsx')
        book.close()
        book = Workbook()
        book.active.title = 'Export'
        book.active.append(['Polo', 'Laboratório', 'Data agendada', 'semestre_operacional_x',
                            'Tipo auditoria', 'Auditor', 'Agendada', 'Realizada',
                            'Data realização', 'Finalizada', 'Parecer Auditoria'])
        book.active.append(['Polo A', 'Lab 1', '17/11/2026 09:00', '262', 'Regular', 'Auditor do lab', 'Sim'])
        book.active.append(['Polo A', 'Lab 1', '18/11/2026 09:00', '262', 'Regular', 'Auditor do lab', 'Sim'])
        book.active.append(['Polo B', 'Lab 2', None, '262', 'Regular', 'Auditor do lab', 'Sim'])
        book.active.append(['Applied filters: semestre_operacional_x is 262'])
        book.save(self.data / 'auditoria-timeline-262.xlsx')
        book.close()
        for name, headers, values in [
            ('auditoria-apps-prazo.xlsx', ['Polo', 'Total de Aulas', 'Comprovadas', 'Pendentes'],
             [['Polo A', 10, 5, 5], ['Polo B', 12, 3, 9]]),
            ('auditoria-polos-acompanhamento-262.xlsx', ['Polo', 'Rep. Sem Retorno'],
             [['Polo A', 0], ['Polo B', 2], ['TOTAL', 2]])]:
            book = Workbook(); book.active.title = 'Export'; book.active.append(headers)
            for row in values:
                book.active.append(row)
            book.active.append(['Filtros aplicados: semestre_operacional é 262'])
            book.save(self.data / name); book.close()
        self.directory = load_directory(self.data)

    def filled(self):
        values = recipients(['Polo A', 'Polo B'], self.directory)
        values[1]['academico_nome'] = 'Auditor novo'
        return values

    def test_directory_roles_and_unassigned_auditors(self):
        self.assertEqual(len(self.directory['polos']), 3)
        values = recipients(['Polo A', 'Polo B'], self.directory)
        self.assertEqual(values[0]['negocios_email'], 'negocios@example.test')
        self.assertEqual(values[1]['academico_email'], '')
        self.assertEqual(values[1]['academico_nome'], '')
        self.assertTrue(all(r['academico_nome'] != 'Auditor novo' for r in self.directory['polos'].values()))

    def test_manager_groups_keep_every_occurrence_and_real_groups(self):
        records = load_mari(self.root)
        self.assertEqual(len(records), 1)
        record = next(iter(records.values()))
        self.assertEqual(record['polo_count'], 2)
        self.assertEqual(len(record['draft']['rows']), 3)
        self.assertEqual([r['grupo'] for r in record['draft']['rows']], ['GE-A', 'GE-A', 'GE-B'])
        self.assertEqual(record['draft']['rows'][-1]['date'], '')

    def test_same_name_with_different_emails_does_not_merge_carteiras(self):
        directory = deepcopy(self.directory)
        directory['polos']['POLO B']['email'] = 'homonimo@example.test'
        self.assertEqual(len(load_mari(self.root, directory)), 2)

    def test_email_order_does_not_split_the_same_manager(self):
        directory = deepcopy(self.directory)
        directory['polos']['POLO A']['email'] = 'one@example.test;two@example.test'
        directory['polos']['POLO B']['email'] = 'two@example.test;one@example.test'
        self.assertEqual(len(load_mari(self.root, directory)), 1)

    def test_each_polo_needs_a_valid_academic_choice(self):
        with self.assertRaises(ValueError):
            review_recipients(recipients(['Polo A', 'Polo B'], self.directory), ['Polo A', 'Polo B'], self.directory)
        values = self.filled()
        values[1]['academico_email'] = 'forged@example.test'
        reviewed = review_recipients(values, ['Polo A', 'Polo B'], self.directory)
        self.assertEqual(reviewed[1]['academico_email'], 'novo@example.test')
        self.assertEqual(self.directory['polos']['POLO B']['academico_nome'], '')

    def test_contacts_are_scoped_deduplicated_and_not_checklist(self):
        reviewed = review_recipients(self.filled(), ['Polo A', 'Polo B'], self.directory)
        self.assertEqual(len(support_contacts(reviewed)), 4)
        with self.assertRaises(ValueError):
            review_recipients(reviewed, ['Polo A'], self.directory)
        self.assertEqual(len(review_recipients(reviewed[:1], ['Polo A'], self.directory)), 1)

    def test_missing_duplicate_outside_and_invalid_emails_rejected(self):
        original = self.filled()
        for values in [[], [original[0], original[0]], [{'polo': 'Outro'}]]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                review_recipients(values, ['Polo A', 'Polo B'], self.directory)
        for field in [f for f in FIELDS if 'email' in f]:
            values = deepcopy(original)
            values[0][field] = 'bad\r\nBcc: hidden@example.test'
            with self.subTest(field=field), self.assertRaises(ValueError):
                review_recipients(values, ['Polo A', 'Polo B'], self.directory)

    def test_explicit_multimail_is_supported(self):
        values = self.filled()
        values[0]['email'] = 'one@example.test; two@example.test;one@example.test'
        self.assertEqual(review_recipients(values, ['Polo A', 'Polo B'], self.directory)[0]['email'],
                         'one@example.test;two@example.test')
        values[0]['infra_email'] = 'first@example.test;second@example.test'
        self.assertEqual(len(support_contacts(review_recipients(values, ['Polo A', 'Polo B'], self.directory))), 6)

    def test_missing_dates_stay_manual_and_deselection_is_explicit(self):
        record = next(iter(load_mari(self.root).values()))
        draft = deepcopy(record['draft'])
        draft['reviewed'] = True
        with self.assertRaises(ValueError):
            review_mari(draft, record)
        draft['rows'][-1]['selected'] = False
        self.assertEqual(len(review_mari(draft, record)['rows']), 2)

    def test_consolidado_uses_manager_and_does_not_infer_checklist(self):
        records = load_consolidado(self.root)
        active = [r for identity, r in records.items() if identity != 'manual']
        self.assertEqual(len(active), 1)
        draft = active[0]['draft']
        self.assertEqual(draft['polos'], ['Polo A', 'Polo B'])
        self.assertEqual(draft['reprovados_sem_retorno'], 2)
        self.assertTrue(all(row['auditor'] == '' and row['nota'] is None for row in draft['checklist']))
        self.assertEqual(len(draft['contatos']), 3)
        self.assertEqual(draft['prazo_auditorias'], '')
        book = load_workbook(self.data / 'emails.xlsx', read_only=True, data_only=True)
        try:
            values = list(book.active.values)
            self.assertEqual(values[0], ('Polo', 'Email', 'Enviar'))
            self.assertEqual(len(values), 3)
            self.assertTrue(all(not row[2] for row in values[1:]))
        finally:
            book.close()

    def test_consolidado_dates_use_actual_then_scheduled_with_provenance(self):
        book = load_workbook(self.data / 'auditoria-timeline-262.xlsx')
        sheet = book.active
        sheet.delete_rows(2, sheet.max_row)
        scheduled = datetime(2026, 11, 6, 14)
        actual = datetime(2026, 11, 7, 10)
        cases = [
            ('Realizada', scheduled, actual, 'Sim', 'Não', '', '2026-11-07', 'Realizada'),
            ('Reprovada com realização', scheduled, actual, 'Sim', 'Não', 'Reprovado',
             '2026-11-07', 'Realizada'),
            ('Reprovada', scheduled, None, 'Sim', 'Não', 'Reprovado', '2026-11-06',
             'Realizada (data agendada como referência)'),
            ('Finalizada', scheduled, None, 'Sim', 'Sim', 'Aprovado', '2026-11-06',
             'Finalizada (data agendada como referência)'),
            ('Agendada', scheduled, None, 'Não', 'Não', '', '2026-11-06', 'Agendada'),
            ('Sem agendamento', None, None, 'Não', 'Não', '', '', 'Agendada'),
            ('Realizada sem nenhuma data', None, None, 'Sim', 'Não', 'Reprovado', '', 'Realizada'),
        ]
        for label, agenda, done, performed, finalized, result, _, _ in cases:
            sheet.append(['Polo A', label, agenda, '262', 'Regular', 'Auditor do lab',
                          'Sim', performed, done, finalized, result])
        book.save(self.data / 'auditoria-timeline-262.xlsx')
        book.close()
        record = next(r for r in load_consolidado(self.root).values() if r['draft']['gestor'])
        agenda = {r['ambiente']: r for r in record['draft']['agenda']}
        for label, _, _, _, _, _, expected_date, expected_status in cases:
            with self.subTest(case=label):
                self.assertEqual(agenda[label]['data'], expected_date)
                self.assertEqual(agenda[label]['status'], expected_status)
        self.assertEqual(record['draft']['prazo_auditorias'], '')

    def test_editing_a_source_contact_does_not_detach_it_from_its_polo(self):
        server = make_server(self.root, 0)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            def request(method, path, payload=None):
                connection = HTTPConnection('127.0.0.1', server.server_port, timeout=20)
                try:
                    body = json.dumps(payload) if payload is not None else None
                    connection.request(method, path, body, {'Content-Type': 'application/json'} if body else {})
                    response = connection.getresponse()
                    return response.status, response.read().decode()
                finally:
                    connection.close()
            flow = '/api/draft/auditoria-situacao-polos?id=1'
            status, body = request('GET', flow)
            self.assertEqual(status, 200, body)
            draft = json.loads(body)['draft']
            for contact in draft['contatos']:
                if contact['nome'] == 'Auditor ativo':
                    contact['telefone'] = '123456789'
            draft['polos'] = ['Polo B']
            for section in ('checklist', 'agenda', 'praticas', 'laboratorios'):
                draft[section] = [r for r in draft[section] if r['polo'] == 'Polo B']
            draft['destinatarios'] = [r for r in draft['destinatarios'] if r['polo'] == 'Polo B']
            draft['destinatarios'][0]['academico_nome'] = 'Auditor novo'
            status, body = request('POST', '/api/render/auditoria-situacao-polos', {'id': '1', 'draft': draft})
            self.assertEqual(status, 200, body)
            self.assertNotIn('Auditor ativo', body)
            self.assertIn('Auditor novo', body)
        finally:
            server.shutdown(); server.server_close(); worker.join()


if __name__ == '__main__':
    unittest.main()
