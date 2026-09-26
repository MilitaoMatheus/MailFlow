# ✉️ MailFlow - Sistema de Gerenciamento e Envio de E-mails & Newsletters

> **MailFlow** é uma plataforma multiusuário, modular, moderna e escalável para gerenciamento de contatos, criação de campanhas de e-mail com construtor visual sem código (*Zero HTML*), suporte a anexos múltiplos (PDF, Word, imagens), configuração individual de contas de e-mail/SMTP com criptografia de ponta e relatórios analíticos de entrega em tempo real.

---

## 🌟 1. Visão Geral e Conceito

O **MailFlow** foi desenvolvido seguindo arquitetura em camadas e princípios **SOLID**, combinando segurança corporativa com uma experiência visual fluida e moderna voltada para produtos SaaS de alta produtividade.

### 🎨 Nova Identidade Visual & Design System
A interface foi projetada para transmitir **tecnologia, comunicação, confiança e profissionalismo**:
* **Azul Principal (`#2563EB`)**: Ações primárias, links, destaques de navegação e botões de chamada para ação (CTA).
* **Azul Claro (`#60A5FA`)**: Gradiente da marca e acentos visuais.
* **Azul Marinho / Slate 900 (`#0F172A`)**: Sidebar estrutural de alto contraste e cabeçalhos escuros sóbrios.
* **Fundo Slate 50 (`#F8FAFC`) e Branco Puro (`#FFFFFF`)**: Superfícies limpas com excelente legibilidade e conforto visual.
* **Cores Semânticas de Alta Precisão**: Verde Sucesso (`#22C55E`), Vermelho Erro (`#EF4444`) e Amarelo Alerta (`#F59E0B`).

### 🔒 Isolamento Rigoroso de Perfis (Multi-Tenancy)
```
Perfil 1 (Empresa A) ──> Conta SMTP Própria ──> Templates Próprios ──> Contatos Próprios ──> Campanhas Próprias
Perfil 2 (Empresa B) ──> Conta SMTP Própria ──> Templates Próprios ──> Contatos Próprios ──> Campanhas Próprias
```
Os dados de um perfil **nunca** são compartilhados ou acessíveis por outro perfil, seja via interface web ou requisições diretas de API.

---

## 🏗️ 2. Arquitetura do Sistema

A aplicação segue separação em camadas bem definidas e desacopladas:

```
┌──────────────────────────────────────────────────────────────────────────┐
│             INTERFACE WEB (HTML5, Tailwind CSS CDN, Alpine.js)           │
│     Design System SaaS • Construtor Semântico • Prévia Fixa ao Vivo     │
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
│   EmailService • SecurityService • PresetService • LogService            │
└──────────────────┬───────────────────────────────────┬───────────────────┘
                   │                                   │
┌──────────────────▼─────────────────┐   ┌─────────────▼───────────────────┐
│ EMAIL PROVIDERS (Envio Agnóstico)  │   │ REPOSITORIES (Acesso a Dados)   │
│ • SmtpEmailProvider (SSL/STARTTLS) │   │ (Filtros estritos por user_id)  │
│ • MockEmailProvider (Dev/Testes)   │   └─────────────┬───────────────────┘
│ • [Futuro: SES, SendGrid, Mailgun] │                 │
└────────────────────────────────────┘   ┌─────────────▼───────────────────┐
                                         │ DATABASE (SQLite / MySQL / PG)  │
                                         └─────────────────────────────────┘
```

---

## 🚀 3. Funcionalidades Principais

### 🎨 3.1 Construtor Visual de Templates Sem Código (*Zero HTML*)
* **Criação Descomplicada**: O usuário não precisa escrever uma única linha de HTML. O layout é montado através de campos semânticos amigáveis (Logotipo/Topo, Saudação, Headline, Mensagem com quebra automática de parágrafos, Botão CTA e Rodapé).
* **Presets de Modelos Prontos**:
  * 📰 *Newsletter / Resumo Semanal* (Conteúdos, novidades e artigos)
  * 🏷️ *Oferta Comercial / Promoção* (Lançamentos de produtos e descontos com alta conversão)
  * 🔔 *Comunicado Oficial / Aviso* (Atualizações institucionais, avisos e termos)
  * 🤝 *Boas-Vindas / Onboarding* (Apresentação de serviços e primeiro contato)
