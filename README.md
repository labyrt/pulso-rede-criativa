<div align="center">

# PULSO

### Rede social para quem transforma ideia em linguagem

**Crie · conecte · colabore · apoie**

[Aplicação online](https://pulso-rede-criativa.onrender.com) · [API Swagger](#api-rest) · [Arquitetura](#arquitetura) · [Segurança](#segurança-e-privacidade)

</div>

---

PULSO é uma rede social brasileira pensada para fotógrafos, nail artists, cabeleireiros, designers, desenvolvedores, tatuadores, músicos, pintores e pessoas de todas as expressões criativas. O projeto combina publicação de portfólio, descoberta, conexões profissionais, apoio direto e conversas em tempo real em uma experiência original e responsiva.

Este é o projeto final do curso de Python da EBAC. Ele cumpre os requisitos de autenticação, perfil, sistema de seguidores, feed, curtidas, comentários, API REST e deploy — e amplia o escopo com uma base de produto contemporânea.

## O que já funciona

### Comunidade

- cadastro e login por sessão segura;
- login social preparado para Google, GitHub, LinkedIn, Instagram e Adobe/Behance, ativado apenas quando as credenciais oficiais existem no ambiente;
- perfil editável com nome, senha, bio, upload de foto e capa, área criativa, localização, portfólio e redes sociais;
- seguir/deixar de seguir, listas de seguidores e seguidos;
- bloqueio de usuários com remoção automática das conexões;
- feed estrito: exibe publicações apenas de pessoas seguidas;
- exploração de trabalhos por categoria, texto, tags e criador;
- posts de até 500 caracteres com upload direto de imagem, vídeo, tags e link de portfólio;
- curtidas, comentários/respostas, reposts e favoritos;
- notificações de conexões e interações.

### Conversa e colaboração

- conversas diretas privadas com identificação inequívoca de remetente e destinatário;
- mensagens em tempo real com Django Channels/WebSocket;
- conteúdo das mensagens cifrado em repouso;
- indicação de digitação e leitura;
- chamadas de áudio e vídeo peer-to-peer com WebRTC;
- STUN padrão e suporte configurável a TURN para redes restritivas.

### Economia criativa e IA

- chave Pix cifrada no perfil;
- QR Code Pix Copia e Cola no perfil e em cada publicação que aceite apoio, com valor opcional;
- transferência ocorre diretamente entre apoiador e criador: a PULSO não custodia valores;
- assistente editorial de legendas com Gemini quando a chave está configurada;
- fallback local funcional quando não há Gemini, sem quebrar o produto;
- rate limit próprio para IA para evitar abuso e consumo inesperado.

## Experiência visual

A interface é autoral. A direção combina tipografia editorial, superfícies de cor sólida, espaços generosos, alto contraste e microinterações discretas. O produto não copia componentes ou identidade de outra rede. Há temas claro e escuro, tooltips, modo responsivo completo e respeito a `prefers-reduced-motion` para acessibilidade.

## Arquitetura

```mermaid
flowchart TD
    UI["Templates + JavaScript"] --> API["Django REST Framework"]
    UI --> WS["Channels / WebSocket"]
    UI --> RTC["WebRTC áudio e vídeo"]
    API --> DB["PostgreSQL ou SQLite"]
    API --> GEM["Gemini opcional"]
    WS --> REDIS["Redis Channel Layer"]
    API --> PIX["Gerador Pix local"]
```

| Módulo | Responsabilidade |
|---|---|
| `apps/accounts` | usuário, perfil, seguidores, bloqueios e autenticação |
| `apps/social` | posts, comentários, curtidas, reposts, favoritos e notificações |
| `apps/chat` | conversas, mensagens cifradas, WebSocket e sinalização WebRTC |
| `apps/payments` | payload/QR Pix e intenções de apoio sem custódia financeira |
| `apps/assistant` | assistente editorial Gemini com fallback local |
| `apps/webapp` | páginas, shell visual, middleware e tratamento uniforme de erros |

## Tecnologias

- Python 3.12, Django 5.2 e Django REST Framework;
- Django Channels, Daphne e Redis;
- PostgreSQL em produção e SQLite no desenvolvimento;
- JavaScript moderno, WebSocket e WebRTC;
- Google GenAI SDK opcional;
- Argon2, Fernet, CSP, CSRF, throttling e permissões por objeto;
- Docker, Render Blueprint e GitHub Actions.

## Rodando localmente

```bash
git clone https://github.com/labyrt/pulso-rede-criativa.git
cd pulso-rede-criativa
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Acesse `http://127.0.0.1:8000`. Os dados de demonstração são descritos pelo comando `seed_demo` e nunca devem ser usados em produção.

Para testar o servidor ASGI e o chat exatamente como em produção:

```bash
daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

## Testes

```bash
python manage.py test --verbosity 2
python manage.py check --deploy
```

A suíte cobre cadastro e senha, perfil parcial, criptografia do Pix, seguir/deixar de seguir, feed restrito, autorização de posts, validação, curtidas, comentários, favoritos, reposts, identidade e isolamento de conversas, criptografia de mensagens, upload assinado no Cloudinary, QR Pix, login social e fallback de IA.

## API REST

A documentação navegável fica em `/api/docs/` e o schema OpenAPI em `/api/schema/`.

Rotas principais:

| Método e rota | Ação |
|---|---|
| `POST /api/v1/auth/register/` | criar conta |
| `POST /api/v1/auth/login/` | iniciar sessão |
| `POST /api/v1/auth/logout/` | encerrar sessão |
| `GET/PATCH /api/v1/auth/me/` | consultar ou editar perfil |
| `POST /api/v1/auth/profiles/{username}/follow/` | alternar seguir |
| `GET /api/v1/social/feed/` | feed de pessoas seguidas |
| `GET/POST /api/v1/social/posts/` | listar/criar posts |
| `POST /api/v1/social/posts/{id}/like/` | alternar curtida |
| `GET/POST /api/v1/social/posts/{id}/comments/` | comentários |
| `GET/POST /api/v1/chat/conversations/` | conversas privadas |
| `WS /ws/chat/{id}/` | mensagens e sinalização em tempo real |
| `GET /api/v1/support/{username}/pix/` | payload e QR Pix |
| `POST /api/v1/ai/caption/` | sugestão editorial |

## Configuração

Copie `.env.example` e ajuste as variáveis. Nunca envie o `.env` ao GitHub.

| Variável | Uso |
|---|---|
| `DJANGO_SECRET_KEY` | assinatura criptográfica do Django |
| `DATABASE_URL` | PostgreSQL; ausente usa SQLite local |
| `REDIS_URL` | Channels e cache; ausente usa memória local |
| `FIELD_ENCRYPTION_KEY` | chave Fernet para mensagens e Pix |
| `CLOUDINARY_URL` | armazenamento persistente para uploads de imagens em produção |
| `GEMINI_API_KEY` | habilita IA; é opcional e fica apenas no servidor |
| `WEBRTC_TURN_*` | credenciais para chamadas em redes restritivas |
| `GOOGLE_OAUTH_CLIENT_ID/SECRET` | login com Google |
| `GITHUB_OAUTH_CLIENT_ID/SECRET` | login com GitHub |
| `LINKEDIN_OAUTH_CLIENT_ID/SECRET` | login com LinkedIn |
| `INSTAGRAM_OAUTH_CLIENT_ID/SECRET` | login com Instagram para contas elegíveis |
| `ADOBE_OAUTH_CLIENT_ID/SECRET` | login Adobe ID para pessoas que usam Behance |

### Ativando login social

Crie um aplicativo OAuth em cada provedor desejado e registre os callbacks HTTPS abaixo. Os segredos ficam somente nas variáveis do Render; nunca no código, banco público ou JavaScript.

| Provedor | Callback de produção |
|---|---|
| Google | `https://pulso-rede-criativa.onrender.com/accounts/google/login/callback/` |
| GitHub | `https://pulso-rede-criativa.onrender.com/accounts/github/login/callback/` |
| LinkedIn | `https://pulso-rede-criativa.onrender.com/accounts/linkedin_oauth2/login/callback/` |
| Instagram | `https://pulso-rede-criativa.onrender.com/accounts/instagram/login/callback/` |
| Adobe / Behance | `https://pulso-rede-criativa.onrender.com/accounts/oidc/adobe/login/callback/` |

O Instagram restringe o acesso de API conforme o tipo e a aprovação do aplicativo. Adobe/Behance usa Adobe ID via OpenID Connect; não existe um login Behance independente no Django Allauth. Quando as credenciais de um provedor estão ausentes, o botão permanece visível, porém inativo, em vez de iniciar um fluxo quebrado.

Gere uma chave Fernet com:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Segurança e privacidade

- Argon2 é o hasher de senha preferencial;
- cookies de sessão são `HttpOnly`, `Secure` em produção e `SameSite=Lax`;
- CSRF obrigatório nas mutações do navegador;
- CSP, HSTS, X-Frame-Options e Permissions-Policy;
- limites diferentes para anônimos, usuários, login, posts e IA;
- mensagens e chaves Pix cifradas em repouso;
- autorização de objeto e bloqueios aplicados no backend;
- nenhuma chave secreta é enviada ao frontend;
- uploads aceitam somente JPG, PNG e WebP válidos, com limite de 8 MB;
- a IA só recebe o rascunho depois de uma ação explícita da pessoa.

Consulte [SECURITY.md](SECURITY.md) para limites e processo de relato.

> **Transparência:** mensagens cifradas em repouso não são E2EE. Para lançar comercialmente, são necessários auditoria externa, moderação, termos e política LGPD, backups testados, armazenamento de mídia gerenciado, monitoramento e TURN próprio. O código foi preparado para esses próximos passos, sem prometer segurança que ainda não foi auditada.

## Deploy

O repositório inclui `render.yaml`, `build.sh` e `Dockerfile`. No Render, crie um Blueprint a partir deste repositório; banco PostgreSQL e Redis serão vinculados por variáveis. Para persistir os uploads no plano gratuito, configure `CLOUDINARY_URL` como segredo no serviço. `GEMINI_API_KEY` e as credenciais TURN continuam opcionais.

No plano gratuito, o Render não disponibiliza Shell. Para criar o primeiro
administrador, adicione temporariamente `DJANGO_SUPERUSER_USERNAME`,
`DJANGO_SUPERUSER_EMAIL` e `DJANGO_SUPERUSER_PASSWORD` às variáveis secretas
do serviço e faça um novo deploy. O `build.sh` cria a conta somente quando ela
ainda não existe; depois do primeiro login, remova essas três variáveis.

Produção: **https://pulso-rede-criativa.onrender.com**.

## Roadmap de produto

- vídeos enviados diretamente e processamento assíncrono de mídia;
- moderação e denúncias com painel de confiança e segurança;
- E2EE real com gerenciamento de chaves no cliente;
- chamadas em grupo e TURN gerenciado;
- PWA, notificações push e aplicativo móvel;
- Pix Cobrança via PSP homologado e webhooks;
- busca vetorial e recomendações com consentimento;
- internacionalização e recursos avançados de acessibilidade.

---

Desenvolvido por **Lucy Mazzini (Labyrt)** como projeto final de Python — EBAC.
