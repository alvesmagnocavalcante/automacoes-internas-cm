# Automações Internas CM

Repositório centralizado para desenvolvimento e execução de automações internas
por meio do GitHub Actions, utilizando runners Windows `self-hosted`.

Cada automação possui código, testes, configurações e workflow independentes. O
arquivo `main.py` funciona como ponto único de entrada e direciona a execução
para a automação solicitada.

## Automações disponíveis

| Identificador | Descrição |
| --- | --- |
| `booking-opera` | Conciliação de reservas e valores entre Booking e OPERA. |
| `conferencia-recebimentos` | Conferência diária entre OPERA, CMFlex e Rede. |

Para consultar a lista pelo terminal:

```powershell
uv run python main.py --list
```

## Estrutura do projeto

```text
.
├── .github/workflows/          # Workflows do GitHub Actions
│   ├── booking-opera.yml
│   └── conferencia-recebimentos.yml
├── automations/
│   ├── base.py                 # Contrato comum das automações
│   ├── registry.py             # Registro central de automações
│   ├── booking_opera/          # Conciliação Booking × OPERA
│   └── recebimentos/           # Conferência OPERA, CMFlex e Rede
├── tests/
│   ├── booking_opera/
│   └── recebimentos/
├── main.py                     # Ponto de entrada
├── pyproject.toml              # Projeto e dependências Python
└── uv.lock                     # Versões fixadas das dependências
```

Nos dois projetos, `service.py` coordena a execução, `domain.py` concentra a
lógica de conferência e `cli.py` mantém a entrada por linha de comando. Os
fluxos de navegação continuam em `browser.py` (Booking × OPERA) e em
`opera_browser.py`/`cmflex_browser.py` (recebimentos). Seus seletores e scripts
de página ficam em arquivos `*_selectors.py` próprios de cada automação;
nenhuma delas importa os seletores da outra.

## Execução local

### Requisitos

- Python 3.12;
- `uv`;
- Chrome ou Chromium compatível;
- acesso aos sistemas Booking e OPERA;
- VPN ativa, quando exigida pelo ambiente.

Instale as dependências:

```powershell
uv sync --frozen
```

Configure as variáveis de ambiente com base em `.env.example` e execute:

```powershell
uv run python main.py booking-opera --output-dir output
```

O identificador da automação é obrigatório. Executar `python main.py` sem um
identificador exibe as opções disponíveis e encerra com código de erro.

### Conferência de recebimentos

Para testar somente o login, a seleção do hotel e o download do relatório
Pagamentos Financeiros do OPERA, preencha `RECEBIMENTOS_OPERA_USERNAME`,
`RECEBIMENTOS_OPERA_PASSWORD` e `RECEBIMENTOS_OPERA_HOTEL` no `.env` e execute:

```powershell
uv run python main.py conferencia-recebimentos --baixar-opera
```

O navegador é fechado ao final e o arquivo é salvo em `output/recebimentos`.
Para baixar o relatório de Lançamentos de Documentos do CMFlex:

```powershell
uv run python main.py conferencia-recebimentos --baixar-cmflex
```

A empresa padrão é `MAGNA` e pode ser alterada com `--empresa-cmflex` ou
`RECEBIMENTOS_CMFLEX_COMPANY`. Para executar somente a conferência com os três
arquivos já baixados:

```powershell
uv run python main.py conferencia-recebimentos `
  --opera "opera.xml" `
  --cmflex "cmflex.xlsx" `
  --rede "venda-rede.xlsx"
