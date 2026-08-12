# Política de segurança

## Como relatar

Não abra uma issue pública para vulnerabilidades. Envie um relato privado ao mantenedor do repositório, incluindo impacto, passos de reprodução e uma correção sugerida quando possível.

## Modelo de proteção

- Senhas usam Argon2 como algoritmo preferencial.
- Sessões usam cookies `HttpOnly`, `SameSite=Lax` e `Secure` em produção.
- Toda mutação feita pelo navegador exige CSRF.
- API tem throttling distinto para autenticação, publicação e IA.
- Cabeçalhos CSP, HSTS, X-Frame-Options e Permissions-Policy reduzem superfícies do navegador.
- Mensagens e chaves Pix são cifradas em repouso com Fernet.
- Segredos só são aceitos por variáveis de ambiente.
- Autorização de objeto impede editar posts e conversas de terceiros.

## Limites honestos

A proteção das mensagens é **criptografia em repouso**, e não criptografia ponta a ponta. O servidor precisa decifrar o conteúdo para entregar a participantes autenticados. Antes de um lançamento comercial, o projeto ainda requer auditoria independente, política LGPD, moderação, backups testados, observabilidade, antivírus para uploads e um provedor TURN autenticado para chamadas WebRTC.
