from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import call, patch

from DrissionPage.errors import BrowserConnectError, ElementLostError, NoRectError

from automations.recebimentos import opera_browser
from automations.recebimentos.opera_browser import (
    CHANGE_LOCATION_SELECTOR,
    CONTINUE_BUTTON_SELECTOR,
    HOTEL_INPUT_SELECTORS,
    HOTEL_RESULT_SELECTORS,
    HOTEL_SEARCH_SELECTORS,
    LOGIN_BUTTON_SELECTOR,
    PASSWORD_SELECTOR,
    PROFILE_SELECTOR,
    USERNAME_SELECTOR,
    OperaLoginConfig,
    config_from_env,
    create_browser,
    download_financial_payments,
    login_opera,
    open_hotel_search,
    open_reports_and_analytics,
    run_opera_download,
    select_hotel,
)


class FakeElement:
    def __init__(self) -> None:
        self.inputs: list[tuple[str, bool]] = []
        self.click_count = 0
        self.value = ""

    def input(self, value: str, *, clear: bool) -> None:
        self.inputs.append((value, clear))
        self.value = value

    def run_js(self, _script: str) -> None:
        self.value = ""

    def property(self, name: str):
        return self.value if name == "value" else None

    def click(self) -> None:
        self.click_count += 1


class FakeWait:
    def __init__(self) -> None:
        self.timeouts: list[int] = []

    def doc_loaded(self, *, timeout: int) -> None:
        self.timeouts.append(timeout)


class FakeTab:
    def __init__(self, elements: dict[str, FakeElement]) -> None:
        self.elements = elements
        self.wait = FakeWait()
        self.urls: list[str] = []
        self.selectors: list[tuple[str, int]] = []

    def get(self, url: str) -> None:
        self.urls.append(url)

    def ele(self, selector: str, *, timeout: int):
        self.selectors.append((selector, timeout))
        return self.elements.get(selector)


class FakeBrowser:
    def __init__(self, tab: FakeTab) -> None:
        self.latest_tab = tab


class FakeMission:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.is_done = True
        self.final_path = str(path)
        self.state = "completed"
        self.cancel_count = 0

    def cancel(self) -> None:
        self.cancel_count += 1


class FakeDownloadClick:
    def __init__(self, mission: FakeMission) -> None:
        self.mission = mission
        self.arguments = None

    def to_download(self, **kwargs):
        self.arguments = kwargs
        return self.mission


class FakeDownloadElement:
    def __init__(self, mission: FakeMission) -> None:
        self.click = FakeDownloadClick(mission)


