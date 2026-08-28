# PULSO Android + Meu Pulso widget

Esta pasta contém a camada Android fina do PULSO. O produto continua sendo servido pelo backend/web existente; o aplicativo nativo hospeda essa experiência e adiciona recursos que uma PWA não consegue oferecer diretamente, como um widget de tela inicial.

## Arquitetura

- `MainActivity`: WebView restrito ao domínio oficial do PULSO, com upload de arquivos e permissões sob demanda para câmera/microfone.
- `PulsoAndroid` JS bridge: expõe apenas ações nativas pequenas (`requestPinWidget` e `refreshWidget`) para páginas do próprio PULSO.
- `PulsoWidget`: widget Jetpack Glance responsivo, com tamanhos compacto e 4×2.
- `/api/v1/widget/summary/`: endpoint autenticado e `no-store` que retorna somente contagens e categorias de atividade. Não retorna corpo de mensagem, trecho de post, Pix, e-mail, username ou nome de perfil.
- Deep links do widget: Feed, Mensagens, Atividade e Criar publicação.

## Sessão

A primeira versão compartilha a sessão criada no WebView através do `CookieManager` do Android. O cookie não é copiado para SharedPreferences nem escrito em arquivos próprios do widget. Sem sessão válida, o widget mostra somente a instrução para abrir o PULSO.

## Atualização

O launcher pode solicitar atualização periodicamente (metadados atuais: até uma vez por hora). Quando o PULSO está aberto, a camada nativa também solicita atualização das instâncias do widget. A interface nunca reutiliza conteúdo textual antigo de mensagens ou posts.

## Build local

Requisitos: JDK 17, Android SDK 36 e Gradle 8.13.

```bash
gradle -p android :app:lintDebug :app:assembleDebug
```

O CI gera `android/app/build/outputs/apk/debug/app-debug.apk` como artefato de teste. Assinatura de release/Play Store não está configurada nesta etapa.

## Identidade do pacote

O identificador inicial é `com.labyrt.pulso`. Ele deve ser tratado como candidato para a primeira publicação; antes de uma release pública na Play Store, confirme que este é o application ID definitivo, pois trocar o ID depois de publicar cria outro aplicativo para a loja.
