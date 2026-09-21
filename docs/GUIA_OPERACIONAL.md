# Automações Internas CM — Guia técnico e operacional

## 1. Objetivo

Este repositório centraliza automações financeiras executadas por Python e
DrissionPage. O GitHub Actions prepara o ambiente e executa o código em um
runner Windows local. O Semaphore UI é o único agendador externo:
ele chama a API do GitHub, e o processamento continua acontecendo no GitHub
Actions.

Nunca registre senhas, tokens ou caminhos sensíveis diretamente nos arquivos do
repositório. Credenciais devem ficar em **GitHub Actions Secrets** ou em
**Secrets de um Variable Group do Semaphore**.

## 2. Visão geral

```text
Semaphore UI (único agendador)
        |
        | POST workflow_dispatch
        v
GitHub Actions
        |
        | seleciona runner self-hosted
        v
Runner Windows em sessão interativa
        |
        +-- Booking
        +-- OPERA Cloud
        +-- CMFlex
        +-- pasta de entrada da Rede
        +-- pasta compartilhada de saída
```

| Componente | Responsabilidade |
| --- | --- |
| `main.py` | Ponto de entrada e seleção da automação. |
| `automations/booking_opera/` | Conferência Booking × OPERA. |
| `automations/recebimentos/` | Conferência OPERA × CMFlex × Rede. |
| `.github/workflows/` | Execução pelo GitHub Actions. |
| `scripts/disparar-recebimentos.sh` | Disparo do workflow pelo Semaphore. |
| `tests/` | Testes automatizados. |

## 3. Requisitos e instalação

### 3.1 Desenvolvimento local

- Windows;
- Python 3.12;
- `uv` instalado;
- Google Chrome ou Chromium compatível;
- acesso aos sites Booking, OPERA e CMFlex;
- acesso de leitura e gravação às pastas utilizadas;
- sessão gráfica ativa para execução com navegador visível.

```powershell
uv sync --frozen --system-certs
Copy-Item .env.example .env
uv run python main.py --list
```

O `--system-certs` faz o `uv` utilizar os certificados do Windows. Isso evita o
erro `invalid peer certificate: UnknownIssuer` em redes com certificado
corporativo.

Testes e qualidade:

```powershell
uv run python -m unittest discover -s tests -v
uv run ruff check automations tests main.py
```

### 3.2 Runner Windows do GitHub Actions

Cadastre o runner em **Settings → Actions → Runners → New self-hosted runner**.
O GitHub recomenda `C:\actions-runner` para a instalação no Windows. Consulte
[Adding self-hosted runners](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners).

Requisitos específicos deste projeto:

1. O runner deve estar online antes do horário agendado.
2. A conta do runner deve conseguir abrir o Chrome.
3. A conta deve estar autenticada no Windows e com a sessão gráfica ativa.
4. A conta deve possuir acesso às pastas UNC de entrada e saída.
5. Chrome, PowerShell e acesso de rede devem estar disponíveis.

As automações usam navegador visível. Portanto, embora o GitHub permita instalar
o runner como serviço, neste projeto ele deve ser iniciado dentro da sessão
interativa do usuário:

```powershell
Set-Location C:\actions-runner
.\run.cmd
```

Como serviço, o Chrome pode não acessar a área de trabalho. A documentação geral
está em [Configuring the self-hosted runner application as a service](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/configure-the-application).

Labels esperadas:

- Recebimentos: `self-hosted`, `windows`, `x64`;
- Booking × OPERA: atualmente exige apenas `self-hosted` no workflow.

## 4. Automação Booking × OPERA

### 4.1 Fluxo e empresas

A automação extrai as reservas financeiras da Booking, consulta cada reserva no
OPERA e gera uma planilha de conferência.

Empresas ativas em `--all-companies`, nesta ordem:

1. CHARME;
2. WIND;
3. TAIBA;
4. MAGNA.

