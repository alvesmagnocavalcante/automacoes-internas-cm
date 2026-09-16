from __future__ import annotations

import os
import re
from collections.abc import Callable
from threading import Event
from time import monotonic, sleep
from typing import Any
from urllib.parse import urlsplit

from DrissionPage import Chromium, ChromiumOptions
from DrissionPage.errors import ContextLostError, ElementLostError, NoRectError

from automations.booking_opera.booking_selectors import (
    APPLY_COLUMNS_SCRIPT,
    BOOKING_PASSWORD_SELECTORS,
    BOOKING_REPORT_ROW_COUNT_SCRIPT,
    BOOKING_TABLE_SNAPSHOT_SCRIPT,
    BOOKING_USERNAME_SELECTORS,
    COLUMN_SELECTION_SCRIPT,
    OPEN_COLUMNS_PANEL_SCRIPT,
    SELECT_ALL_BOOKING_ROWS_SCRIPT,
)
from automations.booking_opera.booking_selectors import (
    COLUMN_BUTTON_XPATH as COLUMN_BUTTON_XPATH,
)
from automations.booking_opera.domain import checkpoint
from automations.booking_opera.models import AutomationCancelled, BookingConfig
from automations.booking_opera.opera_selectors import (
    BOOKINGS_SELECTOR,
    CHANGE_LOCATION_SELECTOR,
    CLOSE_RATE_SELECTORS,
    CONTINUE_BUTTON_SELECTOR,
    HOTEL_INPUT_SELECTORS,
    HOTEL_RESULT_SELECTORS,
    HOTEL_SEARCH_SELECTORS,
    LOGIN_BUTTON_SELECTOR,
    MANAGE_RESERVATION_SELECTOR,
    OPERA_RESULT_SIGNATURE_SCRIPT,
    PASSWORD_SELECTOR,
    PROFILE_SELECTOR,
    RATE_LINK_SELECTOR,
    RESERVATION_INPUT_SELECTOR,
    RESERVATIONS_SELECTOR,
    RESULT_COUNT_SELECTOR,
    SEARCH_BUTTON_SELECTOR,
    SEARCH_MODE_SELECTORS,
    TOTAL_VALUE_SELECTOR,
    USERNAME_SELECTOR,
)
from automations.booking_opera.opera_selectors import (
    CLOSE_RATE_SELECTOR as CLOSE_RATE_SELECTOR,
)
from automations.booking_opera.opera_selectors import (
    HOTEL_INPUT_SELECTOR as HOTEL_INPUT_SELECTOR,
)
from automations.booking_opera.opera_selectors import (
    HOTEL_RESULT_SELECTOR as HOTEL_RESULT_SELECTOR,
)
from automations.booking_opera.opera_selectors import (
    HOTEL_SEARCH_SELECTOR as HOTEL_SEARCH_SELECTOR,
)

POLL_INTERVAL = 0.25
ACTION_SETTLE_SECONDS = 0.25
PAGE_SETTLE_SECONDS = 0.75
RESULT_SETTLE_SECONDS = 0.75
TABLE_TIMEOUT = 60
TABLE_STABLE_SECONDS = 2.0
BOOKING_LOGIN_TIMEOUT = 60
BOOKING_REPORT_TIMEOUT = 60
BOOKING_REPORT_SETTLE_SECONDS = 1.5
BOOKING_REFRESH_RETRIES = 3
OPERA_ACTION_SETTLE_SECONDS = 0.25
OPERA_INPUT_SETTLE_SECONDS = 1.0
OPERA_DETAIL_SETTLE_SECONDS = 0.1
OPERA_CLOSE_SETTLE_SECONDS = 0.1
OPERA_BETWEEN_QUERIES_SECONDS = 0.1
OPERA_RESULT_TIMEOUT = 10
OPERA_RESULTS_STABLE_SECONDS = 0.5
OPERA_RESULT_COUNT_GRACE_SECONDS = 2.0
OPERA_QUERY_RETRIES = 3

