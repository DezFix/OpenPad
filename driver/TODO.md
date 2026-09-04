# OpenPad Virtual Mic — TODO (⛔ ПАУЗА: нет денег на подпись)

> Решение: свой драйвер заморожен. Причина — релизная подпись
> (EV-сертификат ~$200–500/год + Partner Center) сейчас не по карману,
> а без неё драйвер встанет только в test-режиме.
> Основной путь — **виртуальный аудио кабель (VB-Cable)**:
> установка в 1 клик прямо из OpenPad (Помощь → Установить VB-Cable),
> см. `src/openpad/cable_setup.py`.
> CI остаётся зелёным для будущего — когда появятся деньги/мейнтейнер,
> продолжить с шага 2.

## Шаг 0. Стенд (нужен отдельный ПК или готовность к ребутам)

- Windows 10/11 x64, права админа, точка восстановления.
- Для **тестовых** сборок: `bcdedit /set testsigning on` + ребут
  (на обоях появится «Test Mode», Secure Boot может мешать —
  для проб проще всего тестовый ПК/виртуалка).

## Шаг 1. Тулчейн

1. Visual Studio 2022 (Community хватит) + workload
   «Desktop development with C++».
2. Windows Driver Kit (WDK) под версию VS + Spectre-mitigated libs.
3. Проверить: собирается ли чистый сэмпл
   `Microsoft/Windows-driver-samples` → `audio/sysvad`
   (TabletAudioSample). Если да — тулчейн ок.

## Шаг 2. Урезанный драйвер OpenPadCable

База — SysVAD TabletAudioSample, выкинуть лишнее:

- оставить 1 render endpoint `OpenPad Speakers`
  + 1 capture endpoint `OpenPad Microphone`, связанные loopback;
- формат на старте: 48 кГц / 16-bit / stereo;
- переименовать все строки endpoints в `OpenPad ...`;
- INF: `driver/inf/OpenPadCable.inf` (взять за основу INF сэмпла,
  поменять HWID на `Root\OpenPadCable`, вендора, имена);
- собрать x64 (+ ARM64 позже), тестовые сборки подписать
  тест-сертификатом (`MakeCert`/`New-SelfSignedCertificate`).

Критерий готовности шага: `pnputil /add-driver ... /install`
в test mode проходит, в `mmsys.cpl` видны оба endpoint'а.

## Шаг 3. Интеграция с Python

- `driver/install.bat` уже готов (зовёт pnputil).
- В OpenPad добавить кнопку «Установить OpenPad Virtual Mic»
  (запуск install.bat от админа) — делать после шага 2.
- Детект `*openpad*` в `devices.py` уже есть.

## Шаг 4. Релизная подпись (блокер для «всех»)

- Сертификат (EV, ~$200–500/год) → Partner Center →
  attestation-подпись → публикация в GitHub Releases.
- Без этого: только test mode для энтузиастов.

## Шаг 5 (позже). Вариант B — APO-инъекция в реальный микрофон

См. раздел в `driver/README.md`. Только после шагов 1–4.
