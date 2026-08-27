# Incidente: feed preso no mobile — 2026-08-27

## Evidência

A telemetria de produção registrou `watchdog_loaded` e `recovery_armed`, mas não registrou `recovery_started` nem `recovery_deadline` durante uma reprodução real no Android. O backend e o Neon estavam saudáveis.

## Causa

O timer do fallback era cancelado e rearmado em mutações do DOM. Como outros scripts também alteram a árvore de `#page-content`, o prazo de recuperação podia ser adiado indefinidamente e deixar o spinner visível.

## Correção

O watchdog passa a usar um prazo absoluto que não é reiniciado por mutações do DOM. O fallback usa somente requisições GET, pode concluir mesmo com a aba em segundo plano e ainda respeita a renderização normal quando ela termina antes do prazo.