TRANSIENT_BROWSER_ERRORS = (ContextLostError, ElementLostError, NoRectError)
OPERA_RETRYABLE_ERRORS = (*TRANSIENT_BROWSER_ERRORS, RuntimeError)


class BookingPageRefreshed(RuntimeError):
    """Signals that Booking invalidated the JavaScript execution context."""


def create_browser() -> Chromium:
    options = ChromiumOptions().auto_port()
    options.set_pref("credentials_enable_service", False)
    options.set_pref("profile.password_manager_enabled", False)
    options.set_argument("--disable-save-password-bubble")
    options.set_argument("--disable-features=PasswordManagerOnboarding,PasswordLeakDetection")
    options.set_argument("--window-size=1920,1080")
    headless = os.getenv("BOOKING_HEADLESS", "false").strip().casefold() not in {
        "0",
        "false",
        "no",
        "off",
    }
    if headless:
        options.set_argument("--headless=new")
    if headless and os.getenv("CI"):
        options.set_argument("--no-sandbox")
        options.set_argument("--disable-dev-shm-usage")
    return Chromium(options)


def find_visible(tab: Any, selector: str, description: str, cancel: Event | None = None, timeout: int = 30) -> Any:
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        checkpoint(cancel)
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
    by_js: bool = False,
    settle_seconds: float = ACTION_SETTLE_SECONDS,
    timeout: int = 30,
) -> None:
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        checkpoint(cancel)
        try:
            element = find_visible(tab, selector, description, cancel, timeout=5)
            if by_js:
                element.click(by_js=True)
            else:
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
    """Find the first visible element among stable and dynamic selectors."""

    deadline = monotonic() + timeout
    while monotonic() < deadline:
        checkpoint(cancel)
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
    settle_seconds: float = OPERA_ACTION_SETTLE_SECONDS,
    timeout: int = 30,
) -> None:
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        checkpoint(cancel)
        try:
            element = find_visible_any(
                tab, selectors, description, cancel, timeout=5
            )
            element.scroll.to_see()
            sleep(OPERA_ACTION_SETTLE_SECONDS)
            element.click()
            if settle_seconds:
                sleep(settle_seconds)
            return
        except (RuntimeError, *TRANSIENT_BROWSER_ERRORS):
            sleep(POLL_INTERVAL)
    raise RuntimeError(f"{description} não respondeu ao clique.")


def find_booking_field(
    browser: Chromium,
    selectors: tuple[str, ...],
    description: str,
    cancel: Event | None,
    timeout: int = BOOKING_LOGIN_TIMEOUT,
) -> tuple[Any, Any]:
    deadline = monotonic() + timeout
    tab = browser.latest_tab
    while monotonic() < deadline:
        checkpoint(cancel)
        tab = browser.latest_tab
        for selector in selectors:
            try:
                elements = tab.eles(selector)
                field = next(
                    (element for element in elements if element.states.is_displayed),
                    None,
                )
            except Exception:
                field = None
            if field:
                return tab, field
        sleep(POLL_INTERVAL)
    current_url = str(getattr(tab, "url", "indisponível"))
    parsed_url = urlsplit(current_url)
    safe_location = (
        f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
        if parsed_url.scheme and parsed_url.netloc
        else "indisponível"
    )
    raise RuntimeError(
        f"Campo de {description} da Booking não encontrado após {timeout}s. "
        f"Página atual: {safe_location}"
    )


def login_booking(browser: Chromium, config: BookingConfig, cancel: Event | None) -> None:
    tab = browser.latest_tab
    tab.get(config.booking_url)
    tab.wait.doc_loaded(timeout=60)
    sleep(PAGE_SETTLE_SECONDS)
    fields = (
        (BOOKING_USERNAME_SELECTORS, config.booking_username, "usuário"),
        (BOOKING_PASSWORD_SELECTORS, config.booking_password, "senha"),
    )
    for selectors, value, description in fields:
        checkpoint(cancel)
        tab, field = find_booking_field(
            browser, selectors, description, cancel
        )
        field.input(value, clear=True)
        sleep(ACTION_SETTLE_SECONDS)
        submit_button = field.ele("xpath:./ancestor::form//button[@type='submit']")
        if not submit_button:
            raise RuntimeError(
                f"Botão de envio do campo de {description} da Booking não encontrado."
            )
        try:
            submit_button.click()
        except NoRectError:
            submit_button.click(by_js=True)
        sleep(PAGE_SETTLE_SECONDS)
        tab.wait.doc_loaded(timeout=60)