```

O relatório do OPERA pode estar em XML ou XLSX. Fora do modo diário, o resultado
detalhado é salvo em `output/conferencia_recebimentos.json`. A conferência usa a
Rede como fonte principal para cartões e compara valores individuais ou somas de
lançamentos do OPERA. Dinheiro e Pix usam o número da transação, valores a
faturar usam o número do fólio e depósitos usam o total diário. Valores positivos
no relatório do OPERA são tratados como estornos.

Para localizar automaticamente a planilha Rede do dia anterior, baixar OPERA e
CMFlex quando ainda não estiverem disponíveis, conferir e arquivar os arquivos
no padrão `MM - MÊS/DD`, configure
`RECEBIMENTOS_REDE_DIR` e, opcionalmente, `RECEBIMENTOS_ARCHIVE_ROOT`:

```powershell
uv run python main.py conferencia-recebimentos --conferir-baixados
```

Cada pasta diária contém somente `Opera Magna DD.MM.xlsx`,
`CmFlex Magna DD.MM.xlsx` e `Rede Magna DD.MM.xlsx`. Os valores conciliados são
marcados nos próprios relatórios, seguindo o padrão das planilhas conferidas
manualmente. O XML baixado do OPERA é convertido para Excel nessa etapa.

## GitHub Actions e runner local

Os workflows ficam em `.github/workflows/booking-opera.yml` e
`.github/workflows/conferencia-recebimentos.yml`. Ambos usam exclusivamente um
runner com os rótulos:

```text
self-hosted, windows, x64
```

### Configuração do runner

1. Acesse **Settings → Actions → Runners** no repositório.
2. Adicione e configure um runner Windows.
3. Instale Chrome ou Chromium na máquina responsável pela execução.
4. Inicie o runner por `run.cmd` na sessão do usuário que acompanhará a
   automação.
5. Mantenha a máquina ligada, a sessão do usuário ativa e as conexões de rede ou
   VPN disponíveis.

Como a automação utiliza um navegador visível, o runner não deve ser executado
como serviço do Windows.

Os workflows definem `UV_SYSTEM_CERTS=true` para que o `uv` confie no repositório
de certificados do Windows, inclusive em redes com certificado corporativo.

## Configuração da Booking × OPERA

Cadastre os seguintes secrets em
**Settings → Secrets and variables → Actions**:

| Secret | Finalidade |
| --- | --- |
| `BOOKING_USERNAME` | Usuário Booking da Magna (configuração existente). |
| `BOOKING_PASSWORD` | Senha Booking da Magna (configuração existente). |
| `OPERA_USERNAME` | Usuário de acesso ao OPERA. |
| `OPERA_PASSWORD` | Senha de acesso ao OPERA. |
| `OPERA_HOTEL` | Hotel da Magna no OPERA (configuração existente). |

A execução manual está disponível em
**Actions → Conciliação Booking x OPERA → Run workflow**.

O agendamento permanece desabilitado no workflow; a execução atual é manual.

O workflow confere `CHARME`, `WIND` e `MAGNA` nessa ordem, sem executar duas
empresas ao mesmo tempo. Antes de abrir o navegador, valida as credenciais e o
hotel OPERA das três; se uma conferência falhar, as seguintes não começam.
O mesmo usuário e senha `OPERA_USERNAME`/`OPERA_PASSWORD` são usados em todas.

| Empresa | Secrets de acesso Booking | Configuração do hotel no OPERA |
| --- | --- | --- |
| Magna | `BOOKING_USERNAME` e `BOOKING_PASSWORD` existentes, ou o par `BOOKING_MAGNA_USERNAME`/`BOOKING_MAGNA_PASSWORD` | `OPERA_HOTEL` existente, ou `OPERA_HOTEL_MAGNA` |
| Charme | `BOOKING_CHARME_USERNAME` e `BOOKING_CHARME_PASSWORD` | `OPERA_HOTEL_CHARME` |
| Wind | `BOOKING_WIND_USERNAME` e `BOOKING_WIND_PASSWORD` | `OPERA_HOTEL_WIND` |

Cadastre os nomes dos hotéis como **Secrets** do repositório, assim como o
`OPERA_HOTEL` já existente. Acarizinho está previsto por
`BOOKING_ACARIZINHO_USERNAME`, `BOOKING_ACARIZINHO_PASSWORD` e
`OPERA_HOTEL_ACARIZINHO`, mas não participa da execução conjunta até que suas
credenciais estejam disponíveis. Para conferir uma única empresa, use
`uv run python main.py booking-opera --company CHARME`; sem `--company` nem
`--all-companies`, o comando local mantém o comportamento anterior.

Para salvar também o Excel final em uma pasta escolhida por você, cadastre a
Variable `BOOKING_ARCHIVE_DIR` em **Settings → Secrets and variables → Actions**
com o caminho dessa pasta. O caminho deve ser acessível pelo runner que executa
o workflow (no webtop, use um caminho Linux ou um volume montado). Na execução
conjunta, cada empresa recebe sua própria subpasta nessa raiz. A cópia recebe
data e hora no nome para preservar execuções anteriores; os arquivos em
`output/<empresa>/` e o artefato do Actions permanecem disponíveis. Sem a
Variable, não há cópia adicional. Localmente, também é possível usar
`--archive-dir`.

## Configuração da conferência de recebimentos

Cadastre secrets exclusivos para esta automação:

| Secret | Finalidade |
| --- | --- |
| `RECEBIMENTOS_OPERA_USERNAME` | Usuário do OPERA. |
| `RECEBIMENTOS_OPERA_PASSWORD` | Senha do OPERA. |
| `RECEBIMENTOS_OPERA_HOTEL` | Nome exato do hotel ou resort. |
| `RECEBIMENTOS_CMFLEX_USERNAME` | Usuário do CMFlex. |
| `RECEBIMENTOS_CMFLEX_PASSWORD` | Senha do CMFlex. |
| `RECEBIMENTOS_REDE_DIR` | Pasta onde o setor disponibiliza a planilha Rede. |
| `RECEBIMENTOS_ARCHIVE_ROOT` | Raiz das pastas mensais e diárias; opcional, padrão `output/recebimentos/conferencias`. |

A execução manual está em
**Actions → Conferência de recebimentos → Run workflow**. O workflow usa os
Secrets `RECEBIMENTOS_*` para credenciais e caminhos, sem recorrer às
credenciais da automação Booking × OPERA. A empresa do CMFlex é `MAGNA` por
padrão e pode ser definida por `RECEBIMENTOS_CMFLEX_COMPANY` em Secret ou
Variable. A pasta da Rede é obrigatória;
sem ela, a execução falha antes dos downloads em vez de pular a conferência.
Secrets cadastrados em um Environment não ficam disponíveis neste job sem
vincular esse Environment ao workflow.
Nesta etapa, ele baixa os relatórios do OPERA e do CMFlex e publica o artefato
`conferencia-recebimentos-<número-da-execução>`.

### Arquivos gerados

Na execução conjunta, os relatórios são gravados em `output/magna/`,
`output/charme/` e `output/wind/`. Em cada subpasta são gerados:

- `reservas_booking.csv`;
- `conferencia_booking_opera.csv`;
- `conferencia_booking_opera.xlsx`.

O relatório final inclui os valores da Booking, a comissão cobrada, o valor do
OPERA, a diferença, o status e as observações da conciliação.

Ao final do workflow, o diretório é publicado no artefato
`booking-opera-<número-da-execução>`.

### Códigos de saída

| Código | Significado |
| --- | --- |
| `0` | Execução concluída. |
| `1` | Configuração inválida ou falha geral. |
| `2` | Automação inválida ou divergência com `--fail-on-divergence`. |

## Inclusão de uma nova automação

1. Crie o pacote `automations/<nome_da_automacao>/`.
2. Implemente um `cli.py` que receba os argumentos e retorne o código de saída.
3. Registre o identificador e o ponto de entrada em `automations/registry.py`.
4. Adicione os testes em `tests/<nome_da_automacao>/`.
5. Crie o workflow `.github/workflows/<nome-da-automacao>.yml`.
6. Configure no workflow os secrets, a agenda, o timeout, a concorrência e os
   artefatos específicos da automação.

O comando do workflow deve informar explicitamente o identificador registrado:

```powershell
uv run python main.py <identificador>
```

## Testes

Execute a suíte completa com:

```powershell
uv run python -m unittest discover -s tests -v
```