MAGNA é executada por último. ACARIZINHO está cadastrado como suportado, mas não
participa de `--all-companies`. O acesso ao OPERA é compartilhado; a Booking e a
localização do hotel no OPERA são específicas por empresa. Uma falha interrompe
as empresas seguintes.

### 4.2 Secrets e Variable

Cadastre em **Settings → Secrets and variables → Actions → Secrets**:

| Nome | Uso |
| --- | --- |
| `BOOKING_CHARME_USERNAME` | Usuário Booking da CHARME. |
| `BOOKING_CHARME_PASSWORD` | Senha Booking da CHARME. |
| `BOOKING_WIND_USERNAME` | Usuário Booking da WIND. |
| `BOOKING_WIND_PASSWORD` | Senha Booking da WIND. |
| `BOOKING_TAIBA_USERNAME` | Usuário Booking da TAIBA. |
| `BOOKING_TAIBA_PASSWORD` | Senha Booking da TAIBA. |
| `BOOKING_MAGNA_USERNAME` | Usuário Booking da MAGNA. |
| `BOOKING_MAGNA_PASSWORD` | Senha Booking da MAGNA. |
| `OPERA_USERNAME` | Usuário compartilhado do OPERA. |
| `OPERA_PASSWORD` | Senha compartilhada do OPERA. |
| `OPERA_HOTEL_CHARME` | Localização exata da CHARME no OPERA. |
| `OPERA_HOTEL_WIND` | Localização exata da WIND no OPERA. |
| `OPERA_HOTEL_TAIBA` | Localização exata da TAIBA no OPERA. |
| `OPERA_HOTEL_MAGNA` | Localização exata da MAGNA no OPERA. |

Compatibilidade legada da MAGNA:

- `BOOKING_USERNAME` e `BOOKING_PASSWORD` substituem o par específico quando
  `BOOKING_MAGNA_*` não está preenchido;
- `OPERA_HOTEL` substitui `OPERA_HOTEL_MAGNA`.

Os Secrets `BOOKING_ACARIZINHO_USERNAME`, `BOOKING_ACARIZINHO_PASSWORD` e
`OPERA_HOTEL_ACARIZINHO` somente serão necessários quando a empresa for ativada.

Cadastre como **Repository Variable**:

| Nome | Uso |
| --- | --- |
| `BOOKING_ARCHIVE_DIR` | Pasta opcional onde será copiado o Excel final. |

Prefira caminho UNC, como `\\servidor\setor\Booking`. Uma unidade mapeada como
`Z:` pode não existir na sessão do runner.

### 4.3 Execução e saídas

```powershell
# Todas as empresas
uv run python main.py booking-opera --all-companies

# Uma empresa
uv run python main.py booking-opera --company TAIBA

# Pasta externa pela linha de comando
uv run python main.py booking-opera --all-companies `
  --archive-dir "\\servidor\setor\Booking"