class OperaBrowserTests(TestCase):
    def test_dynamic_selector_search_disables_per_selector_implicit_wait(self):
        class States:
            is_displayed = True

        class Element:
            states = States()

        class Tab:
            def __init__(self) -> None:
                self.calls = []

            def eles(self, selector, *, timeout):
                self.calls.append((selector, timeout))
                return [Element()]

        tab = Tab()
        result = opera_browser.find_visible_any(
            tab,
            ("xpath://button",),
            "Botão",
            timeout=1,
        )

        self.assertIsInstance(result, Element)
        self.assertEqual(tab.calls, [("xpath://button", 0)])

    def test_falls_back_to_javascript_click_when_element_has_no_dimensions(self):
        class Click:
            def __init__(self) -> None:
                self.by_js: list[bool] = []

            def __call__(self, *, by_js: bool = False) -> None:
                self.by_js.append(by_js)

        element = type("Element", (), {})()
        element.scroll = type(
            "Scroll", (), {"to_see": lambda _self: (_ for _ in ()).throw(NoRectError())}
        )()
        element.click = Click()

        with patch.object(opera_browser, "sleep"):
            opera_browser._click_rendered_or_by_js(element)

        self.assertEqual(element.click.by_js, [True])

    def test_opens_responsive_reports_flyout_before_analytics(self):
        tab = FakeTab({})
        with patch.object(
            opera_browser,
            "click_visible_any",
            side_effect=[None, RuntimeError("ainda fechado"), None, None],
        ) as click_any:
            open_reports_and_analytics(tab)

        self.assertEqual(
            [item.args[1] for item in click_any.call_args_list],
            [
                opera_browser.REPORTS_MENU_SELECTORS,
                opera_browser.REPORTS_ANALYTICS_SELECTORS,
                opera_browser.REPORTS_FLYOUT_SELECTORS,
                opera_browser.REPORTS_ANALYTICS_SELECTORS,
            ],
        )
        self.assertEqual(tab.wait.timeouts, [60])

    def test_retries_when_drission_cannot_connect_to_first_chrome(self):
        browser = object()
        with (
            patch.object(
                opera_browser,
                "_browser_options",
                side_effect=[object(), object()],
            ) as options,
            patch.object(
                opera_browser,
                "Chromium",
                side_effect=[BrowserConnectError(), browser],
            ) as chromium,
            patch.object(opera_browser, "sleep"),
        ):
            result = create_browser()

        self.assertIs(result, browser)
        self.assertEqual(options.call_count, 2)
        self.assertEqual(chromium.call_count, 2)

    def test_config_loads_existing_opera_variables_from_dotenv(self):
        with (
            patch.object(opera_browser, "load_environment"),
            patch.dict(
                "os.environ",
                {
                    "OPERA_USERNAME": "usuario-existente",
                    "OPERA_PASSWORD": "senha-existente",
                },
                clear=True,
            ),
        ):
            config = config_from_env()

        self.assertEqual(config.username, "usuario-existente")
        self.assertEqual(config.password, "senha-existente")

    def test_uses_independent_copy_of_booking_opera_login_xpaths(self):
        self.assertEqual(
            USERNAME_SELECTOR,
            'xpath://*[@id="idcs-signin-basic-signin-form-username"]',
        )
        self.assertEqual(
            PASSWORD_SELECTOR,
            'xpath://*[@id="idcs-signin-basic-signin-form-password|input"]',
        )
        self.assertEqual(
            LOGIN_BUTTON_SELECTOR,
            'xpath://*[@id="idcs-signin-basic-signin-form-submit"]/button',
        )
        self.assertEqual(
            CONTINUE_BUTTON_SELECTOR,
            'xpath://*[@id="ode_init_ovrdbtn"]',
        )

    def test_fills_credentials_and_clicks_access_button(self):
        username = FakeElement()
        password = FakeElement()
        button = FakeElement()
        tab = FakeTab(
            {
                USERNAME_SELECTOR: username,
                PASSWORD_SELECTOR: password,
                LOGIN_BUTTON_SELECTOR: button,
            }
        )

        result = login_opera(
            FakeBrowser(tab),
            OperaLoginConfig("usuario", "senha", "https://opera.example/login"),
            sleeper=lambda _seconds: None,
        )

        self.assertIs(result, tab)
        self.assertEqual(tab.urls, ["https://opera.example/login"])
        self.assertEqual(username.inputs, [("usuario", True)])
        self.assertEqual(password.inputs, [("senha", True)])
        self.assertEqual(button.click_count, 1)
        self.assertEqual(tab.wait.timeouts, [60, 60])

    def test_ignores_popup_error_and_continues_when_present(self):
        username = FakeElement()
        password = FakeElement()
        login_button = FakeElement()
        continue_button = FakeElement()
        continue_button.scroll = type(
            "FakeScroll", (), {"to_see": lambda _self: None}
        )()
        tab = FakeTab(
            {
                USERNAME_SELECTOR: username,
                PASSWORD_SELECTOR: password,
                LOGIN_BUTTON_SELECTOR: login_button,
                CONTINUE_BUTTON_SELECTOR: continue_button,
            }
        )

        login_opera(
            FakeBrowser(tab),
            OperaLoginConfig("usuario", "senha", "https://opera.example/login"),
            sleeper=lambda _seconds: None,
        )

        self.assertEqual(login_button.click_count, 1)
        self.assertEqual(continue_button.click_count, 1)
        self.assertEqual(tab.wait.timeouts, [60, 60, 60])

    def test_opens_profile_and_change_location_with_copied_xpaths(self):
        self.assertEqual(len(HOTEL_INPUT_SELECTORS), 3)
        self.assertEqual(len(HOTEL_SEARCH_SELECTORS), 2)
        self.assertEqual(len(HOTEL_RESULT_SELECTORS), 2)
        field = object()
        with (
            patch.object(opera_browser, "click_visible_any") as click,
            patch.object(opera_browser, "find_visible_any", return_value=field),
        ):
            result = open_hotel_search(object())

        self.assertIs(result, field)
        self.assertEqual(
            [item.args[1] for item in click.call_args_list],
            [(PROFILE_SELECTOR,), (CHANGE_LOCATION_SELECTOR,)],
        )

    def test_searches_hotel_and_selects_first_result(self):
        field = FakeElement()
        tab = FakeTab({})
        with (
            patch.object(opera_browser, "open_hotel_search", return_value=field),
            patch.object(opera_browser, "click_visible_any") as click,
            patch.object(opera_browser, "sleep"),
        ):
            select_hotel(tab, "  MAGNA - Magna Praia Hotel  ")

        self.assertEqual(field.inputs, [("MAGNA - Magna Praia Hotel", True)])
        self.assertEqual(
            click.call_args_list,
            [
                call(
                    tab,
                    HOTEL_SEARCH_SELECTORS,
                    "Pesquisa do hotel/resort",
                    None,
                    settle_seconds=opera_browser.PAGE_SETTLE_SECONDS,
                ),
                call(
                    tab,
                    HOTEL_RESULT_SELECTORS,
                    "Hotel/resort pesquisado",
                    None,
                    settle_seconds=opera_browser.PAGE_SETTLE_SECONDS,
                ),
            ],
        )
        self.assertEqual(tab.wait.timeouts, [60])

    def test_downloads_financial_payments_for_previous_day(self):
        report_name = FakeElement()
        report_date_field = FakeElement()
        filter_one = FakeElement()
        filter_two = FakeElement()
        tab = FakeTab({})

        with TemporaryDirectory() as directory:
            downloaded = Path(directory) / "opera_recebimentos_2026-09-13.xml"
            downloaded.touch()
            mission = FakeMission(downloaded)
            download_button = FakeDownloadElement(mission)
            with (
                patch.object(
                    opera_browser,
                    "find_visible_any",
                    side_effect=[
                        report_name,
                        report_date_field,
                        filter_one,
                        filter_two,
                        download_button,
                    ],
                ) as find_any,
                patch.object(opera_browser, "open_reports_and_analytics") as navigation,
                patch.object(opera_browser, "click_visible_any") as click_any,
                patch.object(opera_browser, "sleep"),
            ):
                result = download_financial_payments(
                    tab,
                    Path(directory),
                    run_date=date(2026, 9, 14),
                )

        self.assertEqual(result, downloaded)
        self.assertEqual(report_name.inputs, [("CASH", True)])
        self.assertEqual(report_date_field.inputs, [("13/09/2026", True)])
        self.assertEqual(filter_one.inputs, [])
        self.assertEqual(filter_two.inputs, [])
        self.assertEqual(
            opera_browser.REPORT_NAME_SELECTORS[0],
            "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[4]/span/span/div/div[2]/div/div/div[2]/span/div/div[2]/div/div[2]/div[2]/span/span/span[2]/span[2]/span/input",
        )
        self.assertEqual(
            opera_browser.REPORT_SEARCH_SELECTORS[0],
            "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[4]/span/span/div/div[2]/div/div/div[3]/span/span[2]/div",
        )
        self.assertEqual(
            opera_browser.FINANCIAL_PAYMENTS_SELECTORS[0],
            "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[6]/span/span[1]/span/div/div/div/div/div/div[2]/div/div[2]/table/tbody/tr[4]/td[1]/div/table/tbody/tr/td[3]",
        )
        self.assertEqual(
            opera_browser.EDIT_REPORT_SELECTORS[0],
            "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[7]/span/div/div/span/span/span[2]/span[1]/span/div[3]",
        )
        self.assertEqual(
            opera_browser.REPORT_DATE_SELECTORS[0],
            "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[4]/span/span/span/div/div/div/div/span/div[2]/div[3]/div/div[2]/div[1]/span/span/span[2]/span[2]/span[1]/input",
        )
        self.assertEqual(
            opera_browser.FILTER_FIELD_SELECTORS[0][0],
            "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[4]/span/span/span/div/div/div/div/span/div[3]/div[2]/div/div[2]/div[1]/span/span/span[2]/span[2]/span/span/input",
        )
        self.assertEqual(
            opera_browser.FILTER_FIELD_SELECTORS[1][0],
            "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[4]/span/span/span/div/div/div/div/span/div[3]/div[2]/div/div[2]/div[2]/span/span/span[2]/span[2]/span/span/input",
        )
        self.assertEqual(
            opera_browser.GENERATE_REPORT_SELECTORS[0],
            "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[5]/span/div/div/span/span/span[3]/span[1]/span/div[1]",
        )
        self.assertEqual(
            opera_browser.REPORT_FORMAT_SELECTORS[0],
            "xpath:/html/body/div[1]/form/div/div[2]/div[1]/div[1]/table/tbody/tr/td/div/div/table/tbody/tr[2]/td[2]/div/div[2]/div/div[2]/div/span/span/span[2]/span[2]/table/tbody/tr/td[2]/div/fieldset/div[3]/span/label",
        )
        self.assertEqual(
            opera_browser.FINAL_DOWNLOAD_SELECTORS[0],
            "xpath:/html/body/div[1]/form/div/div[2]/div[1]/div[1]/table/tbody/tr/td/div/div/table/tbody/tr[3]/td[2]/table/tbody/tr/td[1]/span/span[1]/span[2]/div",
        )
        self.assertEqual(
            find_any.call_args_list,
            [
                call(
                    tab,
                    opera_browser.REPORT_NAME_SELECTORS,
                    "Campo Report Name",
                    None,
                    timeout=45,
                ),
                call(
                    tab,
                    opera_browser.REPORT_DATE_SELECTORS,
                    "Data do relatório",
                    None,
                    timeout=45,
                ),
                call(
                    tab,
                    opera_browser.FILTER_FIELD_SELECTORS[0],
                    "Campo de filtro 1",
                    None,
                    timeout=30,
                ),
                call(
                    tab,
                    opera_browser.FILTER_FIELD_SELECTORS[1],
                    "Campo de filtro 2",
                    None,
                    timeout=30,
                ),
                call(
                    tab,
                    opera_browser.FINAL_DOWNLOAD_SELECTORS,
                    "Download do relatório",
                    None,
                    timeout=45,
                ),
            ],
        )
        self.assertEqual(
            click_any.call_args_list,
            [
                call(
                    tab,
                    opera_browser.REPORT_SEARCH_SELECTORS,
                    "Busca de relatórios",
                    None,
                    settle_seconds=opera_browser.PAGE_SETTLE_SECONDS,
                    timeout=45,
                ),
                call(
                    tab,
                    opera_browser.FINANCIAL_PAYMENTS_SELECTORS,
                    "Relatório Pagamentos Financeiros",
                    None,
                    settle_seconds=opera_browser.PAGE_SETTLE_SECONDS,
                    timeout=45,
                ),
                call(
                    tab,
                    opera_browser.EDIT_REPORT_SELECTORS,
                    "Edição do relatório",
                    None,
                    settle_seconds=opera_browser.PAGE_SETTLE_SECONDS,
                    timeout=45,
                ),
                call(
                    tab,
                    opera_browser.GENERATE_REPORT_SELECTORS,
                    "Geração do relatório",
                    None,
                    settle_seconds=opera_browser.PAGE_SETTLE_SECONDS,
                    timeout=45,
                ),
                call(
                    tab,
                    opera_browser.REPORT_FORMAT_SELECTORS,
                    "Formato do relatório",
                    None,
                    settle_seconds=opera_browser.ACTION_SETTLE_SECONDS,
                    timeout=30,
                ),
            ],
        )
        navigation.assert_called_once_with(tab, None)
        self.assertEqual(
            download_button.click.arguments,
            {
                "save_path": Path(directory).resolve(),
                "rename": "opera_recebimentos_2026-09-13",
                "new_tab": True,
                "by_js": True,
                "timeout": 60,
            },
        )
        self.assertEqual(mission.cancel_count, 0)

    def test_download_wait_returns_immediately_when_mission_is_done(self):
        mission = FakeMission(Path("opera.xml"))

        with patch.object(opera_browser, "sleep") as wait:
            result = opera_browser._wait_for_report_download(mission, None)

        self.assertEqual(result, Path("opera.xml"))
        wait.assert_not_called()

    def test_download_wait_cancels_mission_on_timeout(self):
        mission = FakeMission(Path("opera.xml"))
        mission.is_done = False
        with (
            patch.object(opera_browser, "monotonic", side_effect=[0, 181]),
            self.assertRaisesRegex(RuntimeError, "180 segundos"),
        ):
            opera_browser._wait_for_report_download(mission, None)

        self.assertEqual(mission.cancel_count, 1)

    def test_relocates_download_button_when_opera_replaces_element(self):
        stale_mission = FakeMission(Path("stale.xml"))
        stale_button = FakeDownloadElement(stale_mission)

        def raise_element_lost(**_kwargs):
            raise ElementLostError()

        stale_button.click.to_download = raise_element_lost
        valid_mission = FakeMission(Path("valid.xml"))
        valid_button = FakeDownloadElement(valid_mission)
        with (
            patch.object(
                opera_browser,
                "find_visible_any",
                side_effect=[stale_button, valid_button],
            ) as find,
            patch.object(opera_browser, "sleep"),
        ):
            result = opera_browser._start_report_download(
                object(),
                Path("output"),
                date(2026, 9, 14),
                None,
            )

        self.assertIs(result, valid_mission)
        self.assertEqual(find.call_count, 2)
        self.assertEqual(valid_button.click.arguments["by_js"], True)

    def test_rpa_closes_browser_after_download(self):
        class Browser:
            def __init__(self) -> None:
                self.quit_count = 0
                self.quit_options = None

            def quit(self, **options) -> None:
                self.quit_count += 1
                self.quit_options = options

        browser = Browser()
        config = OperaLoginConfig("usuario", "senha")
        with (
            patch.object(opera_browser, "login_opera", return_value="tab") as login,
            patch.object(opera_browser, "select_hotel") as hotel,
            patch.object(
                opera_browser,
                "download_financial_payments",
                return_value=Path("opera.xml"),
            ) as download,
        ):
            result = run_opera_download(
                config,
                "MAGNA - Magna Praia Hotel",
                Path("output"),
                browser_factory=lambda: browser,
            )

        self.assertEqual(result, Path("opera.xml"))
        login.assert_called_once_with(browser, config, None)
        hotel.assert_called_once_with("tab", "MAGNA - Magna Praia Hotel", None)
        download.assert_called_once_with("tab", Path("output"), None)
        self.assertEqual(browser.quit_count, 1)
        self.assertEqual(browser.quit_options, {"timeout": 1, "force": False})
