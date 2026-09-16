"""Download do relatório de lançamentos no CMFlex."""

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
from DrissionPage.errors import BrowserConnectError, ElementLostError, NoRectError

from automations.recebimentos.cmflex_selectors import (
    ACCOUNTS_RECEIVABLE_SELECTOR,
    CMFLEX_URL,
    COMPANY_LOGIN_SELECTOR,
    COMPANY_SELECTOR,
    DOCUMENT_ENTRIES_SELECTOR,
    DOWNLOAD_SELECTORS,
    END_DATE_SELECTORS,
    GENERATE_REPORT_SELECTOR,
    LOGIN_SELECTOR,
    OPERATIONAL_GROUPS_SELECTOR,
    PASSWORD_SELECTOR,
    QUERIES_SELECTOR,
    REPORTS_SELECTOR,
    START_DATE_SELECTORS,
    USERNAME_SELECTOR,
)
from automations.recebimentos.cmflex_selectors import (
    DOWNLOAD_SELECTOR as DOWNLOAD_SELECTOR,
)
from automations.recebimentos.cmflex_selectors import (
    END_DATE_SELECTOR as END_DATE_SELECTOR,
)
from automations.recebimentos.cmflex_selectors import (
    START_DATE_SELECTOR as START_DATE_SELECTOR,
)

POLL_INTERVAL = 0.25
ACTION_DELAY = 2.0
PAGE_DELAY = 2.0
DOWNLOAD_START_TIMEOUT = 30
DOWNLOAD_SETTLE_SECONDS = 30
TRANSIENT_ERRORS = (ElementLostError, NoRectError)


class CMFlexAutomationCancelled(RuntimeError):
    """Indica cancelamento solicitado durante o RPA do CMFlex."""


@dataclass(frozen=True)
class CMFlexConfig:
    username: str
    password: str
    company: str = "MAGNA"
    url: str = CMFLEX_URL

    def validate(self) -> None:
        missing = [
            name
            for name, value in (
                ("usuário CMFlex", self.username),
                ("senha CMFlex", self.password),
                ("empresa CMFlex", self.company),
                ("URL CMFlex", self.url),
            )
            if not value.strip()
        ]
        if missing:
            raise ValueError("Preencha: " + ", ".join(missing))


def config_from_env(company: str | None = None) -> CMFlexConfig:
    load_dotenv()
    return CMFlexConfig(
        username=os.getenv("RECEBIMENTOS_CMFLEX_USERNAME")
        or os.getenv("CMFLEX_USERNAME", ""),
        password=os.getenv("RECEBIMENTOS_CMFLEX_PASSWORD")
        or os.getenv("CMFLEX_PASSWORD", ""),
        company=company
        or os.getenv("RECEBIMENTOS_CMFLEX_COMPANY")
        or os.getenv("CMFLEX_COMPANY", "MAGNA"),
        url=os.getenv("RECEBIMENTOS_CMFLEX_URL")
        or os.getenv("CMFLEX_URL")
        or CMFLEX_URL,
    )


def _browser_options() -> ChromiumOptions:
    options = ChromiumOptions().auto_port()
    options.set_argument("--window-size=1920,1080")
    options.set_pref("credentials_enable_service", False)
    options.set_pref("profile.password_manager_enabled", False)
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
        "O Chrome do CMFlex abriu, mas a conexão local falhou."
    ) from last_error


def _checkpoint(cancel: Event | None) -> None:
    if cancel is not None and cancel.is_set():
        raise CMFlexAutomationCancelled("Execução do CMFlex cancelada.")


def _element(tab: Any, selector: str, description: str, timeout: int = 45) -> Any:
    element = tab.ele(selector, timeout=timeout)
    if not element:
        raise RuntimeError(f"{description} não encontrado.")
    return element


def _element_any(
    tab: Any,
    selectors: tuple[str, ...],
    description: str,
    cancel: Event | None,
    timeout: int = 45,
) -> Any:
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        _checkpoint(cancel)
        for selector in selectors:
            try:
                element = tab.ele(selector, timeout=0)
                if element and _is_displayed(element):
                    return element
            except TRANSIENT_ERRORS:
                continue
        sleep(POLL_INTERVAL)
    raise RuntimeError(f"{description} não encontrado.")


def _is_displayed(element: Any) -> bool:
    """Aceita somente o controle visível, ignorando inputs auxiliares da máscara."""
    try:
        return bool(element.states.is_displayed)
    except AttributeError:
        return True
    except TRANSIENT_ERRORS:
        return False


