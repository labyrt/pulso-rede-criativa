# Privacidade: contas internas e bloqueio

- Contas administrativas (`is_staff` / `is_superuser`) não entram em descoberta, perfil público, conexões, comentários públicos ou superfícies sociais.
- A conta `labyrt_admin` é marcada como oculta pela migration de dados `0004_hide_internal_profiles`.
- Quem bloqueia outra pessoa deixa de seguir e remove o follow recíproco existente.
- Pessoas bloqueadas deixam de aparecer mutuamente em descoberta, feed e conexões.
- O bloqueador pode reabrir o perfil bloqueado apenas para desfazer o bloqueio; quem foi bloqueado não acessa o perfil de quem bloqueou.
- Conversas anteriores permanecem legíveis como histórico, mas não aceitam novas mensagens ou chamadas enquanto houver bloqueio.