def wait_booking_report_ready(
    tab: Any, cancel: Event | None, timeout: int = BOOKING_REPORT_TIMEOUT
) -> None:
    """Wait until the asynchronous Booking report is populated."""

    deadline = monotonic() + timeout
    while monotonic() < deadline:
        checkpoint(cancel)
        try:
            row_count = int(
                run_booking_js(tab, BOOKING_REPORT_ROW_COUNT_SCRIPT, cancel) or 0
            )
        except BookingPageRefreshed:
            row_count = 0
        except (TypeError, ValueError, RuntimeError):
            row_count = 0
        if row_count:
            sleep(BOOKING_REPORT_SETTLE_SECONDS)
            return
        sleep(POLL_INTERVAL)
    raise RuntimeError("Relatório de reservas da Booking não terminou de carregar.")


def run_booking_js(tab: Any, script: str, cancel: Event | None) -> Any:
    """Execute JavaScript and expose page refresh as a recoverable event."""

    checkpoint(cancel)
    try:
        return tab.run_js(script)
    except ContextLostError as error:
        raise BookingPageRefreshed(
            "A página da Booking foi atualizada durante a operação."
        ) from error


def open_columns_panel(
    tab: Any, cancel: Event | None, timeout: int = 30
) -> None:
    """Open the panel through the exact XPath without Drission DOM search."""

    deadline = monotonic() + timeout
    last_status = "not-found"
    while monotonic() < deadline:
        checkpoint(cancel)
        try:
            last_status = str(run_booking_js(tab, OPEN_COLUMNS_PANEL_SCRIPT, cancel))
        except BookingPageRefreshed:
            raise
        except RuntimeError as error:
            last_status = type(error).__name__
        if last_status == "clicked":
            sleep(PAGE_SETTLE_SECONDS)
            return
        sleep(POLL_INTERVAL)
    raise RuntimeError(
        "Botão de seleção das colunas da Booking não ficou disponível "
        f"({last_status})."
    )


def configure_columns(tab: Any, cancel: Event | None, timeout: int = 30) -> int:
    """Select the panel checkboxes and apply them without a fragile modal XPath."""

    deadline = monotonic() + timeout
    last_reason = "painel ainda não renderizado"
    while monotonic() < deadline:
        checkpoint(cancel)
        try:
            result = run_booking_js(tab, COLUMN_SELECTION_SCRIPT, cancel)
        except BookingPageRefreshed:
            raise
        except Exception as error:
            last_reason = type(error).__name__
            sleep(POLL_INTERVAL)
            continue
        if isinstance(result, dict):
            last_reason = str(result.get("reason", last_reason))
            if result.get("ready"):
                sleep(ACTION_SETTLE_SECONDS)
                if run_booking_js(tab, APPLY_COLUMNS_SCRIPT, cancel):
                    return int(result.get("changed", 0))
        sleep(POLL_INTERVAL)
    raise RuntimeError(
        "Painel de colunas da Booking não ficou pronto para aplicar "
        f"({last_reason})."
    )


