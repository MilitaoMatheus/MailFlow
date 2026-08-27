# ✉️ MailFlow - Sistema de Gerenciamento e Envio de E-mails/Newsletters

> Plataforma multiusuário, modular, segura e escalável para gerenciamento de contatos, criação de templates particionados (Header, Body, Footer), configuração individual de contas de e-mail/SMTP com criptografia e disparo de campanhas com relatórios analíticos de entrega.

---

## 🌟 1. Visão Geral e Conceito

O **MailFlow** foi projetado seguindo uma arquitetura em camadas e princípios **SOLID**, oferecendo separação clara entre usuários, contatos, templates, campanhas e servidores de envio.

### 🔒 Isolamento Rigoroso de Perfis (Multi-Tenancy)
```
Perfil 1 (João)  ──>  Conta SMTP Própria  ──>  Templates Próprios  ──>  Contatos Próprios  ──>  Campanhas Próprias
Perfil 2 (Maria) ──>  Conta SMTP Própria  ──>  Templates Próprios  ──>  Contatos Próprios  ──>  Campanhas Próprias
```
Os dados de um perfil **nunca** são compartilhados ou acessíveis por outro perfil, seja via interface web ou requisições diretas de API.

---

## 🏗️ 2. Arquitetura do Sistema

A aplicação segue a separação em 4 camadas fundamentais:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                   INTERFACE WEB (HTML5, Tailwind, Alpine.js)             │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │ HTTP (Forms / API)
┌────────────────────────────────────▼─────────────────────────────────────┐
│                   CONTROLLERS (Rotas e Validação de Entrada)             │
│   Auth • Dashboard • Contacts • Templates • Campaigns • Settings • Public│
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼─────────────────────────────────────┐
│                   SERVICES (Regras de Negócio e Orquestração)            │
│   AuthService • ContactService • TemplateService • CampaignService       │
│   EmailService • SecurityService • LogService                            │
└──────────────────┬───────────────────────────────────┬───────────────────┘
                   │                                   │
┌──────────────────▼─────────────────┐   ┌─────────────▼───────────────────┐
│ EMAIL PROVIDERS (Envio Agnostico)  │   │ REPOSITORIES (Acesso a Dados)   │
│ • SmtpEmailProvider (SSL/STARTTLS) │   │ (Filtros estritos por user_id)  │
│ • MockEmailProvider (Dev/Testes)   │   └─────────────┬───────────────────┘
│ • [Futuro: SES, SendGrid, Mailgun] │                 │
└────────────────────────────────────┘   ┌─────────────▼───────────────────┐
                                         │ DATABASE (SQLite / MySQL / PG)  │
                                         └─────────────────────────────────┘
```

---

## 🚀 3. Funcionalidades Implementadas (MVP Completo)

### 🔐 3.1 Autenticação & Perfis
- Cadastro de perfis com validação de dados.
- Login e Logout com cookies seguros `HttpOnly` assinados via **HMAC-SHA256**.
- Hashing de senhas com algoritmo seguro **PBKDF2-SHA256** (100.000 iterações + salt aleatório de 16 bytes).
- Alteração de senha no perfil.

### 🛡️ 3.2 Segurança & Criptografia SMTP
- Suporte a múltiplos provedores (Gmail, Outlook/Office 365, Mailgun, Amazon SES ou qualquer servidor SMTP genérico).
- **Criptografia Simétrica**: Credenciais SMTP (senhas e App Passwords) são criptografadas em repouso no banco de dados via **AES-GCM / Fernet**.
- **Logs Seguros**: Nenhuma senha ou credencial sensível é registrada em logs ou na base de auditoria.
- Botão interativo **"Testar Conexão SMTP"** em tempo real com diagnóstico de conexão.

### 👥 3.3 Gerenciamento de Contatos
- Cadastro, edição, exclusão e alternância de status (Ativar/Desativar).
- Validação sintática rigorosa de e-mails no cadastro e pré-disparo (RFC 5322).
- Estados de contato: `ATIVO`, `INATIVO`, `INVALIDO`, `DESCADASTRADO`.
- **Importação CSV**: Detecção automática de delimitadores (`,` ou `;`), mapeamento flexível de colunas, validação e deduplicação automática com relatório.
- **Exportação CSV**: Download da base completa de contatos do perfil.

### 🎨 3.4 Templates Particionados & Variáveis Dinâmicas
- Estrutura em 3 blocos independentes:
  - **HEADER**: Logotipo, identidade visual, cores e cabeçalho.
  - **BODY**: Conteúdo principal da mensagem, textos, imagens e chamadas para ação.
  - **FOOTER**: Informações da empresa, redes sociais e link de descadastro obrigatório.
- **Motor de Interpolação de Variáveis**:
  - `{{nome}}`: Nome do contato destinatário.
  - `{{email}}`: E-mail do destinatário.
  - `{{empresa}}`: Empresa do destinatário.
  - `{{data}}`: Data atual formatada (DD/MM/AAAA).
  - `{{nome_perfil}}`: Nome do remetente / perfil.
  - `{{link_descadastro}}`: Link exclusivo de descadastro com token seguro.
- **Pré-visualização Interativa**: Modal com iframe renderizando o template formatado com dados de exemplo.

### 📢 3.5 Campanhas e Disparo Tolerante a Falhas
- Criação de campanhas com seleção de template e público (todos os contatos ativos ou seleção personalizada).
- **Envio Resiliente por Lote**:
  - A falha no envio para um destinatário **não interrompe** o disparo dos demais contatos da campanha.
  - Registro individual do resultado de cada destinatário (`ENVIADO`, `FALHA`, `INVALIDO`, `IGNORADO`) com a causa do erro.
- **Relatório Analítico Pós-Campanha**:
  - Total de destinatários, enviados com sucesso, falhas, inválidos, ignorados e taxa de sucesso percentual (%).
  - Tabela detalhada de cada disparo individual.

### 🛑 3.6 Descadastro Automático (*Opt-Out*)
- Todo e-mail gerado inclui link dinâmico de descadastro com token seguro de 32 bytes (`/unsubscribe?token=...`).
- Cabeçalhos RFC 2369 e RFC 8058 (`List-Unsubscribe` e `List-Unsubscribe-Post`).
- Ao clicar no link, o status do contato é alterado imediatamente para `DESCADASTRADO` e campanhas futuras ignoram esse contato automaticamente.

---

## 💻 4. Guia de Instalação e Execução Local

### Pré-requisitos
- Python 3.10+ (ou superior)

### 1. Clonar ou Acessar a Pasta do Projeto
```bash
cd newsletter-system
```

### 2. Criar e Ativar Ambiente Virtual (Opcional, mas Recomendado)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar Variáveis de Ambiente
Copie o arquivo de exemplo e ajuste se necessário:
```bash
cp .env.example .env
```

### 5. Iniciar a Aplicação
```bash
python run.py
```
Acesse no navegador: **`http://localhost:8000`**