def _click(
    tab: Any,
    selector: str,
    description: str,
    cancel: Event | None,
    *,
    delay: float = ACTION_DELAY,
) -> None:
    _checkpoint(cancel)
    element = _element(tab, selector, description)
    try:
        element.scroll.to_see()
        element.click()
    except NoRectError:
        element.click(by_js=True)
    sleep(delay)


def _select_company(select_element: Any, company: str) -> None:
    normalized = company.strip().casefold()
    options = list(select_element.select.options)
    option = next(
        (item for item in options if item.text.strip().casefold() == normalized), None
    )
    if option is None:
        option = next(
            (item for item in options if normalized in item.text.strip().casefold()),
            None,
        )
    if option is None:
        raise RuntimeError(f"Empresa CMFlex não encontrada: {company}.")
    select_element.select.by_option(option)


def _set_input_value(element: Any, value: str) -> None:
    """Define o valor e notifica componentes JS sem emitir comandos de teclado."""
    element.run_js(
        """
        const value = arguments[0];
        const setter = Object.getOwnPropertyDescriptor(
            HTMLInputElement.prototype, 'value'
        ).set;
        setter.call(this, '');
        setter.call(this, value);
        this.dispatchEvent(new Event('input', {bubbles: true}));
        this.dispatchEvent(new Event('change', {bubbles: true}));
        """,
        value,
    )


def login_cmflex(
    browser: Chromium,
    config: CMFlexConfig,
    cancel: Event | None = None,
) -> Any:
    """Autentica e seleciona a empresa no CMFlex."""
    config.validate()
    tab = browser.latest_tab
    tab.get(config.url)
    tab.wait.doc_loaded(timeout=60)

    for selector, value, description in (
        (USERNAME_SELECTOR, config.username, "Campo de usuário do CMFlex"),
        (PASSWORD_SELECTOR, config.password, "Campo de senha do CMFlex"),
    ):
        _checkpoint(cancel)
        _set_input_value(_element(tab, selector, description, 60), value)
        sleep(ACTION_DELAY)

    _click(tab, LOGIN_SELECTOR, "Botão Entrar do CMFlex", cancel, delay=PAGE_DELAY)
    tab.wait.doc_loaded(timeout=60)
    company_select = _element(tab, COMPANY_SELECTOR, "Seleção de empresa", 60)
    _select_company(company_select, config.company)
    sleep(ACTION_DELAY)
    _click(
        tab,
        COMPANY_LOGIN_SELECTOR,
        "Botão de acesso à empresa",
        cancel,
        delay=PAGE_DELAY,
    )
    tab.wait.doc_loaded(timeout=60)
    return tab


def _has_report_date_field(tab: Any) -> bool:
    for selector in (*START_DATE_SELECTORS, *END_DATE_SELECTORS):
        try:
            element = tab.ele(selector, timeout=0)
            if element and _is_displayed(element):
                return True
        except TRANSIENT_ERRORS:
            continue
    return False


def _wait_report_tab(
    browser: Chromium,
    source_tab: Any,
    previous_tab_ids: set[str],
    cancel: Event | None,
    timeout: int = 60,
) -> Any:
    deadline = monotonic() + timeout
    source_id = getattr(source_tab, "tab_id", None)
    while monotonic() < deadline:
        _checkpoint(cancel)
        new_tab_ids = [
            tab_id for tab_id in browser.tab_ids if tab_id not in previous_tab_ids
        ]
        if new_tab_ids:
            return browser.get_tab(new_tab_ids[0])

        latest_tab = browser.latest_tab
        if getattr(latest_tab, "tab_id", None) != source_id:
            return latest_tab
        if _has_report_date_field(source_tab):
            return source_tab
        sleep(POLL_INTERVAL)
    raise RuntimeError(
        "O relatório Lançamentos de Documentos não abriu em uma nova aba "
        "nem na aba atual."
    )


def open_document_entries_report(
    browser: Chromium,
    tab: Any,
    cancel: Event | None = None,
) -> Any:
    """Navega até Lançamentos de Documentos e retorna sua nova aba."""
    for selector, description, delay in (
        (ACCOUNTS_RECEIVABLE_SELECTOR, "Contas a Receber", PAGE_DELAY),
        (QUERIES_SELECTOR, "Menu Consultas", ACTION_DELAY),
        (REPORTS_SELECTOR, "Visualizar Relatórios", PAGE_DELAY),
        (OPERATIONAL_GROUPS_SELECTOR, "Grupos Operacionais", ACTION_DELAY),
    ):
        _click(tab, selector, description, cancel, delay=delay)

    previous_tab_ids = set(browser.tab_ids)
    _click(
        tab,
        DOCUMENT_ENTRIES_SELECTOR,
        "Relatório Lançamentos de Documentos",
        cancel,
        delay=0,
    )
    report_tab = _wait_report_tab(browser, tab, previous_tab_ids, cancel)
    report_tab.wait.doc_loaded(timeout=60)
    sleep(PAGE_DELAY)
    return report_tab