def select_all_booking_rows(tab: Any, cancel: Event | None) -> int | None:
    checkpoint(cancel)
    value = run_booking_js(tab, SELECT_ALL_BOOKING_ROWS_SCRIPT, cancel)
    if value is None:
        raise RuntimeError("Seletor de quantidade de reservas não encontrado.")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def wait_for_booking_data(
    tab: Any,
    page_capacity: int | None,
    cancel: Event | None,
    *,
    clock: Callable[[], float] = monotonic,
    sleeper: Callable[[float], None] = sleep,
) -> tuple[list[str], list[list[str]]]:
    """Wait for stable data and extract it without Drission element searches."""

    deadline = clock() + TABLE_TIMEOUT
    previous_signature: tuple[tuple[str, ...], ...] | None = None
    stable_since = clock()
    while clock() < deadline:
        checkpoint(cancel)
        values = run_booking_js(tab, BOOKING_TABLE_SNAPSHOT_SCRIPT, cancel)
        if not isinstance(values, list) or len(values) != 2:
            sleeper(POLL_INTERVAL)
            continue
        raw_headers, raw_rows = values
        headers = [str(header).strip() for header in raw_headers]
        rows = [
            [str(value).replace("\xa0", " ") for value in row]
            for row in raw_rows
        ]
        signature = tuple(tuple(row) for row in rows)
        if rows and page_capacity is not None and len(rows) >= page_capacity:
            return headers, rows
        if rows and signature == previous_signature:
            if clock() - stable_since >= TABLE_STABLE_SECONDS:
                return headers, rows
        else:
            previous_signature = signature
            stable_since = clock()
        sleeper(POLL_INTERVAL)
    raise RuntimeError("A tabela de reservas não estabilizou dentro do prazo.")


def booking_table(browser: Chromium, cancel: Event | None) -> tuple[list[str], list[list[str]]]:
    for _attempt in range(BOOKING_REFRESH_RETRIES):
        tab = browser.latest_tab
        try:
            wait_booking_report_ready(tab, cancel)
            open_columns_panel(tab, cancel)
            configure_columns(tab, cancel)
            page_capacity = select_all_booking_rows(tab, cancel)
            headers, records = wait_for_booking_data(tab, page_capacity, cancel)
        except BookingPageRefreshed:
            sleep(PAGE_SETTLE_SECONDS)
            continue
        if not headers or not records:
            raise RuntimeError("A Booking não retornou reservas.")
        return headers, records
    raise RuntimeError(
        "A página da Booking foi atualizada repetidamente durante a extração."
    )


def login_opera(browser: Chromium, config: BookingConfig, cancel: Event | None) -> Any:
    tab = browser.latest_tab
    tab.get(config.opera_url)
    tab.wait.doc_loaded(timeout=60)
    sleep(PAGE_SETTLE_SECONDS)
    for selector, value, field_name in ((USERNAME_SELECTOR, config.opera_username, "usuário"), (PASSWORD_SELECTOR, config.opera_password, "senha")):
        checkpoint(cancel)
        field = tab.ele(selector, timeout=60)
        if not field:
            raise RuntimeError(f"Campo de {field_name} do OPERA não encontrado.")
        field.input(value, clear=True)
        sleep(ACTION_SETTLE_SECONDS)
    login_button = tab.ele(LOGIN_BUTTON_SELECTOR, timeout=30)
    if not login_button:
        raise RuntimeError("Botão de login do OPERA não encontrado.")
    login_button.click()
    sleep(PAGE_SETTLE_SECONDS)
    tab.wait.doc_loaded(timeout=60)
    continue_button = tab.ele(CONTINUE_BUTTON_SELECTOR, timeout=10)
    if continue_button:
        continue_button.scroll.to_see()
        sleep(ACTION_SETTLE_SECONDS)
        continue_button.click()
        sleep(PAGE_SETTLE_SECONDS)
        tab.wait.doc_loaded(timeout=60)
    find_visible(
        tab,
        PROFILE_SELECTOR,
        "Página inicial do OPERA",
        cancel,
        timeout=120,
    )
    return tab


def open_hotel_search(tab: Any, cancel: Event | None) -> Any:
    """Open OPERA's dynamic location panel and return its fresh input."""

    last_error: RuntimeError | None = None
    for _attempt in range(OPERA_QUERY_RETRIES):
        checkpoint(cancel)
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
            sleep(OPERA_ACTION_SETTLE_SECONDS)
    raise RuntimeError(
        "Janela de pesquisa do hotel/resort não abriu após "
        f"{OPERA_QUERY_RETRIES} tentativas: {last_error}"
    )


