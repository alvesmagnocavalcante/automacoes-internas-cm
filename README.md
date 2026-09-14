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

Para consultar a lista pelo terminal:

```powershell
uv run python main.py --list
```

## Estrutura do projeto

```text
.
├── .github/workflows/          # Workflows do GitHub Actions
│   └── booking-opera.yml
├── automations/
│   ├── base.py                 # Contrato comum das automações
│   ├── registry.py             # Registro central de automações
│   └── booking_opera/
│       ├── cli.py              # Interface de linha de comando
│       ├── browser.py          # Integração com Booking e OPERA
│       ├── domain.py           # Regras de negócio da conciliação
│       ├── models.py           # Configurações e modelos
│       ├── reports.py          # Geração de relatórios
│       └── service.py          # Orquestração do processo
├── tests/
│   └── booking_opera/          # Testes da automação
├── main.py                     # Ponto de entrada
├── pyproject.toml              # Projeto e dependências Python
└── uv.lock                     # Versões fixadas das dependências
```

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

## GitHub Actions e runner local

O workflow da Booking × OPERA está definido em
`.github/workflows/booking-opera.yml` e é executado exclusivamente em um runner
com os rótulos:

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

## Configuração da Booking × OPERA

Cadastre os seguintes secrets em
**Settings → Secrets and variables → Actions**:

| Secret | Finalidade |
| --- | --- |
| `BOOKING_USERNAME` | Usuário de acesso à Booking. |
| `BOOKING_PASSWORD` | Senha de acesso à Booking. |
| `OPERA_USERNAME` | Usuário de acesso ao OPERA. |
| `OPERA_PASSWORD` | Senha de acesso ao OPERA. |
| `OPERA_HOTEL` | Nome exato do hotel ou resort no OPERA. |

A execução manual está disponível em
**Actions → Conciliação Booking x OPERA → Run workflow**.

### Arquivos gerados

Os relatórios são gravados no diretório `output/`:

- `reservas_booking.csv`;
- `conferencia_booking_opera.csv`;
- `conferencia_booking_opera.xlsx`.

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