---

## ⚙️ 5. Guia de Configuração SMTP

Para realizar disparos reais, acesse a aba **Configurações SMTP** no painel da aplicação.

### Configuração com Gmail:
1. Acesse sua Conta Google -> **Segurança** -> **Verificação em 2 etapas** (deve estar ativada).
2. Vá em **Senhas de app** (App Passwords) e gere uma senha de 16 caracteres para "MailFlow".
3. No MailFlow, configure:
   - **Remetente:** Seu Nome ou Empresa
   - **E-mail:** `seu-email@gmail.com`
   - **Servidor SMTP:** `smtp.gmail.com`
   - **Porta:** `587`
   - **Usuário:** `seu-email@gmail.com`
   - **Senha:** A senha de app gerada de 16 letras
   - **Segurança:** `STARTTLS`
4. Clique em **Salvar** e depois em **Testar Conexão**.

### Configuração com Outlook / Microsoft 365:
- **Servidor:** `smtp.office365.com`
- **Porta:** `587`
- **Segurança:** `STARTTLS`

---

## 🧪 6. Testes Automatizados

O projeto conta com suíte de testes com **100% de aprovação** cobrindo todas as regras de negócio:

```bash
# Executar todos os testes com saída detalhada
python -m pytest -v
```

### Cobertura de Testes:
- `tests/test_auth.py`: Fluxo de registro, login, senha incorreta, usuário inexistente, integridade de tokens HMAC.
- `tests/test_isolation.py`: Isolamento rigoroso multi-tenant entre Usuário A e Usuário B em contatos, templates, campanhas e SMTP.
- `tests/test_validation.py`: Validação de e-mails RFC 5322 (válidos, inválidos, com espaços) e ciclo de vida de status de contatos.
- `tests/test_templates.py`: Montagem de blocos Header/Body/Footer e substituição de tags `{{nome}}`, `{{link_descadastro}}`, etc.
- `tests/test_campaigns.py`: Execução de campanhas por lote com tolerância a falhas (sucesso, falha SMTP simulada, descadastrado) e cálculo de métricas.
- `tests/test_unsubscribe.py`: Descadastro via token público, alteração para `DESCADASTRADO` e bloqueio de novos envios.
- `tests/test_web_integration.py`: Jornada web completa e proteção de rotas HTTP contra acessos cruzados.

---

## 🚀 7. Guia de Execução em Produção

Para implantação em servidores de produção (Linux / Docker / Cloud):

### 1. Variáveis de Ambiente Críticas
No arquivo `.env` de produção:
```env
APP_ENV=production
DEBUG=False
SECRET_KEY=sua-chave-secreta-longa-min-64-caracteres
ENCRYPTION_KEY=sua-chave-fernet-base64-gerada
APP_BASE_URL=https://seudominio.com
DATABASE_URL=mysql+pymysql://usuario:senha@localhost:3306/newsletter_db
```

### 2. Gunicorn / Uvicorn Workers
```bash
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 3. Proxy Reverso (Nginx)
Configure Nginx para redirecionar tráfego HTTPS para a porta 8000 com cabeçalhos `X-Forwarded-For` e `X-Forwarded-Proto`.

---

## 🗺️ 8. Roadmap e Funcionalidades Futuras

- [ ] **Fila Assíncrona de Disparo**: Integração com Celery / Redis para envio em background em grandes volumes.
- [ ] **Editor Visual Drag & Drop**: Edição WYSIWYG de blocos sem necessidade de HTML.
- [ ] **Métricas Avançadas**: Pixel de rastreamento de abertura e redirecionamento de cliques.
- [ ] **Provedores Nativos na Nuvem**: Plugins para Amazon SES, SendGrid e Mailgun via API REST.
- [ ] **Agendamento de Campanhas**: Disparo programado por data e hora.
- [ ] **Segmentação por Tags**: Envio filtrado por tags (`VIP`, `Lead`, `Cliente`).