# Código 2 se houver divergências ou erros
uv run python main.py booking-opera --all-companies --fail-on-divergence
```

Para cada empresa são criados:

```text
output/<empresa>/reservas_booking.csv
output/<empresa>/conferencia_booking_opera.csv
output/<empresa>/conferencia_booking_opera.xlsx
```

Com `BOOKING_ARCHIVE_DIR`:

```text
BOOKING_ARCHIVE_DIR/<empresa>/conferencia_booking_opera_<data_hora>.xlsx
```

Resultados: `OK`, `DIVERGENTE`, `ERRO` ou `NÃO CONFERIDA - REGRA`. Uma reserva
não conferida não atende à regra de comparação, por exemplo um cancelamento sem
cobrança/comissão aplicável.

Regras principais da comparação:

- reservas concluídas são elegíveis;
- cancelamentos somente entram quando possuem comissão e valor aplicável;
- no-show somente entra quando possui comissão e valor final positivo;
- linhas agrupadas da mesma reserva são consolidadas antes da consulta;
- o valor final da Booking é comparado ao total encontrado no OPERA;
- diferença absoluta de até `R$ 0,01` é considerada `OK`;
- uma falha de consulta vira `ERRO` na própria reserva e fica contabilizada como
  divergência no resumo.

### 4.4 Workflow

Arquivo: `.github/workflows/booking-opera.yml`.

- disparo manual (`workflow_dispatch`);
- timeout de 270 minutos;
- uma execução por vez;
- comando `uv run python main.py booking-opera --all-companies`;
- publicação de `output/` como artifact por 30 dias.

A pasta externa não é um artifact: ela é gravada diretamente pelo runner.

## 5. Conferência de recebimentos

### 5.1 Fluxo e empresas

A automação baixa relatórios do OPERA e do CMFlex, localiza os arquivos
entregues pela Rede, realiza as comparações e salva três planilhas marcadas.

Empresas ativas, nesta ordem:

1. TAIBA — `CARMEL TAÍBA` no CMFlex;
2. CHARME — `CARMEL CHARME HOSPEDAGEM`;
3. CUMBUCO — `CARMEL CUMBUCO`;
4. MAGNA — `MAGNA PRAIA`.

Na Rede, `CARMEL WIND` é tratado como CUMBUCO. ICARAIZINHO e CM CENTRAL
SERVIÇOS não são processados.

### 5.2 Secrets e Variables

Secrets obrigatórios:

| Nome | Uso |
| --- | --- |
| `RECEBIMENTOS_OPERA_USERNAME` | Usuário OPERA. |
| `RECEBIMENTOS_OPERA_PASSWORD` | Senha OPERA. |
| `RECEBIMENTOS_CMFLEX_USERNAME` | Usuário CMFlex. |
| `RECEBIMENTOS_CMFLEX_PASSWORD` | Senha CMFlex. |
| `RECEBIMENTOS_REDE_DIR` | Pasta de entrada dos arquivos da Rede. |
| `RECEBIMENTOS_ARCHIVE_ROOT` | Raiz das conferências finais. |

Localizações OPERA, aceitas pelo workflow como Secret ou Repository Variable:

| Nome |
| --- |
| `RECEBIMENTOS_OPERA_HOTEL_TAIBA` |
| `RECEBIMENTOS_OPERA_HOTEL_CHARME` |
| `RECEBIMENTOS_OPERA_HOTEL_CUMBUCO` |
| `RECEBIMENTOS_OPERA_HOTEL_MAGNA` |

`RECEBIMENTOS_OPERA_HOTEL` continua sendo fallback da MAGNA.

Secrets de um GitHub Environment não chegam ao job atual, porque o workflow não
declara `environment`. Use Repository Secrets ou altere deliberadamente o job.

### 5.3 Entrada da Rede

Todos os arquivos podem ficar juntos em `RECEBIMENTOS_REDE_DIR`. Cada arquivo:

- deve ser `.xlsx` ou `.xlsm`;
- deve conter `Rede` no nome;
- deve conter a data como `DD.MM`, `DD-MM`, `DD_MM` ou `AAAA-MM-DD`;
- deve possuir `nome do estabelecimento`, preferencialmente nas primeiras 20
  linhas;
- deve conter somente uma empresa.

Exemplo:

```text
Rede_Rel_Vendas_20_09_2026-a1b2c3.xlsx
```

A data vem do nome, não da data de criação do Windows. A empresa vem do conteúdo
da planilha. Se o nome também indicar empresa, os valores devem coincidir.

Antes de abrir os navegadores, a execução é interrompida se houver empresa
desconhecida, empresas misturadas, arquivo duplicado, empresa obrigatória
ausente ou pasta inacessível.

### 5.4 Regra das datas

O runner usa `date.today()` e o calendário local do Windows:

- segunda-feira: sexta, sábado e domingo, em ordem cronológica;
- demais dias: dia anterior;
- com `--data`: somente a data informada.

Na segunda-feira, todos os arquivos das três datas são validados primeiro. A
execução segue:

```text
sexta:   TAIBA → CHARME → CUMBUCO → MAGNA
sábado:  TAIBA → CHARME → CUMBUCO → MAGNA
domingo: TAIBA → CHARME → CUMBUCO → MAGNA
```

A mesma data é enviada ao OPERA, CMFlex, seleção da Rede e pasta de saída.

### 5.5 Regras de conciliação

Categorias reconhecidas no OPERA:

| Categoria | Identificação principal |
| --- | --- |
| Dinheiro | código `9086` ou descrição contendo dinheiro |
| PIX | código `9087` ou descrição contendo PIX |
| A faturar | código `9090` ou descrição contendo faturar |
| Depósito | descrição contendo depósito |
| Cartão | descrição iniciada por Rede ou código iniciado por `93` |

Comparações realizadas:

- cartões: Rede × OPERA, considerando apenas vendas Rede aprovadas de crédito
  ou débito;
- cartões usam valor e, quando disponível nos dois lados, os quatro últimos
  dígitos;
- a busca tenta correspondência individual e depois agrupamentos de até quatro
  lançamentos que somem o mesmo valor;
- dinheiro, PIX e a faturar: CMFlex × OPERA pela chave do documento;
- depósitos: CMFlex × OPERA pelo total do dia;
- estornos do CMFlex são associados ao PIX ou ao depósito conforme a chave;
- tolerância monetária: `R$ 0,01`.

Registros fora dessas categorias são contabilizados como ignorados e não
alteram o resultado das categorias conciliadas.

### 5.6 Execução

```powershell
# Fluxo completo
uv run python main.py conferencia-recebimentos --all-companies

