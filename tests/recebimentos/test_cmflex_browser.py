from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from automations.recebimentos import cmflex_browser
from automations.recebimentos.cmflex_browser import (
    ACCOUNTS_RECEIVABLE_SELECTOR,
    COMPANY_LOGIN_SELECTOR,
    COMPANY_SELECTOR,
    DOCUMENT_ENTRIES_SELECTOR,
    DOWNLOAD_SELECTOR,
    END_DATE_SELECTOR,
    GENERATE_REPORT_SELECTOR,
    LOGIN_SELECTOR,
    OPERATIONAL_GROUPS_SELECTOR,
    PASSWORD_SELECTOR,
    QUERIES_SELECTOR,
    REPORTS_SELECTOR,
    START_DATE_SELECTOR,
    START_DATE_SELECTORS,
    USERNAME_SELECTOR,
    CMFlexConfig,
    download_document_entries,
    login_cmflex,
    open_document_entries_report,
    run_cmflex_download,
)


class FakeElement:
    def __init__(self, *, displayed=True) -> None:
        self.inputs = []
        self.js_values = []
        self.click_count = 0
        self.value = ""
        self.states = SimpleNamespace(is_displayed=displayed)
        self.scroll = SimpleNamespace(to_see=lambda: None)

    def input(self, value, *, clear=False, by_js=False):
        self.inputs.append((value, clear))
        self.value = value

    def property(self, name):
        return self.value if name == "value" else None

    def attr(self, name):
        return self.value if name == "value" else None

    def run_js(self, _script, value=None):
        if value is not None:
            self.js_values.append(value)
            self.value = value

    def click(self, **_kwargs):
        self.click_count += 1


class FakeTab:
    def __init__(self, elements=None, tab_id="main") -> None:
        self.elements = elements or {}
        self.tab_id = tab_id
        self.urls = []
        self.closed = False
        self.wait = SimpleNamespace(doc_loaded=lambda **_kwargs: None)

    def get(self, url):
        self.urls.append(url)

    def ele(self, selector, *, timeout):
        return self.elements.get(selector)

    def close(self):
        self.closed = True


class FakeMission:
    def __init__(self, path: Path) -> None:
        self.is_done = True
        self.final_path = str(path)
        self.state = "completed"


