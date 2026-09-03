# KirLat

Малка програма за Windows и macOS, която седи в системния трей (лентата с менюта на Mac) и при
натискане на избрана клавишна комбинация (по подразбиране **Ctrl+W**) заменя селектирания текст
в която и да е програма:

- `Zdrawej kak si` → `Здравей как си`
- `Здравей как си` → `Zdrawej kak si`

Посоката се познава автоматично по преобладаващата азбука. Работи с всички български подредби:
Фонетична (традиционна), Фонетична (нова, БДС 2006), БДС и Пишеща машина. Една и съща кодова база
се билдва до `KirLat.exe` (Windows) и `KirLat.app` (macOS).

## Инсталиране

### Windows

**Вариант 1 – сваляне:** изтеглете [KirLat.exe](https://github.com/NPashofff/KirLat/releases/latest/download/KirLat.exe)
и го стартирайте. Иконата се появява в трея. Автостартът се включва от настройките.

**Вариант 2 – една команда** (PowerShell): сваля последната версия в `%LOCALAPPDATA%\KirLat`,
добавя пряк път в Start менюто, включва автостарт и стартира приложението.

```powershell
irm https://raw.githubusercontent.com/NPashofff/KirLat/main/install.ps1 | iex
```

Деинсталиране:

```powershell
irm https://raw.githubusercontent.com/NPashofff/KirLat/main/uninstall.ps1 | iex
```

### macOS

**Вариант 1 – сваляне:** изтеглете [KirLat-macOS.zip](https://github.com/NPashofff/KirLat/releases/latest/download/KirLat-macOS.zip),
разархивирайте и преместете `KirLat.app` в `/Applications`. При първо стартиране, ако macOS каже,
че приложението е от неизвестен разработчик: десен бутон → Open, или в терминала
`xattr -dr com.apple.quarantine /Applications/KirLat.app`.

**Вариант 2 – една команда** (Terminal): сваля готовия билд, слага го в `/Applications`,
включва автостарт и го стартира.

```bash
curl -fsSL https://raw.githubusercontent.com/NPashofff/KirLat/main/install.sh | bash
```

Деинсталиране:

```bash
curl -fsSL https://raw.githubusercontent.com/NPashofff/KirLat/main/uninstall.sh | bash
```

**И в двата случая** macOS ще поиска разрешения *System Settings → Privacy & Security →
Accessibility* и *Input Monitoring* за KirLat. Без тях нищо не работи. След като ги дадете,
рестартирайте приложението.

## Как работи

При натискане на комбинацията програмата:
1. запомня текущия клипборд;
2. симулира Ctrl+C (Cmd+C на Mac), за да вземе селекцията;
3. преобразува текста по избраната подредба;
4. симулира Ctrl+V (Cmd+V), за да го замени;
5. връща стария клипборд (може да се изключи от настройките).

Самата комбинация се „поглъща“, т.е. програмата под курсора не я получава (Ctrl+W няма да
затвори таба в браузъра).

## Готови билдове

- Windows: `dist\KirLat.exe` (създава се с `build_windows.ps1`)
- macOS: `dist/KirLat.app` (създава се с `build_macos.sh`, **изпълнява се на Mac**)

## Стартиране от изходния код

Нужен е Python 3.10+ (на Windows – от python.org, с включен tkinter).

```bash
pip install -r requirements.txt
python main.py            # стартира в трея
python main.py --settings # само прозорецът с настройки
python main.py --convert "Zdrawej"   # проба в конзолата
```

На Windows, за да няма конзолен прозорец, стартирайте с `pythonw main.py`.

## Билд

### Windows

```powershell
.\build_windows.ps1
```

Резултат: `dist\KirLat.exe` (единичен файл, без конзола).

### macOS

```bash
chmod +x build_macos.sh
./build_macos.sh
```

Резултат: `dist/KirLat.app`. Копирайте го в `/Applications`. Приложението няма икона в Dock
(`LSUIElement`), само в лентата с менюта.

**Разрешения на macOS (задължително):** при първо стартиране macOS ще поиска
*System Settings → Privacy & Security → Accessibility* и *Input Monitoring* за KirLat.
Без тях нито клавишната комбинация, нито симулираното Cmd+C/Cmd+V работят. След промяна на
разрешенията рестартирайте приложението.

## Настройки

Десен бутон върху иконата в трея → **Настройки…** (или двоен клик). Там се задават:

- клавишната комбинация – модификатори (Ctrl / Alt(Option) / Shift / Win(Cmd)) + клавиш;
- българската подредба, която ползвате;
- посоката (автоматично / само към кирилица / само към латиница);
- автоматично стартиране при вход в системата;
- дали да се възстановява клипбордът след замяната;
- поле за проба, което показва резултата на живо.

Промените се прилагат веднага, без рестарт. Настройките се пазят в:

- Windows: `%APPDATA%\KirLat\config.json`
- macOS: `~/Library/Application Support/KirLat/config.json`

Дневник с грешки: `kirlat.log` в същата папка.

## Автостарт

- Windows: запис в `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- macOS: `~/Library/LaunchAgents/com.kirlat.app.plist`

Включва се от настройките или от менюто в трея.

## Структура

```
main.py                 стартов файл (--settings / --convert)
kirlat/layouts.py       таблици на подредбите (извлечени от реалните Windows подредби)
kirlat/converter.py     преобразуване + автоматично разпознаване на посоката
kirlat/hotkey.py        глобална клавишна комбинация (Windows hook / macOS CGEventTap)
kirlat/actions.py       копиране → преобразуване → поставяне
kirlat/tray.py          икона и меню в трея, презареждане на настройките
kirlat/settings_gui.py  прозорец с настройки (tkinter, отделен процес)
kirlat/autostart.py     автостарт (Registry / LaunchAgent)
KirLat.spec             PyInstaller спецификация за двете платформи
tests/                  unit тестове + жив тест (tests/live_test.py)
```

## Известни ограничения

- Ако в клипборда има изображение (не текст), след замяната то не се възстановява.
- Програми, които не поддържат Ctrl+C / Ctrl+V за селекцията (някои терминали), няма да работят.
- Ако друга програма вече е заела същата комбинация глобално, изберете друга.