# Reprocessamento de uma data
uv run python main.py conferencia-recebimentos --all-companies `
  --data 20/09/2026

# Teste parcial
uv run python main.py conferencia-recebimentos --all-companies `
  --allow-partial --data 20/09/2026

# Downloads isolados
uv run python main.py conferencia-recebimentos --baixar-opera `
  --hotel "LOCALIZAÇÃO OPERA" --data 20/09/2026

uv run python main.py conferencia-recebimentos --baixar-cmflex `
  --empresa-cmflex "CARMEL TAÍBA" --data 20/09/2026
```

### 5.7 Saídas e permissões

Downloads intermediários:

```text
output/recebimentos/<empresa>/opera_recebimentos_AAAA-MM-DD.xml
output/recebimentos/<empresa>/cmflex_recebimentos_AAAA-MM-DD.xlsx
```

Conferência final:

```text
RECEBIMENTOS_ARCHIVE_ROOT/
  MM - MÊS/
    DD/
      EMPRESA/
        Opera Empresa DD.MM.xlsx
        CmFlex Empresa DD.MM.xlsx
        Rede Empresa DD.MM.xlsx
```

A pasta final contém somente os três arquivos Excel. Registros conciliados são
marcados com cores correspondentes.

No Windows, cada arquivo recebe `icacls /reset /Q` para herdar as permissões da
pasta. A conta do runner precisa criar arquivos e redefinir a ACL. Em Linux, o
modo aplicado é `0644`.

### 5.8 Workflow

Arquivo: `.github/workflows/conferencia-recebimentos.yml`.

- runner `self-hosted`, `windows`, `x64`;
- timeout de 180 minutos;
- uma execução por vez;
- testes de recebimentos antes da automação;
- inputs manuais `allow_partial` e `report_date`;
- artifact `output/recebimentos/` por 30 dias.

O workflow não possui `schedule`. O único cron válido fica no Semaphore, que
aciona o GitHub Actions por `workflow_dispatch`. Não adicione cron ao workflow,
pois isso criaria uma segunda fonte de agendamento e poderia duplicar execuções.

## 6. Semaphore UI acionando GitHub Actions

### 6.1 Responsabilidade

O Semaphore não executa os navegadores nem acessa as pastas financeiras. Ele
executa `scripts/disparar-recebimentos.sh`, que chama a API do GitHub. O GitHub
coloca o job na fila do runner Windows.

### 6.2 Token do GitHub

Crie um Fine-grained Personal Access Token:

1. restrinja-o ao repositório `automacoes-internas-cm`;
2. conceda **Repository permissions → Actions: Read and write**;
3. defina expiração e responsável pela renovação.

O endpoint exige `Actions: write`. Token clássico precisa do escopo `repo` em
repositório privado. Consulte [REST API endpoints for workflows](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event).

Não use o token temporário de cadastro do runner; ele expira.

### 6.3 Repositório no Semaphore

1. Abra **Repositories**.
2. Cadastre
   `https://github.com/alvesmagnocavalcante/automacoes-internas-cm`.