class CMFlexBrowserTests(TestCase):
    def test_report_navigation_targets_labels_instead_of_row_numbers(self):
        self.assertIn("Grupo: Operacionais", OPERATIONAL_GROUPS_SELECTOR)
        self.assertIn("Lançamento de Documentos", DOCUMENT_ENTRIES_SELECTOR)
        self.assertNotIn("/tr[24]", OPERATIONAL_GROUPS_SELECTOR)
        self.assertNotIn("/tr[37]", DOCUMENT_ENTRIES_SELECTOR)

    def test_config_reads_recebimentos_environment(self):
        environment = {
            "RECEBIMENTOS_CMFLEX_USERNAME": "usuario",
            "RECEBIMENTOS_CMFLEX_PASSWORD": "senha",
            "RECEBIMENTOS_CMFLEX_COMPANY": "MAGNA",
        }
        with (
            patch.object(cmflex_browser, "load_dotenv"),
            patch.dict("os.environ", environment, clear=True),
        ):
            config = cmflex_browser.config_from_env()

        self.assertEqual(config.username, "usuario")
        self.assertEqual(config.password, "senha")
        self.assertEqual(config.company, "MAGNA")

    def test_login_fills_credentials_and_selects_company(self):
        username = FakeElement()
        password = FakeElement()
        login = FakeElement()
        company_login = FakeElement()
        magna = SimpleNamespace(text="MAGNA - Magna Praia Hotel")

        class Select:
            options = [SimpleNamespace(text="Escolha"), magna]

            def __init__(self):
                self.selected = None

            def by_option(self, option):
                self.selected = option

        company = FakeElement()
        company.select = Select()
        tab = FakeTab(
            {
                USERNAME_SELECTOR: username,
                PASSWORD_SELECTOR: password,
                LOGIN_SELECTOR: login,
                COMPANY_SELECTOR: company,
                COMPANY_LOGIN_SELECTOR: company_login,
            }
        )
        browser = SimpleNamespace(latest_tab=tab)

        with patch.object(cmflex_browser, "sleep"):
            result = login_cmflex(browser, CMFlexConfig("usuario", "senha", "MAGNA"))

        self.assertIs(result, tab)
        self.assertEqual(username.inputs, [])
        self.assertEqual(password.inputs, [])
        self.assertEqual(username.js_values, ["usuario"])
        self.assertEqual(password.js_values, ["senha"])
        self.assertIs(company.select.selected, magna)
        self.assertEqual(login.click_count, 1)
        self.assertEqual(company_login.click_count, 1)

    def test_opens_document_entries_in_new_tab(self):
        elements = {
            selector: FakeElement()
            for selector in (
                ACCOUNTS_RECEIVABLE_SELECTOR,
                QUERIES_SELECTOR,
                REPORTS_SELECTOR,
                OPERATIONAL_GROUPS_SELECTOR,
                DOCUMENT_ENTRIES_SELECTOR,
            )
        }
        tab = FakeTab(elements)
        report_tab = FakeTab(tab_id="report")

        class Browser:
            latest_tab = tab

            def __init__(self):
                self.tab_id_reads = 0

            @property
            def tab_ids(self):
                self.tab_id_reads += 1
                return ["main"] if self.tab_id_reads == 1 else ["main", "report"]

            def get_tab(self, tab_id):
                return report_tab if tab_id == "report" else None

        browser = Browser()
        with patch.object(cmflex_browser, "sleep"):
            result = open_document_entries_report(browser, tab)

        self.assertIs(result, report_tab)
        self.assertTrue(all(element.click_count == 1 for element in elements.values()))

    def test_accepts_report_opened_in_current_tab(self):
        elements = {
            selector: FakeElement()
            for selector in (
                ACCOUNTS_RECEIVABLE_SELECTOR,
                QUERIES_SELECTOR,
                REPORTS_SELECTOR,
                OPERATIONAL_GROUPS_SELECTOR,
                DOCUMENT_ENTRIES_SELECTOR,
            )
        }
        elements[START_DATE_SELECTORS[0]] = FakeElement()
        tab = FakeTab(elements)
        browser = SimpleNamespace(latest_tab=tab, tab_ids=["main"])

        with patch.object(cmflex_browser, "sleep"):
            result = open_document_entries_report(browser, tab)

        self.assertIs(result, tab)

    def test_downloads_current_day_report(self):
        start_date = FakeElement()
        end_date = FakeElement()
        generate = FakeElement()

        with TemporaryDirectory() as directory:
            downloaded = Path(directory) / "cmflex_recebimentos_2026-09-14.xlsx"
            downloaded.touch()
            mission = FakeMission(downloaded)

            class DownloadClick:
                def __init__(self):
                    self.arguments = None

                def to_download(self, **kwargs):
                    self.arguments = kwargs
                    return mission

            download = FakeElement()
            download.click = DownloadClick()
            tab = FakeTab(
                {
                    START_DATE_SELECTOR: start_date,
                    END_DATE_SELECTOR: end_date,
                    GENERATE_REPORT_SELECTOR: generate,
                    DOWNLOAD_SELECTOR: download,
                }
            )
            with patch.object(cmflex_browser, "sleep"):
                result = download_document_entries(
                    tab,
                    Path(directory),
                    run_date=date(2026, 9, 15),
                )

        self.assertEqual(result, downloaded)
        self.assertEqual(start_date.inputs, [("14/09/2026", False)])
        self.assertEqual(end_date.inputs, [("14/09/2026", False)])
        self.assertEqual(generate.click_count, 1)
        self.assertEqual(download.click.arguments["timeout"], 30)
        self.assertEqual(download.click.arguments["new_tab"], False)
        self.assertEqual(download.click.arguments["by_js"], True)

    def test_finds_initial_date_by_label_when_absolute_xpath_changes(self):
        field = FakeElement()
        tab = FakeTab({START_DATE_SELECTORS[0]: field})

        with patch.object(cmflex_browser, "sleep"):
            result = cmflex_browser._element_any(
                tab,
                START_DATE_SELECTORS,
                "Data de Lançamento Inicial",
                None,
                timeout=1,
            )

        self.assertIs(result, field)

    def test_ignores_hidden_date_input(self):
        hidden_field = FakeElement(displayed=False)
        visible_field = FakeElement()
        tab = FakeTab(
            {
                START_DATE_SELECTOR: hidden_field,
                START_DATE_SELECTORS[0]: visible_field,
            }
        )

        with patch.object(cmflex_browser, "sleep"):
            result = cmflex_browser._element_any(
                tab,
                START_DATE_SELECTORS,
                "Data de Lançamento Inicial",
                None,
                timeout=1,
            )

        self.assertIs(result, visible_field)

    def test_date_uses_real_input_without_select_all(self):
        field = FakeElement()

        with patch.object(cmflex_browser, "sleep"):
            cmflex_browser._fill_date(
                field,
                "15/09/2026",
                "Data de Lançamento Inicial",
            )

        self.assertEqual(field.value, "15/09/2026")
        self.assertEqual(field.inputs, [("15/09/2026", False)])

    def test_run_closes_browser(self):
        class Browser:
            def __init__(self):
                self.quit_options = None

            def quit(self, **options):
                self.quit_options = options

        browser = Browser()
        report_tab = FakeTab(tab_id="report")
        config = CMFlexConfig("usuario", "senha")
        with (
            patch.object(cmflex_browser, "login_cmflex", return_value="main"),
            patch.object(
                cmflex_browser,
                "open_document_entries_report",
                return_value=report_tab,
            ),
            patch.object(
                cmflex_browser,
                "download_document_entries",
                return_value=Path("cmflex.xlsx"),
            ),
        ):
            result = run_cmflex_download(
                config,
                Path("output"),
                browser_factory=lambda: browser,
            )

        self.assertEqual(result, Path("cmflex.xlsx"))
        self.assertTrue(report_tab.closed)
        self.assertEqual(browser.quit_options, {"timeout": 1, "force": False})

    def test_run_rejects_missing_credentials_before_opening_browser(self):
        browser_factory = Mock()

        with self.assertRaisesRegex(ValueError, "usuário CMFlex, senha CMFlex"):
            run_cmflex_download(
                CMFlexConfig("", ""),
                Path("output"),
                browser_factory=browser_factory,
            )

        browser_factory.assert_not_called()
