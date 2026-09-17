"""Acesso ao OPERA exclusivo da automação de conferência de recebimentos."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from threading import Event
from time import monotonic, sleep
from typing import Any

from dotenv import load_dotenv
from DrissionPage import Chromium, ChromiumOptions
from DrissionPage.errors import (
    BrowserConnectError,
    ContextLostError,
    ElementLostError,
    NoRectError,
)

from automations.recebimentos.opera_selectors import (
    CHANGE_LOCATION_SELECTOR,
    CONTINUE_BUTTON_SELECTOR,
    EDIT_REPORT_SELECTORS,
    FILTER_FIELD_SELECTORS,
    FINAL_DOWNLOAD_SELECTORS,
    FINANCIAL_PAYMENTS_SELECTORS,
    GENERATE_REPORT_SELECTORS,
    HOTEL_INPUT_SELECTORS,
    HOTEL_RESULT_SELECTORS,
    HOTEL_SEARCH_SELECTORS,
    LOGIN_BUTTON_SELECTOR,
    OPERA_URL,
    PASSWORD_SELECTOR,
    PROFILE_SELECTOR,
    REPORT_DATE_SELECTORS,
    REPORT_FORMAT_SELECTORS,
    REPORT_NAME_SELECTORS,
    REPORT_SEARCH_SELECTORS,
    REPORTS_ANALYTICS_SELECTORS,
    REPORTS_FLYOUT_SELECTORS,
    REPORTS_MENU_SELECTORS,
    USERNAME_SELECTOR,
)
from automations.recebimentos.opera_selectors import (
    HOTEL_INPUT_SELECTOR as HOTEL_INPUT_SELECTOR,
)
from automations.recebimentos.opera_selectors import (
    HOTEL_RESULT_SELECTOR as HOTEL_RESULT_SELECTOR,
)
from automations.recebimentos.opera_selectors import (
    HOTEL_SEARCH_SELECTOR as HOTEL_SEARCH_SELECTOR,
)
from automations.recebimentos.parsers import opera_xml_has_transactions

POLL_INTERVAL = 0.25
ACTION_SETTLE_SECONDS = 0.25
PAGE_SETTLE_SECONDS = 0.75
FILTER_CLEAR_SETTLE_SECONDS = 2.0
OPERA_QUERY_RETRIES = 3
TRANSIENT_BROWSER_ERRORS = (ContextLostError, ElementLostError, NoRectError)


class RecebimentosAutomationCancelled(RuntimeError):
    """Indica cancelamento solicitado durante o RPA de recebimentos."""


@dataclass(frozen=True)
class OperaLoginConfig:
    username: str
    password: str
    url: str = OPERA_URL

    def validate(self) -> None:
        missing = [
            name
            for name, value in (
                ("usuário OPERA", self.username),
                ("senha OPERA", self.password),
                ("URL OPERA", self.url),
            )
            if not value.strip()
        ]
        if missing:
            raise ValueError("Preencha: " + ", ".join(missing))


def load_environment() -> None:
    """Carrega o .env sem sobrescrever variáveis definidas no processo."""
    load_dotenv()


def _environment_value(primary: str, fallback: str) -> str:
    return os.getenv(primary) or os.getenv(fallback, "")


def config_from_env() -> OperaLoginConfig:
    load_environment()
    return OperaLoginConfig(
        username=_environment_value("RECEBIMENTOS_OPERA_USERNAME", "OPERA_USERNAME"),
        password=_environment_value("RECEBIMENTOS_OPERA_PASSWORD", "OPERA_PASSWORD"),
        url=_environment_value("RECEBIMENTOS_OPERA_URL", "OPERA_URL") or OPERA_URL,
    )


def _browser_options() -> ChromiumOptions:
    options = ChromiumOptions().auto_port()
    options.set_pref("credentials_enable_service", False)
    options.set_pref("profile.password_manager_enabled", False)
    options.set_argument("--disable-save-password-bubble")
    options.set_argument(
        "--disable-features=PasswordManagerOnboarding,PasswordLeakDetection"
    )
    options.set_argument("--window-size=1920,1080")
    if os.getenv("RECEBIMENTOS_HEADLESS", "false").strip().casefold() not in {
        "0",
        "false",
        "no",
        "off",
    }:
        options.set_argument("--headless=new")
    return options


def create_browser() -> Chromium:
    last_error: BrowserConnectError | None = None
    for attempt in range(2):
        try:
            return Chromium(_browser_options())
        except BrowserConnectError as error:
            last_error = error
            if attempt == 0:
                sleep(1)
    raise RuntimeError(
        "O Chrome abriu, mas o DrissionPage não conseguiu conectar à porta local "
        "após duas tentativas. Feche as janelas do Chrome abertas pela automação e "
        "execute novamente."
    ) from last_error


def _checkpoint(cancel: Event | None) -> None:
    if cancel is not None and cancel.is_set():
        raise RecebimentosAutomationCancelled(
            "Execução da conferência de recebimentos cancelada."
        )


def _click_rendered_or_by_js(element: Any) -> None:
    """Clica normalmente e contorna controles sem caixa renderizada."""
    try:
        element.scroll.to_see()
        sleep(ACTION_SETTLE_SECONDS)
        element.click()
    except NoRectError:
        element.click(by_js=True)


def find_visible_any(
    tab: Any,
    selectors: tuple[str, ...],
    description: str,
    cancel: Event | None = None,
    timeout: int = 30,
) -> Any:
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        _checkpoint(cancel)
        for selector in selectors:
            try:
                # O laço externo controla o timeout total. Desativa a espera
                # implícita em cada seletor para evitar atrasos acumulados.
                elements = tab.eles(selector, timeout=0)
            except TRANSIENT_BROWSER_ERRORS:
                continue
            for element in elements:
                try:
                    if element.states.is_displayed:
                        return element
                except TRANSIENT_BROWSER_ERRORS:
                    continue
        sleep(POLL_INTERVAL)
    raise RuntimeError(f"{description} não encontrado.")


def click_visible_any(
    tab: Any,
    selectors: tuple[str, ...],
    description: str,
    cancel: Event | None = None,
    *,
    settle_seconds: float = ACTION_SETTLE_SECONDS,
    timeout: int = 30,
) -> None:
    deadline = monotonic() + timeout
    last_error: Exception | None = None
    while monotonic() < deadline:
        _checkpoint(cancel)
        try:
            element = find_visible_any(tab, selectors, description, cancel, timeout=5)
            _click_rendered_or_by_js(element)
            if settle_seconds:
                sleep(settle_seconds)
            return
        except (RuntimeError, *TRANSIENT_BROWSER_ERRORS) as error:
            last_error = error
            sleep(POLL_INTERVAL)
    raise RuntimeError(
        f"{description} não respondeu ao clique. Última causa: {last_error}"
    ) from last_error


def open_reports_and_analytics(tab: Any, cancel: Event | None = None) -> None:
    """Abre relatórios tanto na barra completa quanto no menu responsivo."""
    click_visible_any(
        tab,
        REPORTS_MENU_SELECTORS,
        "Menu Relatórios",
        cancel,
        settle_seconds=PAGE_SETTLE_SECONDS,
        timeout=45,
    )

    # No layout largo, o item final fica disponível imediatamente. No layout
    # responsivo, aparece antes a linha intermediária "Reports >".
    try:
        click_visible_any(
            tab,
            REPORTS_ANALYTICS_SELECTORS,
            "Relatórios e análises",
            cancel,
            settle_seconds=PAGE_SETTLE_SECONDS,
            timeout=4,
        )
    except RuntimeError:
        click_visible_any(
            tab,
            REPORTS_FLYOUT_SELECTORS,
            "Submenu Reports",
            cancel,
            settle_seconds=ACTION_SETTLE_SECONDS,
            timeout=20,
        )
        click_visible_any(
            tab,
            REPORTS_ANALYTICS_SELECTORS,
            "Relatórios e análises",
            cancel,
            settle_seconds=PAGE_SETTLE_SECONDS,
            timeout=30,
        )

    tab.wait.doc_loaded(timeout=60)


def login_opera(
    browser: Chromium,
    config: OperaLoginConfig,
    cancel: Event | None = None,
    *,
    sleeper: Callable[[float], None] = sleep,
) -> Any:
    """Preenche e envia a tela de login do OPERA."""
    config.validate()
    tab = browser.latest_tab
    tab.get(config.url)
    tab.wait.doc_loaded(timeout=60)
    sleeper(PAGE_SETTLE_SECONDS)

    fields = (
        (USERNAME_SELECTOR, config.username, "usuário"),
        (PASSWORD_SELECTOR, config.password, "senha"),
    )
    for selector, value, field_name in fields:
        _checkpoint(cancel)
        field = tab.ele(selector, timeout=60)
        if not field:
            raise RuntimeError(f"Campo de {field_name} do OPERA não encontrado.")
        field.input(value, clear=True)
        sleeper(ACTION_SETTLE_SECONDS)

    _checkpoint(cancel)
    login_button = tab.ele(LOGIN_BUTTON_SELECTOR, timeout=30)
    if not login_button:
        raise RuntimeError("Botão de login do OPERA não encontrado.")
    login_button.click()
    sleeper(PAGE_SETTLE_SECONDS)
    tab.wait.doc_loaded(timeout=60)

    continue_button = tab.ele(CONTINUE_BUTTON_SELECTOR, timeout=10)
    if continue_button:
        continue_button.scroll.to_see()
        sleeper(ACTION_SETTLE_SECONDS)
        continue_button.click()
        sleeper(PAGE_SETTLE_SECONDS)
        tab.wait.doc_loaded(timeout=60)
    return tab


def open_hotel_search(tab: Any, cancel: Event | None = None) -> Any:
    """Abre o painel dinâmico de localização do OPERA."""
    last_error: RuntimeError | None = None
    for _attempt in range(OPERA_QUERY_RETRIES):
        _checkpoint(cancel)
        try:
            click_visible_any(
                tab,
                (PROFILE_SELECTOR,),
                "Perfil do OPERA",
                cancel,
                settle_seconds=PAGE_SETTLE_SECONDS,
                timeout=45,
            )
            click_visible_any(
                tab,
                (CHANGE_LOCATION_SELECTOR,),
                "Alteração de localização",
                cancel,
                settle_seconds=PAGE_SETTLE_SECONDS,
                timeout=30,
            )
            return find_visible_any(
                tab,
                HOTEL_INPUT_SELECTORS,
                "Campo de pesquisa do hotel/resort",
                cancel,
                timeout=20,
            )
        except RuntimeError as error:
            last_error = error
            sleep(ACTION_SETTLE_SECONDS)
    raise RuntimeError(
        "Janela de pesquisa do hotel/resort não abriu após "
        f"{OPERA_QUERY_RETRIES} tentativas: {last_error}"
    )


def select_hotel(
    tab: Any,
    hotel_name: str,
    cancel: Event | None = None,
) -> None:
    """Pesquisa e seleciona a localização do OPERA."""
    normalized_name = hotel_name.strip()
    if not normalized_name:
        raise ValueError("Informe o hotel/resort do OPERA.")

    field = open_hotel_search(tab, cancel)
    field.input(normalized_name, clear=True)
    sleep(ACTION_SETTLE_SECONDS)
    click_visible_any(
        tab,
        HOTEL_SEARCH_SELECTORS,
        "Pesquisa do hotel/resort",
        cancel,
        settle_seconds=PAGE_SETTLE_SECONDS,
    )
    click_visible_any(
        tab,
        HOTEL_RESULT_SELECTORS,
        "Hotel/resort pesquisado",
        cancel,
        settle_seconds=PAGE_SETTLE_SECONDS,
    )
    tab.wait.doc_loaded(timeout=60)


def _start_report_download(
    tab: Any,
    target_dir: Path,
    report_date: date,
    cancel: Event | None,
) -> Any:
    last_error: Exception | None = None
    for _attempt in range(OPERA_QUERY_RETRIES):
        _checkpoint(cancel)
        download_button = find_visible_any(
            tab,
            FINAL_DOWNLOAD_SELECTORS,
            "Download do relatório",
            cancel,
            timeout=45,
        )
        try:
            mission = download_button.click.to_download(
                save_path=target_dir,
                rename=f"opera_recebimentos_{report_date:%Y-%m-%d}",
                # O OPERA inicia o arquivo em uma nova janela.
                new_tab=True,
                by_js=True,
                timeout=60,
            )
            if mission:
                return mission
        except TRANSIENT_BROWSER_ERRORS as error:
            last_error = error
            sleep(ACTION_SETTLE_SECONDS)
    raise RuntimeError(
        "O botão final do OPERA foi substituído durante o clique e o download não "
        f"iniciou após {OPERA_QUERY_RETRIES} tentativas."
    ) from last_error


def _wait_for_report_download(
    mission: Any,
    cancel: Event | None,
    *,
    timeout: float = 180,
) -> Path:
    """Aguarda sem o wait(timeout), que sempre espera todo o prazo na v4.1.1.4."""
    deadline = monotonic() + timeout
    while not mission.is_done:
        _checkpoint(cancel)
        if monotonic() >= deadline:
            try:
                mission.cancel()
            except Exception:
                pass
            raise RuntimeError(
                f"O download do relatório OPERA não terminou em {timeout:g} segundos."
            )
        sleep(0.1)

    downloaded = mission.final_path
    if not downloaded:
        raise RuntimeError(
            f"O download do relatório OPERA terminou com estado {mission.state!r}."
        )
    return Path(downloaded)


def _clear_filter_field(
    tab: Any,
    selectors: tuple[str, ...],
    description: str,
    cancel: Event | None,
) -> None:
    """Limpa um LOV do OPERA e confirma o valor após possível atualização ADF."""
    last_value = ""
    for _ in range(3):
        field = find_visible_any(tab, selectors, description, cancel, timeout=30)
        try:
            field.run_js(
                """
                const setter = Object.getOwnPropertyDescriptor(
                    HTMLInputElement.prototype, 'value'
                ).set;
                setter.call(this, '');
                this.removeAttribute('value');
                this.dispatchEvent(new Event('input', {bubbles: true}));
                this.dispatchEvent(new Event('change', {bubbles: true}));
                this.blur();
                """
            )
        except (ContextLostError, ElementLostError):
            pass
        sleep(FILTER_CLEAR_SETTLE_SECONDS)
        try:
            refreshed = find_visible_any(
                tab, selectors, description, cancel, timeout=30
            )
            last_value = str(refreshed.property("value") or "").strip()
        except (ContextLostError, ElementLostError):
            continue
        if not last_value:
            return
    raise RuntimeError(f"{description} não foi limpo; valor atual: {last_value!r}.")


def download_financial_payments(
    tab: Any,
    download_dir: Path,
    cancel: Event | None = None,
    *,
    run_date: date | None = None,
) -> Path:
    """Gera e baixa o Financial Payments referente ao dia anterior."""
    target_dir = download_dir.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    execution_date = run_date or date.today()
    report_date = execution_date - timedelta(days=1)

    open_reports_and_analytics(tab, cancel)

    report_name = find_visible_any(
        tab,
        REPORT_NAME_SELECTORS,
        "Campo Report Name",
        cancel,
        timeout=45,
    )
    report_name.input("CASH", clear=True)
    sleep(ACTION_SETTLE_SECONDS)

    report_actions = (
        (REPORT_SEARCH_SELECTORS, "Busca de relatórios", PAGE_SETTLE_SECONDS, 45),
        (
            FINANCIAL_PAYMENTS_SELECTORS,
            "Relatório Pagamentos Financeiros",
            PAGE_SETTLE_SECONDS,
            45,
        ),
        (EDIT_REPORT_SELECTORS, "Edição do relatório", PAGE_SETTLE_SECONDS, 45),
    )
    for selectors, description, settle_seconds, timeout in report_actions:
        click_visible_any(
            tab,
            selectors,
            description,
            cancel,
            settle_seconds=settle_seconds,
            timeout=timeout,
        )

    report_date_field = find_visible_any(
        tab,
        REPORT_DATE_SELECTORS,
        "Data do relatório",
        cancel,
        timeout=45,
    )
    formatted_report_date = report_date.strftime("%d/%m/%Y")
    report_date_field.input(formatted_report_date, clear=True)
    report_date_field.run_js("this.blur();")
    sleep(FILTER_CLEAR_SETTLE_SECONDS)
    report_date_field = find_visible_any(
        tab,
        REPORT_DATE_SELECTORS,
        "Data do relatório",
        cancel,
        timeout=45,
    )
    current_date = str(report_date_field.property("value") or "")
    if "".join(filter(str.isdigit, current_date)) != "".join(
        filter(str.isdigit, formatted_report_date)
    ):
        raise RuntimeError(
            f"O campo de data do OPERA não aceitou {formatted_report_date}."
        )

    for index, selectors in enumerate(FILTER_FIELD_SELECTORS, start=1):
        _clear_filter_field(
            tab,
            selectors,
            f"Campo de filtro {index}",
            cancel,
        )

    final_actions = (
        (GENERATE_REPORT_SELECTORS, "Geração do relatório", PAGE_SETTLE_SECONDS, 45),
        (REPORT_FORMAT_SELECTORS, "Formato do relatório", ACTION_SETTLE_SECONDS, 30),
    )
    for selectors, description, settle_seconds, timeout in final_actions:
        click_visible_any(
            tab,
            selectors,
            description,
            cancel,
            settle_seconds=settle_seconds,
            timeout=timeout,
        )

    mission = _start_report_download(tab, target_dir, report_date, cancel)
    downloaded_path = _wait_for_report_download(mission, cancel)
    if not downloaded_path.is_file():
        raise RuntimeError(
            f"O OPERA informou o download, mas o arquivo não existe: {downloaded_path}"
        )
    if not opera_xml_has_transactions(downloaded_path):
        raise RuntimeError(
            "O OPERA gerou um XML vazio. Confirme se Cashier e Transaction Code "
            "foram limpos e se a data do relatório está correta."
        )
    return downloaded_path


def run_opera_download(
    config: OperaLoginConfig,
    hotel_name: str,
    download_dir: Path,
    cancel: Event | None = None,
    *,
    browser_factory: Callable[[], Any] | None = None,
) -> Path:
    """Executa login, seleção do hotel e download, sempre fechando o navegador."""
    browser = (browser_factory or create_browser)()
    try:
        tab = login_opera(browser, config, cancel)
        select_hotel(tab, hotel_name, cancel)
        return download_financial_payments(tab, download_dir, cancel)
    finally:
        _quit_browser(browser)


def _quit_browser(browser: Any) -> None:
    """Fecha todas as janelas da instância exclusiva criada pela RPA."""
    try:
        browser.quit(timeout=1, force=False)
    except Exception:
        pass