def select_hotel(tab: Any, hotel_name: str, cancel: Event | None) -> None:
    """Select the OPERA location before opening the reservation workflow."""

    field = open_hotel_search(tab, cancel)
    field.input(hotel_name.strip(), clear=True)
    sleep(OPERA_ACTION_SETTLE_SECONDS)
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


def open_reservations(tab: Any, cancel: Event | None) -> None:
    click_visible(tab, BOOKINGS_SELECTOR, "Menu Bookings", cancel)
    if not tab.wait.ele_displayed(RESERVATIONS_SELECTOR, timeout=30):
        raise RuntimeError("Menu Reservations não ficou visível.")
    click_visible(tab, RESERVATIONS_SELECTOR, "Menu Reservations", cancel)
    if not tab.wait.ele_displayed(MANAGE_RESERVATION_SELECTOR, timeout=30):
        raise RuntimeError("Opção Manage Reservation não ficou visível.")
    click_visible(tab, MANAGE_RESERVATION_SELECTOR, "Manage Reservation", cancel)
    tab.wait.doc_loaded(timeout=60)
    click_visible_any(
        tab,
        SEARCH_MODE_SELECTORS,
        "Busca simplificada em Manage Reservation",
        cancel,
    )


def wait_for_text(
    element: Any,
    description: str,
    cancel: Event | None,
    timeout: int = 15,
) -> str:
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        checkpoint(cancel)
        text = str(element.text or "").strip()
        if text:
            return text
        sleep(POLL_INTERVAL)
    raise RuntimeError(f"{description} não carregou conteúdo dentro do prazo.")


def find_visible_now(tab: Any, selector: str) -> Any | None:
    """Return a fresh visible element without waiting."""

    return next(iter(find_all_visible_now(tab, selector)), None)


def find_all_visible_now(tab: Any, selector: str) -> list[Any]:
    """Return a fresh snapshot of visible elements without implicit waits."""

    try:
        elements = tab.eles(selector, timeout=0)
    except TRANSIENT_BROWSER_ERRORS:
        return []
    visible = []
    for element in elements:
        try:
            if element.states.is_displayed:
                visible.append(element)
        except TRANSIENT_BROWSER_ERRORS:
            continue
    return visible


def click_opera_dynamic(
    tab: Any,
    selector: str,
    description: str,
    cancel: Event | None,
    *,
    settle_seconds: float = 0,
    timeout: int = 30,
) -> None:
    """Click a dynamic OPERA control without an unconditional scroll delay."""

    deadline = monotonic() + timeout
    while monotonic() < deadline:
        checkpoint(cancel)
        try:
            element = find_visible(
                tab, selector, description, cancel, timeout=5
            )
            try:
                element.click()
            except NoRectError:
                element.click(by_js=True)
            if settle_seconds:
                sleep(settle_seconds)
            return
        except TRANSIENT_BROWSER_ERRORS:
            sleep(POLL_INTERVAL)
    raise RuntimeError(f"{description} não respondeu ao clique.")


def click_opera_dynamic_any(
    tab: Any,
    selectors: tuple[str, ...],
    description: str,
    cancel: Event | None,
    *,
    settle_seconds: float = 0,
    timeout: int = 15,
) -> None:
    """Click the first visible dynamic OPERA control without implicit waits."""

    deadline = monotonic() + timeout
    while monotonic() < deadline:
        checkpoint(cancel)
        for selector in selectors:
            element = find_visible_now(tab, selector)
            if element is None:
                continue
            try:
                element.click()
            except NoRectError:
                element.click(by_js=True)
            if settle_seconds:
                sleep(settle_seconds)
            return
        sleep(POLL_INTERVAL)
    raise RuntimeError(f"{description} não respondeu ao clique.")


def opera_result_signature(tab: Any) -> str:
    """Return the visible result row contents without retaining DOM elements."""

    try:
        return str(tab.run_js(OPERA_RESULT_SIGNATURE_SCRIPT) or "").strip()
    except (AttributeError, *TRANSIENT_BROWSER_ERRORS):
        return ""