3. Selecione a branch `main`.
4. Para repositório privado, associe uma credencial de leitura do Key Store.
5. Confirme que o Semaphore consegue atualizar o repositório.

Todo Task Template precisa de um repositório. Consulte
[Repositories](https://docs.semaphoreui.com/user-guide/repositories).

### 6.4 Variable Group

1. Abra **Variable Groups**.
2. Crie ou edite o grupo `Action`.
3. Na aba **Secrets**, adicione:

```text
GITHUB_ACTIONS_TOKEN=<token fine-grained>
```

4. Salve.

O nome é exato; o script falha se a variável estiver ausente.

### 6.5 Task Template

Crie um template **Bash Script**:

| Campo | Valor |
| --- | --- |
| Nome | `Cron_Action` ou nome descritivo |
| Repositório | `automacoes-internas-cm` |
| Branch | `main` |
| Script Filename | `scripts/disparar-recebimentos.sh` |
| Variable Group | `Action` |
| Allow parallel tasks | desabilitado |

O Script Filename deve apontar para o `.sh`, não para o `.yml` do Actions. O
Semaphore executa Bash e injeta Variable Groups no ambiente. Consulte
[Shell/Bash scripts](https://semaphoreui.com/docs/user-guide/apps/bash).

Execute o template manualmente. O log esperado termina com:

```text
Disparo solicitado ao GitHub Actions.
```

Confirme em **GitHub → Actions → Conferência de recebimentos** a nova execução.

### 6.6 Agendamento

Configure o fuso do Semaphore como `America/Sao_Paulo`. Sem isso, ele pode usar
UTC. A configuração oficial usa `SEMAPHORE_SCHEDULE_TIMEZONE` ou
`schedule.timezone`; consulte [Schedules](https://docs.semaphoreui.com/user-guide/schedules/).

No projeto:

1. abra **Schedule**;
2. clique em **New Schedule**;
3. selecione `Cron_Action`;
4. use um cron de segunda a sexta-feira.

Exemplo para 18:10:

```cron
10 18 * * 1-5
```

Na segunda-feira, uma única execução processa sexta, sábado e domingo. Não crie
três agendamentos.

### 6.7 Erros do Semaphore

#### `curl: (22) ... 403`

Verifique token expirado, repositório não incluído, `Actions: write` ausente,
conta sem acesso ou Variable Group não associado.

#### Falha logo após atualizar o repositório

Verifique se o script existe na `main`, se o caminho relativo está correto, se
o template é Bash e se o grupo `Action` foi selecionado.

#### Semaphore conclui, mas o job não começa

O disparo somente cria a execução. Verifique workflow habilitado, runner online,
labels, fila e regra de concorrência.

## 7. Operação do GitHub Actions

### 7.1 Execução manual

1. Abra **Actions**.
2. Selecione o workflow.
3. Clique em **Run workflow**.
4. Em recebimentos, use opcionalmente:
   - `allow_partial`, apenas para teste controlado;
   - `report_date`, para reprocessar uma data.

### 7.2 Concorrência

Cada workflow tem `cancel-in-progress: false`. Uma nova execução aguarda a
anterior. Booking e recebimentos usam grupos diferentes e podem disputar o mesmo
runner; mantenha horários separados.

### 7.3 Códigos de saída

| Código | Significado |
| --- | --- |
| `0` | Concluído. |
| `1` | Configuração inválida ou erro geral. |
| `2` | Divergência com `--fail-on-divergence`. |

## 8. Permissões de pasta compartilhada

Use caminho UNC e conceda permissões à conta do runner no compartilhamento SMB
e no NTFS. Ela precisa de leitura/listagem na entrada e criação, leitura,
gravação, alteração e herança na saída.

Teste na sessão do runner, somente em pasta autorizada:

```powershell
$path = "\\servidor\compartilhamento\teste-runner.txt"
Set-Content -LiteralPath $path -Value "teste"
Get-Content -LiteralPath $path
Remove-Item -LiteralPath $path
```

## 9. Solução de problemas

### Credenciais ausentes

- confira o nome exato;
- confira se é Repository Secret;
- Secrets de Environment exigem `environment` no job;
- Secret e Variable são recursos diferentes.

### `UnknownIssuer` no `uv sync`

- mantenha `UV_SYSTEM_CERTS=true` no workflow;
- localmente use `--system-certs`;
- confira o certificado corporativo no Windows.

### `BrowserConnectError`

- runner em sessão gráfica ativa;
- Chrome instalado;
- perfil não utilizado por outra execução;
- nenhum segundo job disputando o desktop;
- firewall permitindo as portas locais do Chromium.

### Relatório Rede ausente

Confira palavra `Rede`, data no nome, extensão, coluna
`nome do estabelecimento`, pasta e data exibida no log.

### Mais de um relatório Rede

Existem dois arquivos da mesma empresa e data. Remova da entrada a cópia
indevida.

### OPERA gera XML vazio

Confira data, limpeza de Cashier e Transaction Code, relatório selecionado e se
existem transações ao testar manualmente.

### Excel repara `styles.xml`

Regere o arquivo com a versão atual. Não reutilize o arquivo corrompido como
modelo.

### `icacls` retorna código 5

Confira permissões da conta do runner, herança NTFS, compartilhamento e se o
arquivo está aberto no Excel.

### Artifact vazio

Confira se a geração terminou. Pastas externas não são incluídas automaticamente
no artifact; somente arquivos dentro de `output/` são publicados.

## 10. Segurança e manutenção

- use token fine-grained limitado ao repositório;
- nunca versione `.env`, senhas ou tokens;
- defina expiração e renovação do token do Semaphore;
- mantenha runner e Chrome atualizados;
- preserve `uv.lock` e use `uv sync --frozen`;
- teste mudanças com `--data` e `--allow-partial`;
- não altere XPaths sem evidência da mudança do site;
- não execute as duas automações simultaneamente no mesmo desktop.

## 11. Checklist operacional

Antes:

- runner online e sessão desbloqueada;
- Chrome disponível;
- pastas acessíveis;
- arquivos Rede esperados presentes;
- nenhuma execução anterior ativa.

Depois:

- workflow concluído no GitHub;
- quantidade de empresas e datas correta;
- três Excel por empresa em recebimentos;
- Excel Booking copiado quando configurado;
- artifacts disponíveis;
- divergências encaminhadas ao responsável.

## 12. Arquivos de referência

- `README.md`: visão rápida;
- `.env.example`: modelo local sem valores;
- `.github/workflows/booking-opera.yml`: workflow Booking × OPERA;
- `.github/workflows/conferencia-recebimentos.yml`: recebimentos;
- `scripts/disparar-recebimentos.sh`: Semaphore → GitHub;
- `automations/`: implementação;
- `tests/`: testes e regressões.
