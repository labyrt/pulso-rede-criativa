# PULSO — PWA + experiência mobile ao vivo

## Escopo desta fase

- Instalação como PWA com identidade PULSO e modo `standalone`.
- Service Worker na raiz com fallback offline seguro.
- Nenhum cache de APIs, autenticação, admin, mensagens, pagamentos ou documentos autenticados.
- Ícones 192, 512, maskable e Apple Touch Icon.
- Seção móvel **Gente para conhecer** em formato horizontal.
- Badges ao vivo para atividade e mensagens.
- Canal WebSocket autenticado por usuário (`/ws/events/`).
- Eventos em tempo real para novas publicações de pessoas seguidas, mensagens e ligações.
- Sinalização WebRTC de chamadas pelo canal pessoal para permitir ligação recebida fora da tela da conversa.
- Permissão de notificações explicitamente opt-in pelo usuário.

## Segurança e privacidade

O Service Worker não intercepta nem persiste respostas de `/api/`, `/accounts/` ou `/admin/`. Navegações usam a rede e só recebem a tela offline quando a conexão falha. O canal realtime valida autenticação, participação na conversa e bloqueios antes de encaminhar sinais de chamada. Falhas do Redis não anulam a ação principal: publicação, mensagem e chamada permanecem persistidas e a entrega ao vivo é tratada como best effort.

Notificações de mensagem não transportam o conteúdo da mensagem. O sistema informa apenas que existe uma nova mensagem e direciona a pessoa ao PULSO.

## Limite desta entrega

As notificações do sistema funcionam a partir dos eventos WebSocket enquanto a aplicação está ativa ou mantida viva pelo navegador. Push confiável com o PULSO totalmente encerrado exige Web Push com inscrição Push API + chaves VAPID no ambiente de produção; isso deve ser ativado como uma etapa separada, com segredos somente no ambiente do Render.

## Validação antes do merge

- `python manage.py check --deploy`
- suíte completa de testes Django
- testes de manifest, Service Worker, assets e sinais de posts/chamadas
- revisão manual em Android/Chrome e iOS/Safari após preview/deploy controlado
- teste com duas contas para mensagem e chamada em telas diferentes