def wait_for_new_opera_result(
    tab: Any,
    previous: Any | None,
    cancel: Event | None,
    previous_signature: str = "",
    timeout: int = OPERA_RESULT_TIMEOUT,
) -> Any:
    """Wait until OPERA replaces the element or changes the result row."""

    deadline = monotonic() + timeout
    previous_invalidated = previous is None
    while monotonic() < deadline:
        checkpoint(cancel)
        current = find_visible_now(tab, RATE_LINK_SELECTOR)
        current_signature = opera_result_signature(tab) if current else ""
        if (
            current is not None
            and current_signature
            and current_signature != previous_signature
        ):
            return current
        if not previous_invalidated:
            try:
                previous_invalidated = (
                    not previous.states.is_alive
                    or not previous.states.is_displayed
                )
            except TRANSIENT_BROWSER_ERRORS:
                previous_invalidated = True
        if previous_invalidated:
            if current is not None:
                return current
        sleep(POLL_INTERVAL)
    raise RuntimeError("O resultado da nova reserva não terminou de carregar.")


def wait_for_stable_opera_rate_count(
    tab: Any,
    cancel: Event | None,
    timeout: int = OPERA_RESULT_TIMEOUT,
) -> int:
    """Wait until every OPERA result row has finished rendering."""

    deadline = monotonic() + timeout
    previous_count = 0
    stable_since = monotonic()
    while monotonic() < deadline:
        checkpoint(cancel)
        count = len(find_all_visible_now(tab, RATE_LINK_SELECTOR))
        expected_count = opera_result_count(tab)
        if count and count == previous_count:
            stable_for = monotonic() - stable_since
            if expected_count is None and stable_for >= OPERA_RESULTS_STABLE_SECONDS:
                return count
            if (
                expected_count is not None
                and count >= expected_count
                and stable_for >= OPERA_RESULTS_STABLE_SECONDS
            ):
                return expected_count or count
            if stable_for >= OPERA_RESULT_COUNT_GRACE_SECONDS:
                return count
        else:
            previous_count = count
            stable_since = monotonic()
        sleep(POLL_INTERVAL)
    raise RuntimeError("Os resultados da reserva não terminaram de carregar.")


def opera_result_count(tab: Any) -> int | None:
    """Read OPERA's own result counter, such as ``4 results``."""

    element = find_visible_now(tab, RESULT_COUNT_SELECTOR)
    if element is None:
        return None
    try:
        match = re.search(r"\d+", str(element.text or ""))
    except TRANSIENT_BROWSER_ERRORS:
        return None
    return int(match.group()) if match else None


def wait_for_opera_rate(
    tab: Any,
    index: int,
    cancel: Event | None,
    timeout: int = OPERA_RESULT_TIMEOUT,
) -> Any:
    """Reacquire a result link after OPERA rebuilds the results table."""

    deadline = monotonic() + timeout
    while monotonic() < deadline:
        checkpoint(cancel)
        rate_links = find_all_visible_now(tab, RATE_LINK_SELECTOR)
        if index < len(rate_links):
            return rate_links[index]
        sleep(POLL_INTERVAL)
    raise RuntimeError(f"Resultado {index + 1} da reserva não ficou disponível.")


def wait_for_opera_detail_closed(
    tab: Any,
    cancel: Event | None,
    timeout: int = OPERA_RESULT_TIMEOUT,
) -> None:
    """Wait until the previous rate detail is gone before clicking another row."""

    deadline = monotonic() + timeout
    while monotonic() < deadline:
        checkpoint(cancel)
        if find_visible_now(tab, TOTAL_VALUE_SELECTOR) is None:
            return
        sleep(POLL_INTERVAL)
    raise RuntimeError("O detalhe do resultado anterior não fechou dentro do prazo.")


