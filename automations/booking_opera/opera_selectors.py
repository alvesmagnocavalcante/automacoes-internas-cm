"""Seletores e scripts do OPERA para a automação de reservas."""

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
BOOKINGS_SELECTOR = 'xpath://*[@id="pt1:oc_pg_pt:dm1:odec_drpmn_mb_grp:1:odec_drpmn_mb_mn"]/div'
RESERVATIONS_SELECTOR = (
    'xpath://*[contains(@id, "odec_drpmn_mb_mn_si")]/td[2]'
    '[normalize-space(.)="Reservations"]'
)
MANAGE_RESERVATION_SELECTOR = (
    'xpath://*[contains(@id, "odec_drpmn_mb_mn_grp_itm") '
    'and normalize-space(.)="Manage Reservation"]'
)
SEARCH_MODE_SELECTOR = 'xpath://*[@id="pt1:oc_pg_pt:mainRegion:1:pt1:oc_srch_tmpl_167b9q:ode_bscrn_tmpl:oc_srch_swtchr:odec_srch_swtchr_advncd_sf:odec_srch_swtchr_advncd_swtch_lnk"]'
SEARCH_MODE_SELECTORS = (
    SEARCH_MODE_SELECTOR,
    'xpath://*[contains(@id, "odec_srch_swtchr_advncd_swtch_lnk")]',
)
RESERVATION_INPUT_SELECTOR = 'xpath://*[@id="pt1:oc_pg_pt:mainRegion:1:pt1:oc_srch_tmpl_167b9q:ode_bscrn_tmpl:oc_srch_swtchr:odec_srch_swtchr_bsc_ts:odec_ts_sbfrm:odec_ts_inpt::content"]'
SEARCH_BUTTON_SELECTOR = 'xpath://*[@id="pt1:oc_pg_pt:mainRegion:1:pt1:oc_srch_tmpl_167b9q:ode_bscrn_tmpl:oc_srch_swtchr:odec_srch_swtchr_bsc_ts:odec_ts_sbfrm:odec_ts_srch"]'
RATE_LINK_SELECTOR = 'xpath://*[contains(@id, "oc_srch_rslts_tbl_tmpl") and contains(@id, ":ca3:occ_crncy_amt_lnk::text")]'
RESULT_COUNT_SELECTOR = (
    "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/"
    "tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/span[5]/"
    "div/div/div/div/div/div[1]/div[5]/span/span[2]/span/div/div[2]/div/"
    "div[1]/div/div/table/tbody/tr/td[2]"
)
TOTAL_VALUE_SELECTOR = 'xpath://*[contains(@id, "oc_srch_rslts_tbl_tmpl") and contains(@id, ":CurrencyAmount245:occ_crncy_amt")]'
CLOSE_RATE_SELECTOR = 'xpath://*[contains(@id, "oc_srch_rslts_tbl_tmpl") and contains(@id, ":oc_pnl_axnbr:odec_axn_br_axns_pstv")]'
CLOSE_RATE_SELECTORS = (
    CLOSE_RATE_SELECTOR,
    'xpath://*[normalize-space()="Close" or normalize-space()="Fechar"]/'
    'ancestor-or-self::*[self::button or self::a or @role="button"][1]',
)
OPERA_RESULT_SIGNATURE_SCRIPT = r"""
const rates = Array.from(document.querySelectorAll(
    '[id*="oc_srch_rslts_tbl_tmpl"][id*="occ_crncy_amt_lnk"]'
));
const rate = rates.find(element => {
    const rect = element.getBoundingClientRect();
    const style = window.getComputedStyle(element);
    return rect.width > 0 && rect.height > 0 &&
        style.display !== 'none' && style.visibility !== 'hidden';
}) || rates[0];
let row = rate && rate.closest('tr');
let resultRow = row;
while (row) {
    const text = (row.innerText || '').replace(/\s+/g, ' ').trim();
    if (text.length >= 40) {
        resultRow = row;
        break;
    }
    const parentRow = row.parentElement && row.parentElement.closest('tr');
    if (!parentRow) break;
    resultRow = parentRow;
    row = parentRow;
}
return (resultRow && resultRow.innerText || '').replace(/\u00a0/g, ' ')
    .replace(/\s+/g, ' ').trim();
"""
