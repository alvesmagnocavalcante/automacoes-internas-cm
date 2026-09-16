"""Seletores da interface CMFlex usados apenas na conferência de recebimentos."""

CMFLEX_URL = "https://carmel.cmerp.com.br/STS/Account/LogOn?returnUrl=%2FSTS"

USERNAME_SELECTOR = (
    "xpath:/html/body/div/section/div/div[1]/div[2]/div/form/div[1]/div/input"
)
PASSWORD_SELECTOR = (
    "xpath:/html/body/div/section/div/div[1]/div[2]/div/form/div[2]/div/input"
)
LOGIN_SELECTOR = (
    "xpath:/html/body/div/section/div/div[1]/div[2]/div/form/div[4]/div[2]/input"
)
COMPANY_SELECTOR = (
    "xpath:/html/body/div/section/div/div[1]/div[2]/div/form/div/fieldset/div[2]/select"
)
COMPANY_LOGIN_SELECTOR = (
    "xpath:/html/body/div/section/div/div[1]/div[2]/div/form/div/fieldset/p/input[2]"
)
ACCOUNTS_RECEIVABLE_SELECTOR = (
    "xpath:/html/body/div/section/div/div/div/div[3]/div/div[1]/div[8]"
)
QUERIES_SELECTOR = "xpath:/html/body/div[1]/div/form/header/div[2]/div[4]"
REPORTS_SELECTOR = "xpath:/html/body/div[1]/div/form/header/div[1]/div[4]/div[2]/div/div/div[2]/div[4]/ul/li/a"
OPERATIONAL_GROUPS_SELECTOR = (
    "xpath:/html/body/div[1]/div/form/div[8]/div[3]/table/tbody/tr[24]/td[1]/input"
)
DOCUMENT_ENTRIES_SELECTOR = (
    "xpath:/html/body/div[1]/div/form/div[8]/div[3]/table/tbody/tr[37]/td[2]/input"
)
START_DATE_SELECTOR = "xpath:/html/body/div[1]/div/form/div[8]/div[2]/div[1]/div[3]/div/table/tbody/tr/td[1]/span/input[1]"
END_DATE_SELECTOR = "xpath:/html/body/div[1]/div/form/div[8]/div[2]/div[1]/div[4]/div/table/tbody/tr/td[1]/span/input[1]"
START_DATE_SELECTORS = (
    'xpath://*[normalize-space(.)="Data de Lançamento Inicial"]/following::input[not(@type="hidden")][1]',
    'xpath://input[contains(translate(@id, "ABCDEFGHIJKLMNOPQRSTUVWXYZ_", "abcdefghijklmnopqrstuvwxyz"), "datalancamentoinicial") or contains(translate(@name, "ABCDEFGHIJKLMNOPQRSTUVWXYZ_", "abcdefghijklmnopqrstuvwxyz"), "datalancamentoinicial")]',
    START_DATE_SELECTOR,
)
END_DATE_SELECTORS = (
    'xpath://*[normalize-space(.)="Data de Lançamento Final"]/following::input[not(@type="hidden")][1]',
    'xpath://input[contains(translate(@id, "ABCDEFGHIJKLMNOPQRSTUVWXYZ_", "abcdefghijklmnopqrstuvwxyz"), "datalancamentofinal") or contains(translate(@name, "ABCDEFGHIJKLMNOPQRSTUVWXYZ_", "abcdefghijklmnopqrstuvwxyz"), "datalancamentofinal")]',
    END_DATE_SELECTOR,
)
GENERATE_REPORT_SELECTOR = "xpath:/html/body/div[1]/div/form/div[8]/div[6]/span/span"
DOWNLOAD_SELECTOR = 'xpath://*[@id="ctl00_ctl00_ctl00_placeHolderMain_mainWebCad_MenuAcoesFiltro_detached"]/ul/li/a[.//span[normalize-space(.)="Download dos Dados em Formato Excel"]]'
DOWNLOAD_SELECTORS = (
    DOWNLOAD_SELECTOR,
    "xpath:/html/body/div[1]/div/form/div[1]/ul/li[4]/a",
    'xpath://*[@id="ctl00_ctl00_ctl00_placeHolderMain_mainWebCad_MenuAcoesFiltro_detached"]/ul/li[4]/a',
    "xpath:/html/body/div[1]/div/form/div[1]/ul/li[4]/a/span",
)
