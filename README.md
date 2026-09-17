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

A empresa padrão nesse comando isolado é `MAGNA`; use `--empresa-cmflex` para
selecionar outra.
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
`.github/workflows/conferencia-recebimentos.yml`. O primeiro usa um runner
`self-hosted`; o segundo exige os rótulos `self-hosted`, `windows` e `x64`.

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

Em **Settings → Secrets and variables → Actions → Repository secrets**, configure:

| Secret | Necessidade na execução `--all-companies` |
| --- | --- |
| `BOOKING_USERNAME` | Usuário Booking da MAGNA; use junto de `BOOKING_PASSWORD`. Alternativa: o par `BOOKING_MAGNA_USERNAME`/`BOOKING_MAGNA_PASSWORD`. |
| `BOOKING_PASSWORD` | Senha Booking da MAGNA; use junto de `BOOKING_USERNAME`. |
| `BOOKING_MAGNA_USERNAME` | Opcional: substitui `BOOKING_USERNAME` se o par MAGNA específico estiver completo. |
| `BOOKING_MAGNA_PASSWORD` | Opcional: substitui `BOOKING_PASSWORD` se o par MAGNA específico estiver completo. |
| `BOOKING_CHARME_USERNAME` | Usuário Booking da CHARME; obrigatório. |
| `BOOKING_CHARME_PASSWORD` | Senha Booking da CHARME; obrigatória. |
| `BOOKING_WIND_USERNAME` | Usuário Booking da WIND; obrigatório. |
| `BOOKING_WIND_PASSWORD` | Senha Booking da WIND; obrigatória. |
| `OPERA_USERNAME` | Usuário OPERA compartilhado entre as empresas deste workflow; obrigatório. |
| `OPERA_PASSWORD` | Senha OPERA compartilhada; obrigatória. |
| `OPERA_HOTEL` | Localização MAGNA no OPERA; use esta ou `OPERA_HOTEL_MAGNA`. |
| `OPERA_HOTEL_MAGNA` | Opcional: substitui `OPERA_HOTEL` para MAGNA. |
| `OPERA_HOTEL_CHARME` | Localização CHARME no OPERA; obrigatória. |
| `OPERA_HOTEL_WIND` | Localização WIND no OPERA; obrigatória. |

A execução manual está disponível em
**Actions → Conciliação Booking x OPERA → Run workflow**.

O agendamento permanece desabilitado no workflow; a execução atual é manual.

O workflow confere `CHARME`, `WIND` e `MAGNA` nessa ordem, sem executar duas
empresas ao mesmo tempo. Antes de abrir o navegador, valida as credenciais e o
hotel OPERA das três; se uma conferência falhar, as seguintes não começam.
O mesmo usuário e senha `OPERA_USERNAME`/`OPERA_PASSWORD` são usados em todas.

Cadastre os nomes dos hotéis como **Secrets** do repositório, assim como o
`OPERA_HOTEL` já existente. Acarizinho está previsto por
`BOOKING_ACARIZINHO_USERNAME`, `BOOKING_ACARIZINHO_PASSWORD` e
`OPERA_HOTEL_ACARIZINHO`, mas não participa da execução conjunta até que suas
credenciais estejam disponíveis. Para conferir uma única empresa, use
`uv run python main.py booking-opera --company CHARME`; sem `--company` nem
`--all-companies`, o comando local mantém o comportamento anterior.

Para salvar também o Excel final em uma pasta escolhida por você, cadastre a
**Repository Variable** `BOOKING_ARCHIVE_DIR` em
**Settings → Secrets and variables → Actions → Variables**
com o caminho dessa pasta. O caminho deve ser acessível pelo runner que executa
o workflow (no webtop, use um caminho Linux ou um volume montado). Na execução
conjunta, cada empresa recebe sua própria subpasta nessa raiz. A cópia recebe
data e hora no nome para preservar execuções anteriores; os arquivos em
`output/<empresa>/` e o artefato do Actions permanecem disponíveis. Sem a
Variable, não há cópia adicional. Um **Secret** chamado `BOOKING_ARCHIVE_DIR`
não é lido pelo workflow atual. Localmente, também é possível usar
`--archive-dir`.

### Arquivos gerados

Na execução conjunta, cada empresa recebe sua subpasta em `output/` com
`reservas_booking.csv`, `conferencia_booking_opera.csv` e
`conferencia_booking_opera.xlsx`. O Excel contém valores Booking e OPERA,
diferença, status e observações. Ao final, `output/` é publicado no artefato
`booking-opera-<número-da-execução>`.

## Configuração da conferência de recebimentos

Em **Repository secrets**, configure os nomes abaixo. Esta automação usa nomes
próprios; não recebe automaticamente os secrets `OPERA_*` do workflow Booking.