def wait_for_opera_text(
    tab: Any,
    selector: str,
    description: str,
    cancel: Event | None,
    timeout: int = OPERA_RESULT_TIMEOUT,
) -> str:
    """Read dynamic OPERA text while reacquiring replaced elements."""

    deadline = monotonic() + timeout
    while monotonic() < deadline:
        checkpoint(cancel)
        element = find_visible_now(tab, selector)
        if element is not None:
            try:
                text = str(element.text or "").strip()
            except TRANSIENT_BROWSER_ERRORS:
                text = ""
            if text:
                return text
        sleep(POLL_INTERVAL)
    raise RuntimeError(f"{description} não carregou conteúdo dentro do prazo.")


def recover_opera_search(tab: Any, cancel: Event | None) -> None:
    """Best-effort return to the reservation search after a partial refresh."""

    checkpoint(cancel)
    try:
        click_opera_dynamic_any(
            tab,
            CLOSE_RATE_SELECTORS,
            "Fechar detalhes da tarifa",
            cancel,
            timeout=2,
        )
    except (RuntimeError, *TRANSIENT_BROWSER_ERRORS):
        pass
    sleep(OPERA_ACTION_SETTLE_SECONDS)
    try:
        find_visible(
            tab,
            RESERVATION_INPUT_SELECTOR,
            "Campo de pesquisa da reserva",
            cancel,
            timeout=15,
        )
    except RuntimeError:
        pass


def fill_opera_reservation(field: Any, reservation: str) -> None:
    """Replace the search value and commit it without typing control characters."""

    field.input(reservation, clear=True)
    field.run_js("this.blur();")


def _opera_total_once(
    tab: Any, reservation: str, cancel: Event | None
) -> str:
    checkpoint(cancel)
    previous_rate = find_visible_now(tab, RATE_LINK_SELECTOR)
    previous_signature = opera_result_signature(tab) if previous_rate else ""
    field = find_visible(
        tab,
        RESERVATION_INPUT_SELECTOR,
        "Campo de pesquisa da reserva",
        cancel,
        timeout=30,
    )
    fill_opera_reservation(field, reservation)
    sleep(OPERA_INPUT_SETTLE_SECONDS)
    click_opera_dynamic(
        tab,
        SEARCH_BUTTON_SELECTOR,
        "Botão de pesquisa",
        cancel,
        settle_seconds=0,
    )
    wait_for_new_opera_result(
        tab,
        previous_rate,
        cancel,
        previous_signature=previous_signature,
    )
    rate_count = wait_for_stable_opera_rate_count(tab, cancel)
    totals = []
    for index in range(rate_count):
        rate_link = wait_for_opera_rate(tab, index, cancel)
        try:
            rate_link.click()
        except NoRectError:
            rate_link.click(by_js=True)
        sleep(OPERA_DETAIL_SETTLE_SECONDS)
        try:
            totals.append(
                wait_for_opera_text(
                    tab,
                    TOTAL_VALUE_SELECTOR,
                    "Valor total da reserva",
                    cancel,
                )
            )
        except RuntimeError as error:
            raise RuntimeError(
                f"Resultado {index + 1}/{rate_count}: {error}"
            ) from error
        click_opera_dynamic_any(
            tab,
            CLOSE_RATE_SELECTORS,
            "Fechar detalhes da tarifa",
            cancel,
            settle_seconds=OPERA_CLOSE_SETTLE_SECONDS,
        )
        wait_for_opera_detail_closed(tab, cancel)
    find_visible(
        tab,
        RESERVATION_INPUT_SELECTOR,
        "Campo para uma nova consulta",
        cancel,
        timeout=30,
    )
    sleep(OPERA_BETWEEN_QUERIES_SECONDS)
    return "\n".join(totals)


def opera_total(tab: Any, reservation: str, cancel: Event | None) -> str:
    last_error: Exception | None = None
    for _attempt in range(OPERA_QUERY_RETRIES):
        try:
            return _opera_total_once(tab, reservation, cancel)
        except AutomationCancelled:
            raise
        except OPERA_RETRYABLE_ERRORS as error:
            last_error = error
            recover_opera_search(tab, cancel)
    raise RuntimeError(
        f"OPERA não estabilizou após {OPERA_QUERY_RETRIES} tentativas: "
        f"{last_error}"
    )