* **Customização de Cores & Estilo da Marca**:
  * Paleta Rápida (*Azul MailFlow, Azul Céu, Verde Esmeralda, Roxo Moderno, Laranja, Rosa, Grafite*) ou seletor nativo de cor hexadecimal.
  * Estilos de cabeçalho: 🌙 *Escuro Sóbrio*, 🎨 *Cor da Marca*, ☀️ *Claro Clean*.
* **Painel com Prévia Fixa ao Vivo (Desktop & Mobile)**:
  * A prévia do e-mail permanece totalmente visível e fixa na lateral direita enquanto o usuário edita o formulário à esquerda.
  * Alternador dinâmico de viewport (Desktop e simulação de smartphone Mobile).
* **Inserção de Tags Dinâmicas com 1 Clique**:
  * `{{nome}}`: Nome do contato destinatário.
  * `{{empresa}}`: Empresa do contato ou organização.
  * `{{email}}`: E-mail de destino.
  * `{{data}}`: Data atual formatada (DD/MM/AAAA).
  * `{{nome_perfil}}`: Nome do remetente / perfil emissor.
  * `{{link_descadastro}}`: Link criptografado e exclusivo de descadastro (opt-out).
* **Suporte a Modelos Sob Medida**:
  * Modal integrado para solicitação de templates personalizados diretamente via WhatsApp Comercial ou E-mail da equipe de suporte.

### 📢 3.2 Campanhas, Anexos Múltiplos & Tolerância a Falhas
* Criação de campanhas com seleção de template, assunto e público (base completa ou contatos selecionados).
* **Suporte a Anexos Múltiplos**:
  * Upload de múltiplos arquivos (PDF, Word DOC/DOCX, Imagens PNG/JPG/JPEG, Texto TXT) de até **5MB por arquivo**.
  * Sanitização rigorosa de nomes de arquivos para evitar path traversal e vulnerabilidades de sistema.
  * Armazenamento seguro e descarte automático de anexos órfãos quando uma campanha é excluída.
  * Envio via protocolo SMTP estruturado em multipart/mixed.
* **Disparo Resiliente em Lote**:
  * Falhas pontuais em destinatários específicos **não interrompem** o restante do lote.
  * Registro detalhado de cada resultado: `ENVIADO`, `FALHA`, `INVALIDO`, `IGNORADO`.
* **Relatório Analítico em Tempo Real**:
  * Contadores em cards semânticos, taxa percentual de sucesso e visualização individual de logs de cada envio.
* **👁️ Rastreamento de Abertura em Tempo Real (Pixel 1x1)**:
  * Injeção automática de pixel transparente (`GET /track/open/{open_token}.png`) com token seguro exclusivo de 32 bytes por contato.
  * Headers estritos anti-cache (`no-cache, no-store, must-revalidate`).
  * Contabilização de primeira abertura com timestamp (`opened_at`), contador acumulado de aberturas (`open_count`) e métrica de taxa de abertura (`open_rate`) exibida no painel da campanha e no dashboard principal.
* **🧪 Disparo de Prova / Envio de Teste**:
  * Validação prévia de layout com envio instantâneo para um e-mail informado pelo usuário antes do disparo em massa.
  * Prefixo automático `[TESTE] ` no assunto, substituição de variáveis com dados simulados e inclusão de todos os anexos reais da campanha.

### 👥 3.3 Gestão de Contatos & Importação de Alta Performance
* CRUD completo com status: `ATIVO`, `INATIVO`, `INVALIDO`, `DESCADASTRADO`.
* Validação sintática rigorosa de e-mails em conformidade com a RFC 5322.
* **Importação CSV em Massa**: Detecção automática de delimitadores (`,` ou `;`), mapeamento de colunas, deduplicação em memória e inserção em lote de alto desempenho.
* **Exportação CSV**: Exportação instantânea dos contatos do perfil ativo.

### 🛑 3.4 Descadastro Automático (*Opt-Out*)
* Todo e-mail compilado inclui link de descadastro com token seguro de 32 bytes (`/unsubscribe?token=...`).
* Inclusão de cabeçalhos RFC 2369 e RFC 8058 (`List-Unsubscribe` e `List-Unsubscribe-Post`).
* Atualização imediata do contato para o estado `DESCADASTRADO`, impedindo envios futuros automaticamente.

