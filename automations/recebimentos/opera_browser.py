"""Acesso ao OPERA exclusivo da automação de conferência de recebimentos."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
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

OPERA_URL = (
    "https://mtcu7.oraclehospitality.us-ashburn-1.ocs.oraclecloud.com/"
    "CARMEL/operacloud/faces/opera-cloud-index/OperaCloud"
)

# Estes seletores são intencionalmente copiados da automação booking_opera.
# As automações permanecem independentes e não compartilham código ou configuração.
USERNAME_SELECTOR = 'xpath://*[@id="idcs-signin-basic-signin-form-username"]'
PASSWORD_SELECTOR = 'xpath://*[@id="idcs-signin-basic-signin-form-password|input"]'
LOGIN_BUTTON_SELECTOR = 'xpath://*[@id="idcs-signin-basic-signin-form-submit"]/button'
CONTINUE_BUTTON_SELECTOR = 'xpath://*[@id="ode_init_ovrdbtn"]'
PROFILE_SELECTOR = 'xpath://*[@id="pt1:oc_pg_pt:ode_pg_mnhdr_rght_cntnt_lnk"]'
CHANGE_LOCATION_SELECTOR = (
    "xpath:/html/body/div[1]/form/div/div[2]/div/table/tbody/tr[2]/td[2]/table/"
    "tbody/tr/td/div/div/div[2]/div/div[1]/div[1]/a/span"
)
HOTEL_INPUT_SELECTOR = 'xpath://*[@id="pt1:oc_pg_pt:pt_r1:0:pt1:oc_pnl_lstng_tmpl:oc_pnl_tmpl_323z8b:oc_pnl_lstng_vw_srch_swtchr:odec_srch_swtchr_advncd_sf:fe2:it1:odec_it_it::content"]'
HOTEL_SEARCH_SELECTOR = 'xpath://*[@id="pt1:oc_pg_pt:pt_r1:0:pt1:oc_pnl_lstng_tmpl:oc_pnl_tmpl_323z8b:oc_pnl_lstng_vw_srch_swtchr:odec_srch_swtchr_advncd_sf:odec_srch_swtchr_advncd_srch_btn"]'
HOTEL_RESULT_SELECTOR = 'xpath://*[@id="pt1:oc_pg_pt:pt_r1:0:ab1:odec_axn_br_axns_pstv_i:0:odec_axn_br_axn_pstv"]'
HOTEL_INPUT_SELECTORS = (
    HOTEL_INPUT_SELECTOR,
    'xpath://input[contains(@id, "oc_pnl_lstng_vw_srch_swtchr") and contains(@id, "odec_it_it::content")]',
    'xpath://input[contains(@id, "odec_srch_swtchr_advncd_sf") and @type="text"]',
)
HOTEL_SEARCH_SELECTORS = (
    HOTEL_SEARCH_SELECTOR,
    'xpath://*[contains(@id, "odec_srch_swtchr_advncd_srch_btn")]',
)
HOTEL_RESULT_SELECTORS = (
    HOTEL_RESULT_SELECTOR,
    'xpath://*[contains(@id, "odec_axn_br_axns_pstv_i:0") and contains(@id, "odec_axn_br_axn_pstv")]',
)
REPORTS_MENU_SELECTOR = 'xpath://*[@id="pt1:oc_pg_pt:dm1:odec_drpmn_mb_grp:7:odec_drpmn_mb_mn"]/div/table/tbody/tr/td[2]'
REPORTS_ANALYTICS_SELECTOR = 'xpath://*[@id="pt1:oc_pg_pt:dm1:odec_drpmn_mb_grp:7:odec_drpmn_mb_mn_grp:1:odec_drpmn_mb_mn_itm"]'
REPORT_NAME_SELECTOR = 'xpath://*[@id="pt1:oc_pg_pt:mainRegion:2:pt1:oc_pnl_lst_cmp:oc_scrn_pnl_lst_tmpl:oc_scrn_tmpl_by43sy:oc_pnl_lst_tmpl:oc_pnl_lstng_tmpl:oc_pnl_tmpl_by43sy:oc_pnl_lstng_vw_srch_swtchr:odec_srch_swtchr_advncd_sf:fe2:reportName:odec_it_it::content"]'
REPORT_NAME_ABSOLUTE_SELECTOR = "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[4]/span/span/div/div[2]/div/div/div[2]/span/div/div[2]/div/div[2]/div[2]/span/span/span[2]/span[2]/span/input"
REPORT_NAME_SELECTORS = (
    REPORT_NAME_ABSOLUTE_SELECTOR,
    REPORT_NAME_SELECTOR,
    'xpath://input[contains(@id, "reportName") and contains(@id, "::content")]',
    'xpath://label[normalize-space()="Report Name"]/following::input[1]',
)
REPORT_SEARCH_SELECTOR = 'xpath://*[@id="pt1:oc_pg_pt:mainRegion:2:pt1:oc_pnl_lst_cmp:oc_scrn_pnl_lst_tmpl:oc_scrn_tmpl_by43sy:oc_pnl_lst_tmpl:oc_pnl_lstng_tmpl:oc_pnl_tmpl_by43sy:oc_pnl_lstng_vw_srch_swtchr:odec_srch_swtchr_advncd_sf:odec_srch_swtchr_advncd_srch_btn"]'
REPORT_SEARCH_ABSOLUTE_SELECTOR = "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[4]/span/span/div/div[2]/div/div/div[3]/span/span[2]/div"
REPORT_SEARCH_SELECTORS = (
    REPORT_SEARCH_ABSOLUTE_SELECTOR,
    REPORT_SEARCH_SELECTOR,
    'xpath://button[normalize-space()="Search" or normalize-space()="Buscar"]',
)
FINANCIAL_PAYMENTS_SELECTOR = 'xpath://*[@id="pt1:oc_pg_pt:mainRegion:2:pt1:oc_pnl_lst_cmp:oc_scrn_pnl_lst_tmpl:oc_scrn_tmpl_by43sy:oc_pnl_lst_tmpl:oc_pnl_lstng_tmpl:oc_pnl_tmpl_by43sy:pc1:t1:3:c4"]'
FINANCIAL_PAYMENTS_ABSOLUTE_SELECTOR = "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[6]/span/span[1]/span/div/div/div/div/div/div[2]/div/div[2]/table/tbody/tr[4]/td[1]/div/table/tbody/tr/td[3]"
FINANCIAL_PAYMENTS_SELECTORS = (
    FINANCIAL_PAYMENTS_ABSOLUTE_SELECTOR,
    FINANCIAL_PAYMENTS_SELECTOR,
    'xpath://*[contains(normalize-space(), "Financial Payments") or contains(normalize-space(), "Pagamentos Financeiros")]',
)
EDIT_REPORT_SELECTOR = 'xpath://*[@id="pt1:oc_pg_pt:mainRegion:2:pt1:oc_pnl_lst_cmp:oc_scrn_pnl_lst_tmpl:oc_scrn_tmpl_by43sy:oc_pnl_lst_tmpl:oc_pnl_lstng_tmpl:oc_pnl_tmpl_by43sy:actionBar:odec_axn_br_axns_pstv_i:2:odec_axn_br_axn_pstv"]'
EDIT_REPORT_ABSOLUTE_SELECTOR = "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[7]/span/div/div/span/span/span[2]/span[1]/span/div[3]"
EDIT_REPORT_SELECTORS = (
    EDIT_REPORT_ABSOLUTE_SELECTOR,
    EDIT_REPORT_SELECTOR,
    'xpath://button[normalize-space()="Edit" or normalize-space()="Editar"]',
)
CALENDAR_SELECTOR = 'xpath://*[@id="pt1:oc_pg_pt:mainRegion:3:pt1:oc_pnl_cmp:oc_scrn_pnl_tmpl:oc_scrn_tmpl_2vf25c:oc_scrn_pnl_pnl:oc_pnl_tmpl_2vf25c:fe0:mdmprm_695718131:oc_mdm_rptpm_id1:odec_dt_it"]/button'
CALENDAR_ABSOLUTE_SELECTOR = "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[4]/span/span/span/div/div/div/div/span/div[2]/div[3]/div/div[2]/div[1]/span/span/span[2]/span[2]/span[1]/button"
CALENDAR_SELECTORS = (
    CALENDAR_ABSOLUTE_SELECTOR,
    CALENDAR_SELECTOR,
    'xpath://button[contains(@aria-label, "calendar") or contains(@title, "calendar") or contains(@aria-label, "calendário") or contains(@title, "calendário")]',
)
CURRENT_DAY_SELECTOR = "xpath:/html/body/div[5]/button"
CURRENT_DAY_SELECTORS = (
    CURRENT_DAY_SELECTOR,
    "xpath:/html/body/div[6]/button",
    'xpath://button[normalize-space()="Today" or normalize-space()="Hoje"]',
)
FILTER_FIELD_SELECTORS = (
    (
        "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[4]/span/span/span/div/div/div/div/span/div[3]/div[2]/div/div[2]/div[1]/span/span/span[2]/span[2]/span/span/input",
        'xpath://*[@id="pt1:oc_pg_pt:mainRegion:3:pt1:oc_pnl_cmp:oc_scrn_pnl_tmpl:oc_scrn_tmpl_2vf25c:oc_scrn_pnl_pnl:oc_pnl_tmpl_2vf25c:j_idt1217:mdmprm_695718131:oc_mdm_rptpm_lov1:odec_lov_itLovetext::content"]',
    ),
    (
        "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[4]/span/span/span/div/div/div/div/span/div[3]/div[2]/div/div[2]/div[2]/span/span/span[2]/span[2]/span/span/input",
        'xpath://*[@id="pt1:oc_pg_pt:mainRegion:3:pt1:oc_pnl_cmp:oc_scrn_pnl_tmpl:oc_scrn_tmpl_2vf25c:oc_scrn_pnl_pnl:oc_pnl_tmpl_2vf25c:j_idt1220:mdmprm_695718131:oc_mdm_rptpm_lov1:odec_lov_itLovetext::content"]',
    ),
)
GENERATE_REPORT_SELECTOR = 'xpath://*[@id="pt1:oc_pg_pt:mainRegion:3:pt1:oc_pnl_cmp:oc_scrn_pnl_tmpl:oc_scrn_tmpl_2vf25c:oc_scrn_pnl_pnl:oc_pnl_tmpl_2vf25c:actionBar:odec_axn_br_axns_pstv_i:0:odec_axn_br_axn_pstv"]'
GENERATE_REPORT_ABSOLUTE_SELECTOR = "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[5]/span/div/div/span/span/span[3]/span[1]/span/div[1]"
GENERATE_REPORT_SELECTORS = (
    GENERATE_REPORT_ABSOLUTE_SELECTOR,
    GENERATE_REPORT_SELECTOR,
)
REPORT_FORMAT_SELECTOR = 'xpath://*[@id="pt1:oc_pg_pt:mainRegion:3:pt1:oc_pnl_cmp:oc_scrn_pnl_tmpl:oc_scrn_tmpl_2vf25c:oc_scrn_pnl_pnl:oc_pnl_tmpl_2vf25c:fe8:sor1:odec_sor_sor::content"]/fieldset/div[3]/span/label'
REPORT_FORMAT_ABSOLUTE_SELECTOR = "xpath:/html/body/div[1]/form/div/div[2]/div[1]/div[1]/table/tbody/tr/td/div/div/table/tbody/tr[2]/td[2]/div/div[2]/div/div[2]/div/span/span/span[2]/span[2]/table/tbody/tr/td[2]/div/fieldset/div[3]/span/label"
REPORT_FORMAT_SELECTORS = (
    REPORT_FORMAT_ABSOLUTE_SELECTOR,
    REPORT_FORMAT_SELECTOR,
)
FINAL_DOWNLOAD_SELECTOR = 'xpath://*[@id="pt1:oc_pg_pt:mainRegion:3:pt1:oc_pnl_cmp:oc_scrn_pnl_tmpl:oc_scrn_tmpl_2vf25c:oc_scrn_pnl_pnl:oc_pnl_tmpl_2vf25c:ab3:odec_axn_br_axns_pstv_i:0:odec_axn_br_axn_pstv"]'
FINAL_DOWNLOAD_ABSOLUTE_SELECTOR = "xpath:/html/body/div[1]/form/div/div[2]/div[1]/div[1]/table/tbody/tr/td/div/div/table/tbody/tr[3]/td[2]/table/tbody/tr/td[1]/span/span[1]/span[2]/div"
FINAL_DOWNLOAD_SELECTORS = (
    FINAL_DOWNLOAD_ABSOLUTE_SELECTOR,
    FINAL_DOWNLOAD_SELECTOR,
)

POLL_INTERVAL = 0.25
ACTION_SETTLE_SECONDS = 0.25
PAGE_SETTLE_SECONDS = 0.75
RESULT_SETTLE_SECONDS = 0.75
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


def find_visible(
    tab: Any,
    selector: str,
    description: str,
    cancel: Event | None = None,
    timeout: int = 30,
) -> Any:
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        _checkpoint(cancel)
        try:
            elements = tab.eles(selector)
        except TRANSIENT_BROWSER_ERRORS:
            sleep(POLL_INTERVAL)
            continue
        for element in elements:
            try:
                if element.states.is_displayed:
                    return element
            except TRANSIENT_BROWSER_ERRORS:
                continue
        sleep(POLL_INTERVAL)
    raise RuntimeError(f"{description} não encontrado.")


def click_visible(
    tab: Any,
    selector: str,
    description: str,
    cancel: Event | None = None,
    *,
    settle_seconds: float = ACTION_SETTLE_SECONDS,
    timeout: int = 30,
) -> None:
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        _checkpoint(cancel)
        try:
            element = find_visible(tab, selector, description, cancel, timeout=5)
            element.scroll.to_see()
            sleep(ACTION_SETTLE_SECONDS)
            element.click()
            if settle_seconds:
                sleep(settle_seconds)
            return
        except TRANSIENT_BROWSER_ERRORS:
            sleep(POLL_INTERVAL)
    raise RuntimeError(f"{description} permaneceu sem dimensão.")


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
                elements = tab.eles(selector)
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
    while monotonic() < deadline:
        _checkpoint(cancel)
        try:
            element = find_visible_any(tab, selectors, description, cancel, timeout=5)
            element.scroll.to_see()
            sleep(ACTION_SETTLE_SECONDS)
            element.click()
            if settle_seconds:
                sleep(settle_seconds)
            return
        except (RuntimeError, *TRANSIENT_BROWSER_ERRORS):
            sleep(POLL_INTERVAL)
    raise RuntimeError(f"{description} não respondeu ao clique.")


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
            click_visible(
                tab,
                PROFILE_SELECTOR,
                "Perfil do OPERA",
                cancel,
                settle_seconds=PAGE_SETTLE_SECONDS,
                timeout=45,
            )
            click_visible(
                tab,
                CHANGE_LOCATION_SELECTOR,
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
        settle_seconds=RESULT_SETTLE_SECONDS,
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


def download_financial_payments(
    tab: Any,
    download_dir: Path,
    cancel: Event | None = None,
    *,
    run_date: date | None = None,
) -> Path:
    """Gera e baixa o relatório Financial Payments do dia corrente."""
    target_dir = download_dir.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    navigation = (
        (REPORTS_MENU_SELECTOR, "Menu Relatórios"),
        (REPORTS_ANALYTICS_SELECTOR, "Relatórios e análises"),
    )
    for selector, description in navigation:
        click_visible(
            tab,
            selector,
            description,
            cancel,
            settle_seconds=PAGE_SETTLE_SECONDS,
            timeout=45,
        )

    report_name = find_visible_any(
        tab,
        REPORT_NAME_SELECTORS,
        "Campo Report Name",
        cancel,
        timeout=45,
    )
    report_name.input("CASH", clear=True)
    sleep(ACTION_SETTLE_SECONDS)

    click_visible_any(
        tab,
        REPORT_SEARCH_SELECTORS,
        "Busca de relatórios",
        cancel,
        settle_seconds=PAGE_SETTLE_SECONDS,
        timeout=45,
    )
    click_visible_any(
        tab,
        FINANCIAL_PAYMENTS_SELECTORS,
        "Relatório Pagamentos Financeiros",
        cancel,
        settle_seconds=PAGE_SETTLE_SECONDS,
        timeout=45,
    )
    click_visible_any(
        tab,
        EDIT_REPORT_SELECTORS,
        "Edição do relatório",
        cancel,
        settle_seconds=PAGE_SETTLE_SECONDS,
        timeout=45,
    )
    click_visible_any(
        tab,
        CALENDAR_SELECTORS,
        "Calendário do relatório",
        cancel,
        settle_seconds=PAGE_SETTLE_SECONDS,
        timeout=45,
    )
    click_visible_any(
        tab,
        CURRENT_DAY_SELECTORS,
        "Dia corrente",
        cancel,
        settle_seconds=PAGE_SETTLE_SECONDS,
        timeout=30,
    )

    for index, selectors in enumerate(FILTER_FIELD_SELECTORS, start=1):
        field = find_visible_any(
            tab,
            selectors,
            f"Campo de filtro {index}",
            cancel,
            timeout=30,
        )
        field.input("", clear=True)

    click_visible_any(
        tab,
        GENERATE_REPORT_SELECTORS,
        "Geração do relatório",
        cancel,
        settle_seconds=PAGE_SETTLE_SECONDS,
        timeout=45,
    )
    click_visible_any(
        tab,
        REPORT_FORMAT_SELECTORS,
        "Formato do relatório",
        cancel,
        settle_seconds=ACTION_SETTLE_SECONDS,
        timeout=30,
    )

    report_date = run_date or date.today()
    mission = _start_report_download(tab, target_dir, report_date, cancel)
    downloaded = mission.wait(show=False, timeout=180, cancel_if_timeout=True)
    if not downloaded:
        raise RuntimeError(
            "O download do relatório OPERA não terminou em 180 segundos."
        )

    downloaded_path = Path(downloaded)
    if not downloaded_path.is_file():
        raise RuntimeError(
            f"O OPERA informou o download, mas o arquivo não existe: {downloaded_path}"
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
    browser = None
    try:
        browser = (browser_factory or create_browser)()
        tab = login_opera(browser, config, cancel)
        select_hotel(tab, hotel_name, cancel)
        return download_financial_payments(tab, download_dir, cancel)
    finally:
        if browser is not None:
            try:
                browser.quit()
            except Exception:
                pass