def _wait_download(mission: Any, cancel: Event | None, timeout: int = 120) -> Path:
    deadline = monotonic() + timeout
    while not mission.is_done:
        _checkpoint(cancel)
        if monotonic() >= deadline:
            mission.cancel()
            raise RuntimeError(
                f"O download do CMFlex não terminou em {timeout} segundos."
            )
        sleep(0.1)
    if not mission.final_path:
        raise RuntimeError(
            f"O download do CMFlex terminou com estado {mission.state!r}."
        )
    return Path(mission.final_path)


def _date_value_matches(element: Any, expected: str) -> bool:
    """Compara datas ignorando os separadores aplicados pela máscara do campo."""
    current = str(element.property("value") or element.attr("value") or "")
    return "".join(filter(str.isdigit, current)) == "".join(
        filter(str.isdigit, expected)
    )


def _fill_date(element: Any, value: str, description: str) -> None:
    """Digita a data para atualizar também o estado interno da máscara."""
    element.run_js("this.value = ''; this.focus();")
    element.input(value)
    element.run_js("this.blur();")
    sleep(ACTION_DELAY)
    if not _date_value_matches(element, value):
        raise RuntimeError(f"{description} não aceitou a data {value}.")


def download_document_entries(
    tab: Any,
    download_dir: Path,
    cancel: Event | None = None,
    *,
    run_date: date | None = None,
) -> Path:
    """Preenche o dia corrente e baixa Lançamentos de Documentos."""
    execution_date = run_date or date.today()
    report_date = execution_date - timedelta(days=1)
    formatted_date = report_date.strftime("%d/%m/%Y")
    for selectors, description in (
        (START_DATE_SELECTORS, "Data de Lançamento Inicial"),
        (END_DATE_SELECTORS, "Data de Lançamento Final"),
    ):
        _fill_date(
            _element_any(tab, selectors, description, cancel, 60),
            formatted_date,
            description,
        )

    _click(
        tab,
        GENERATE_REPORT_SELECTOR,
        "Geração do relatório CMFlex",
        cancel,
        delay=ACTION_DELAY,
    )

    target_dir = download_dir.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    button = _element_any(
        tab,
        DOWNLOAD_SELECTORS,
        "Ação de download",
        cancel,
        60,
    )
    try:
        clicked_at = monotonic()
        mission = button.click.to_download(
            save_path=target_dir,
            rename=f"cmflex_recebimentos_{report_date:%Y-%m-%d}",
            new_tab=False,
            by_js=True,
            timeout=DOWNLOAD_START_TIMEOUT,
        )
    except TRANSIENT_ERRORS as error:
        raise RuntimeError("O botão de download do CMFlex foi invalidado.") from error
    if not mission:
        raise RuntimeError(
            f"O download do CMFlex não iniciou em {DOWNLOAD_START_TIMEOUT} segundos."
        )

    downloaded = _wait_download(mission, cancel)
    remaining = DOWNLOAD_SETTLE_SECONDS - (monotonic() - clicked_at)
    if remaining > 0:
        sleep(remaining)
    _checkpoint(cancel)
    if not downloaded.is_file():
        raise RuntimeError(
            f"O CMFlex informou o download, mas o arquivo não existe: {downloaded}"
        )
    return downloaded


def run_cmflex_download(
    config: CMFlexConfig,
    download_dir: Path,
    cancel: Event | None = None,
    *,
    browser_factory: Callable[[], Any] | None = None,
) -> Path:
    """Executa o fluxo completo do CMFlex e sempre fecha o navegador."""
    config.validate()
    browser = (browser_factory or create_browser)()
    report_tab = None
    try:
        tab = login_cmflex(browser, config, cancel)
        report_tab = open_document_entries_report(browser, tab, cancel)
        return download_document_entries(report_tab, download_dir, cancel)
    finally:
        if report_tab is not None:
            try:
                report_tab.close()
            except (AttributeError, TRANSIENT_ERRORS):
                pass
        try:
            browser.quit(timeout=1, force=False)
        except Exception:
            pass