### 🛡️ 3.5 Segurança, Criptografia & Sessões
* **Criptografia Simétrica de Senhas SMTP**: Credenciais de servidores SMTP armazenadas em repouso com algoritmo **AES-GCM / Fernet**.
* **Proteção contra XSS**: Sanitização de templates HTML com biblioteca `Bleach`.
* **Invalidação de Sessão**: Versionamento de tokens de sessão (`token_version`), garantindo que a alteração de senha revogue automaticamente logins em outros dispositivos.
* **Hashing Robusto**: Senhas de acesso geradas via **PBKDF2-SHA256** com salt de 16 bytes e 100.000 iterações.
* **Cookies de Sessão**: Cookies `HttpOnly`, `SameSite=Lax` assinados via **HMAC-SHA256**.
* **Diagnóstico SMTP**: Ferramenta integrada "Testar Conexão" para validação imediata de servidores antes dos disparos.

---

## 💻 4. Guia de Instalação e Execução Local

### Pré-requisitos
* Python 3.10+ (ou superior)

### 1. Clonar o Repositório
```bash
git clone https://github.com/MilitaoMatheus/MailFlow.git
cd MailFlow
```

### 2. Criar e Ativar Ambiente Virtual
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
Copie o arquivo de exemplo (o banco SQLite local será inicializado automaticamente):
```bash
cp .env.example .env
```

### 5. Iniciar a Aplicação
```bash
python run.py
```
Acesse no seu navegador: **`http://localhost:8000`**

---

## ⚙️ 5. Configuração de Servidores SMTP

No menu **Configurações SMTP**, utilize os presets rápidos ou configure manualmente:

### Exemplo com Gmail:
1. Acesse sua Conta Google -> **Segurança** -> **Verificação em 2 etapas**.
2. Gere uma **Senha de app** (*App Password*) para o "MailFlow".
3. Preencha no painel:
   * **Host:** `smtp.gmail.com` | **Porta:** `587` | **Segurança:** `STARTTLS`
   * **Usuário:** seu endereço `@gmail.com`
   * **Senha:** a senha de app de 16 dígitos
4. Clique em **Salvar** e valide no botão **Testar Conexão**.

---

## 🧪 6. Testes Automatizados

O MailFlow possui uma suíte com **29 testes automatizados com 100% de aprovação**:

```bash
python -m pytest -v
```

### Escopo dos Testes:
* `tests/test_tracking_and_test_send.py`: Injeção de pixel de rastreamento 1x1, rota pública de rastreamento com headers anti-cache, disparo de e-mail de prova (teste) e isolamento multi-tenant de disparo de teste.
* `tests/test_presets.py`: Catálogo de templates prontos, compilação de HTML semântico, aplicação de cores e estilos.
* `tests/test_improvements.py`: Sanitização XSS em templates, sanitização de anexos, invalidação de sessões na troca de senha e importação rápida de CSV.
* `tests/test_attachments.py`: Upload de múltiplos anexos, armazenamento isolado e disparo multipart MIME.
* `tests/test_campaigns.py`: Execução de campanhas por lote, disparo em segundo plano via endpoint HTTP com tolerância a falhas e cálculo de métricas.
* `tests/test_isolation.py`: Isolamento rigoroso multi-tenant entre usuários em todas as entidades.
* `tests/test_templates.py`: Interpolação de variáveis dinâmicas e fallbacks.
* `tests/test_auth.py`: Fluxos de registro, login, cookies HMAC e rejeição de tokens adulterados.
* `tests/test_validation.py`: Validação de sintaxe RFC 5322 e ciclo de vida de contatos.
* `tests/test_unsubscribe.py`: Descadastro público por token e bloqueio automático em novos envios.
* `tests/test_web_integration.py`: Jornada web completa e proteção de rotas privadas.

---

## 🗺️ 7. Roadmap & Próximos Passos

- [x] Construtor Visual de Templates Sem Código (*Zero HTML*)
- [x] Catálogo de Presets Prontos & Personalização de Cores
- [x] Prévia Fixa ao Vivo com Alternador Desktop / Mobile
- [x] Nova Identidade Visual SaaS Profissional
- [x] Suporte a Múltiplos Anexos por Campanha
- [x] Rastreamento de Abertura (Pixel 1x1 Transparente & Taxa de Abertura)
- [x] Disparo de Prova / Envio de Teste com Simulação de Variáveis
- [ ] Fila Assíncrona de Disparos em Segundo Plano (Celery / Redis)
- [ ] Redirecionamento e Rastreamento de Cliques em Links
- [ ] Agendamento Programado de Campanhas (Data e Hora)
- [ ] Segmentação Avançada de Contatos por Tags (`VIP`, `Lead`, `Cliente`)
- [ ] Provedores Nativos em Nuvem (Amazon SES, SendGrid, Mailgun via API REST)

---

## 📄 Licença

Distribuído sob a licença MIT. Consulte `LICENSE` para mais informações.
