"""Seletores do OPERA usados apenas na conferência de recebimentos."""

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
REPORTS_MENU_SELECTORS = (
    'xpath://*[@id="pt1:oc_pg_pt:dm1:odec_drpmn_mb_grp:7:odec_drpmn_mb_mn"]/div/table/tbody/tr/td[2]',
    'xpath://td[normalize-space()="Reports" or normalize-space()="Relatórios"]',
)
# Em larguras menores o OPERA abre primeiro um painel com a linha "Reports >".
# A seta dessa linha precisa ser acionada para o submenu aparecer.
REPORTS_FLYOUT_SELECTORS = (
    'xpath://td[normalize-space()="Reports" or normalize-space()="Relatórios"]/following-sibling::td[1]',
    'xpath://td[normalize-space()="Reports" or normalize-space()="Relatórios"]',
)
REPORTS_ANALYTICS_SELECTORS = (
    'xpath://*[@id="pt1:oc_pg_pt:dm1:odec_drpmn_mb_grp:7:odec_drpmn_mb_mn_grp:1:odec_drpmn_mb_mn_itm"]',
    'xpath://*[self::a or self::td or self::span or self::div][normalize-space()="Reports and Analytics" or normalize-space()="Reports & Analytics" or normalize-space()="Relatórios e Análises"]',
)
REPORT_NAME_SELECTORS = (
    "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[4]/span/span/div/div[2]/div/div/div[2]/span/div/div[2]/div/div[2]/div[2]/span/span/span[2]/span[2]/span/input",
    'xpath://*[@id="pt1:oc_pg_pt:mainRegion:2:pt1:oc_pnl_lst_cmp:oc_scrn_pnl_lst_tmpl:oc_scrn_tmpl_by43sy:oc_pnl_lst_tmpl:oc_pnl_lstng_tmpl:oc_pnl_tmpl_by43sy:oc_pnl_lstng_vw_srch_swtchr:odec_srch_swtchr_advncd_sf:fe2:reportName:odec_it_it::content"]',
    'xpath://input[contains(@id, "reportName") and contains(@id, "::content")]',
    'xpath://label[normalize-space()="Report Name"]/following::input[1]',
)
REPORT_SEARCH_SELECTORS = (
    "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[4]/span/span/div/div[2]/div/div/div[3]/span/span[2]/div",
    'xpath://*[@id="pt1:oc_pg_pt:mainRegion:2:pt1:oc_pnl_lst_cmp:oc_scrn_pnl_lst_tmpl:oc_scrn_tmpl_by43sy:oc_pnl_lst_tmpl:oc_pnl_lstng_tmpl:oc_pnl_tmpl_by43sy:oc_pnl_lstng_vw_srch_swtchr:odec_srch_swtchr_advncd_sf:odec_srch_swtchr_advncd_srch_btn"]',
    'xpath://button[normalize-space()="Search" or normalize-space()="Buscar"]',
)
FINANCIAL_PAYMENTS_SELECTORS = (
    "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[6]/span/span[1]/span/div/div/div/div/div/div[2]/div/div[2]/table/tbody/tr[4]/td[1]/div/table/tbody/tr/td[3]",
    'xpath://*[@id="pt1:oc_pg_pt:mainRegion:2:pt1:oc_pnl_lst_cmp:oc_scrn_pnl_lst_tmpl:oc_scrn_tmpl_by43sy:oc_pnl_lst_tmpl:oc_pnl_lstng_tmpl:oc_pnl_tmpl_by43sy:pc1:t1:3:c4"]',
    'xpath://*[contains(normalize-space(), "Financial Payments") or contains(normalize-space(), "Pagamentos Financeiros")]',
)
EDIT_REPORT_SELECTORS = (
    "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[7]/span/div/div/span/span/span[2]/span[1]/span/div[3]",
    'xpath://*[@id="pt1:oc_pg_pt:mainRegion:2:pt1:oc_pnl_lst_cmp:oc_scrn_pnl_lst_tmpl:oc_scrn_tmpl_by43sy:oc_pnl_lst_tmpl:oc_pnl_lstng_tmpl:oc_pnl_tmpl_by43sy:actionBar:odec_axn_br_axns_pstv_i:2:odec_axn_br_axn_pstv"]',
    'xpath://button[normalize-space()="Edit" or normalize-space()="Editar"]',
)
REPORT_DATE_SELECTORS = (
    "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[4]/span/span/span/div/div/div/div/span/div[2]/div[3]/div/div[2]/div[1]/span/span/span[2]/span[2]/span[1]/input",
    'xpath://input[contains(@id, "mdmprm_695718131") and not(@type="hidden")]',
)

FILTER_FIELD_SELECTORS = (
    (
        "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[4]/span/span/span/div/div/div/div/span/div[3]/div[2]/div/div[2]/div[1]/span/span/span[2]/span[2]/span/span/input",
    ),
    (
        "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[4]/span/span/span/div/div/div/div/span/div[3]/div[2]/div/div[2]/div[2]/span/span/span[2]/span[2]/span/span/input",
    ),
)
GENERATE_REPORT_SELECTORS = (
    "xpath:/html/body/div[1]/form/span[2]/span[2]/span[2]/div[2]/table/tbody/tr/td[2]/div/div[1]/div[3]/div/div[2]/div/span[2]/span/div/div[5]/span/div/div/span/span/span[3]/span[1]/span/div[1]",
    'xpath://*[@id="pt1:oc_pg_pt:mainRegion:3:pt1:oc_pnl_cmp:oc_scrn_pnl_tmpl:oc_scrn_tmpl_2vf25c:oc_scrn_pnl_pnl:oc_pnl_tmpl_2vf25c:actionBar:odec_axn_br_axns_pstv_i:0:odec_axn_br_axn_pstv"]',
)
REPORT_FORMAT_SELECTORS = (
    "xpath:/html/body/div[1]/form/div/div[2]/div[1]/div[1]/table/tbody/tr/td/div/div/table/tbody/tr[2]/td[2]/div/div[2]/div/div[2]/div/span/span/span[2]/span[2]/table/tbody/tr/td[2]/div/fieldset/div[3]/span/label",
    'xpath://*[@id="pt1:oc_pg_pt:mainRegion:3:pt1:oc_pnl_cmp:oc_scrn_pnl_tmpl:oc_scrn_tmpl_2vf25c:oc_scrn_pnl_pnl:oc_pnl_tmpl_2vf25c:fe8:sor1:odec_sor_sor::content"]/fieldset/div[3]/span/label',
)
FINAL_DOWNLOAD_SELECTORS = (
    "xpath:/html/body/div[1]/form/div/div[2]/div[1]/div[1]/table/tbody/tr/td/div/div/table/tbody/tr[3]/td[2]/table/tbody/tr/td[1]/span/span[1]/span[2]/div",
    'xpath://*[@id="pt1:oc_pg_pt:mainRegion:3:pt1:oc_pnl_cmp:oc_scrn_pnl_tmpl:oc_scrn_tmpl_2vf25c:oc_scrn_pnl_pnl:oc_pnl_tmpl_2vf25c:ab3:odec_axn_br_axns_pstv_i:0:odec_axn_br_axn_pstv"]',
)
