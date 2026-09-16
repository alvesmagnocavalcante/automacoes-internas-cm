"""Seletores e scripts da interface Booking para a automação de reservas."""

BOOKING_USERNAME_SELECTORS = (
    "#loginname",
    'css:input[name="loginname"]',
    'css:input[name="username"]',
    'css:input[type="email"]',
    'css:input[autocomplete="username"]',
)
BOOKING_PASSWORD_SELECTORS = (
    "#password",
    'css:input[name="password"]',
    'css:input[type="password"]',
    'css:input[autocomplete="current-password"]',
)
COLUMN_BUTTON_XPATH = (
    "/html/body/div[1]/div/div[2]/div/div/div/main/div/div/"
    "div[2]/div[2]/div[2]/span/button"
)
OPEN_COLUMNS_PANEL_SCRIPT = f"""
const button = document.evaluate(
    {COLUMN_BUTTON_XPATH!r}, document, null,
    XPathResult.FIRST_ORDERED_NODE_TYPE, null
).singleNodeValue;
if (!button) return 'not-found';
const style = window.getComputedStyle(button);
const rect = button.getBoundingClientRect();
if (style.display === 'none' || style.visibility === 'hidden' ||
        rect.width <= 0 || rect.height <= 0) return 'not-visible';
if (button.disabled || button.getAttribute('aria-disabled') === 'true')
    return 'disabled';
button.scrollIntoView({{block: 'center', inline: 'center'}});
button.click();
return 'clicked';
"""
BOOKING_REPORT_ROW_COUNT_SCRIPT = """
return Array.from(document.querySelectorAll('table'))
    .filter(table => {
        const rect = table.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    })
    .reduce((count, table) => Math.max(
        count, table.querySelectorAll('tbody > tr').length
    ), 0);
"""
SELECT_ALL_BOOKING_ROWS_SCRIPT = """
const select = document.querySelector(
    'select[aria-label="itemsPerPageDisplayed"]'
);
if (!select || !select.options.length) return null;
const value = select.options[select.options.length - 1].value;
const setter = Object.getOwnPropertyDescriptor(
    HTMLSelectElement.prototype, 'value'
).set;
setter.call(select, value);
select.dispatchEvent(new Event('input', {bubbles: true}));
select.dispatchEvent(new Event('change', {bubbles: true}));
return value;
"""
BOOKING_TABLE_SNAPSHOT_SCRIPT = r"""
const clean = value => (value || '').replace(/\u00a0/g, ' ').trim();
const tables = Array.from(document.querySelectorAll('table')).filter(table => {
    const rect = table.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0 &&
        table.querySelectorAll('tbody > tr').length > 0;
});
const table = tables.find(candidate => {
    const headers = Array.from(candidate.querySelectorAll('thead th'))
        .map(cell => clean(cell.innerText).toLowerCase());
    return headers.some(header =>
        header.includes('book number') ||
        header.includes('booking number') ||
        header.includes('número da reserva') ||
        header.includes('numero da reserva')
    );
}) || tables[0];
if (!table) return [[], []];
const headers = Array.from(table.querySelectorAll('thead th'))
    .map(cell => clean(cell.innerText));
const rows = Array.from(table.querySelectorAll('tbody > tr')).map(row =>
    Array.from(row.querySelectorAll('td')).map(cell => {
        const checkbox = cell.querySelector('input[type="checkbox"]');
        return checkbox ? (checkbox.checked ? 'Sim' : 'Não')
            : clean(cell.innerText);
    })
);
return [headers, rows];
"""
COLUMN_SELECTION_SCRIPT = r"""
const normalizeText = value => (value || '').replace(/\s+/g, ' ')
    .trim().toLowerCase();
const isVisible = element => {
    const style = window.getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' &&
        rect.width > 0 && rect.height > 0;
};
const hasApplyLabel = element => [
    element.innerText,
    element.textContent,
    element.value,
    element.getAttribute('aria-label'),
    element.getAttribute('title')
].some(value => {
    const label = normalizeText(value);
    return label === 'apply' || label === 'aplicar' ||
        label.startsWith('apply ') || label.startsWith('aplicar ');
});
const applyLabel = Array.from(document.querySelectorAll('body *'))
    .reverse()
    .find(element => isVisible(element) && hasApplyLabel(element));
const apply = applyLabel && (
    applyLabel.closest(
        'button, [role="button"], input[type="button"], input[type="submit"]'
    ) || applyLabel
);
if (!apply) return {ready: false, reason: 'apply-not-found'};

let panel = apply.parentElement;
let controls = [];
while (panel && panel !== document.body) {
    const inputs = Array.from(
        panel.querySelectorAll('input[type="checkbox"]')
    );
    const roles = Array.from(panel.querySelectorAll('[role="checkbox"]'));
    controls = inputs.length ? inputs : roles;
    if (controls.length) break;
    panel = panel.parentElement;
}
if (!controls.length) return {ready: false, reason: 'checkboxes-not-found'};

let changed = 0;
for (const control of controls) {
    const disabled = Boolean(control.disabled) ||
        control.getAttribute('aria-disabled') === 'true';
    const checked = Boolean(control.checked) ||
        control.getAttribute('aria-checked') === 'true';
    if (!disabled && !checked) {
        control.click();
        changed += 1;
    }
}
return {ready: true, total: controls.length, changed};
"""
APPLY_COLUMNS_SCRIPT = r"""
const normalizeText = value => (value || '').replace(/\s+/g, ' ')
    .trim().toLowerCase();
const hasApplyLabel = element => [
    element.innerText,
    element.textContent,
    element.value,
    element.getAttribute('aria-label'),
    element.getAttribute('title')
].some(value => {
    const label = normalizeText(value);
    return label === 'apply' || label === 'aplicar' ||
        label.startsWith('apply ') || label.startsWith('aplicar ');
});
const isVisible = element => {
    const style = window.getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' &&
        rect.width > 0 && rect.height > 0;
};
const applyLabel = Array.from(document.querySelectorAll('body *'))
    .reverse()
    .find(element => isVisible(element) && hasApplyLabel(element));
const apply = applyLabel && (
    applyLabel.closest(
        'button, [role="button"], input[type="button"], input[type="submit"]'
    ) || applyLabel
);
if (!apply) return false;
apply.click();
return true;
"""