| Secret | Necessidade na execução `--all-companies` |
| --- | --- |
| `RECEBIMENTOS_OPERA_USERNAME` | Usuário OPERA; obrigatório e usado para todas as empresas. |
| `RECEBIMENTOS_OPERA_PASSWORD` | Senha OPERA; obrigatória e usada para todas as empresas. |
| `RECEBIMENTOS_CMFLEX_USERNAME` | Usuário CMFlex; obrigatório e usado para todas as empresas. |
| `RECEBIMENTOS_CMFLEX_PASSWORD` | Senha CMFlex; obrigatória e usada para todas as empresas. |
| `RECEBIMENTOS_OPERA_HOTEL_CHARME` | Localização CHARME no OPERA; obrigatória quando CHARME é conferida. |
| `RECEBIMENTOS_OPERA_HOTEL_CUMBUCO` | Localização CUMBUCO no OPERA; obrigatória quando CUMBUCO é conferida. |
| `RECEBIMENTOS_OPERA_HOTEL_TAIBA` | Localização TAIBA no OPERA; obrigatória quando TAIBA é conferida. |
| `RECEBIMENTOS_OPERA_HOTEL_MAGNA` | Localização MAGNA no OPERA; use esta ou `RECEBIMENTOS_OPERA_HOTEL`. |
| `RECEBIMENTOS_OPERA_HOTEL` | Localização MAGNA existente; usada se `RECEBIMENTOS_OPERA_HOTEL_MAGNA` estiver vazia. |
| `RECEBIMENTOS_REDE_DIR` | Pasta dos Excel da Rede acessível pelo runner; obrigatória. |
| `RECEBIMENTOS_ARCHIVE_ROOT` | Pasta de destino das conferências; opcional, padrão `output/recebimentos/conferencias`. |

Os quatro nomes de localização podem ser cadastrados como **Repository
Variables**, em vez de Secrets, com os mesmos nomes: o workflow tenta primeiro
o Secret e depois a Variable. Usuários e senhas devem permanecer em Secrets.
Na execução parcial (`allow_partial`), só são exigidas as localizações das
empresas cujos arquivos da Rede estão presentes.

A execução manual está em
**Actions → Conferência de recebimentos → Run workflow**. O workflow usa os
Secrets `RECEBIMENTOS_*` para credenciais e caminhos, sem recorrer às
credenciais da automação Booking × OPERA. Executa sequencialmente CHARME,
CUMBUCO, TAIBA e MAGNA; CM CENTRAL SERVIÇOS e ICARAIZINHO são ignoradas. No
CMFlex, seleciona as empresas pelos nomes completos apresentados na lista.
O estabelecimento `CARMEL WIND` na Rede é identificado como CUMBUCO e
seleciona `CARMEL CUMBUCO` no CMFlex; não cria uma sexta conferência.
A pasta da Rede deve conter um Excel por empresa e data. O nome pode ser o
original da Rede, como `Rede_Rel_Vendas_16_09_2026-<id>.xlsx`: o sistema lê a
coluna `nome do estabelecimento` para identificar a empresa. O nome precisa
conter `Rede` e a data (`DD.MM`, `DD-MM`, `DD_MM` ou `AAAA-MM-DD`). Se também
contiver uma empresa, ela deve coincidir com o conteúdo. Arquivos sem
identificação, com empresas misturadas, duplicados ou ausentes interrompem a
execução antes dos downloads. Arquivos de ICARAIZINHO são reconhecidos, mas
não exigidos nem processados enquanto a empresa estiver inativa.
Para testes com apenas parte das planilhas, marque `allow_partial` em
**Run workflow** (ou use `--all-companies --allow-partial` localmente). Sem
essa opção, a execução exige as quatro empresas ativas para evitar conferências
diárias incompletas.
Os três relatórios Excel de cada empresa são arquivados em
`RECEBIMENTOS_ARCHIVE_ROOT/MM - MÊS/DD/EMPRESA/`; downloads ficam separados
em `output/recebimentos/empresa/`. O modo antigo `--conferir-baixados`
permanece disponível para uma única empresa com `--hotel` e
`--empresa-cmflex`.
Secrets cadastrados em um Environment não ficam disponíveis neste job sem
vincular esse Environment ao workflow.
O workflow publica os arquivos sob `output/recebimentos` no artefato
`conferencia-recebimentos-<número-da-execução>`. Se a raiz de arquivo for
externa, as conferências finais permanecem nessa raiz, acessível ao runner.

### O que não cadastrar no GitHub

`BOOKING_OUTPUT_DIR`, `BOOKING_HEADLESS`, `RECEBIMENTOS_HEADLESS`, `CI`,
`PYTHONUTF8` e `UV_SYSTEM_CERTS` já são definidos pelos workflows. A opção
`allow_partial` é um campo do botão **Run workflow**, não um Secret/Variable.
`RECEBIMENTOS_CMFLEX_COMPANY` é usado apenas no modo isolado/local; na
execução conjunta, o programa escolhe a empresa CMFlex automaticamente.
Outros ajustes locais, como URLs dos sistemas, estão em `.env.example` e não
são repassados pelos workflows atuais.

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
