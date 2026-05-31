import sys
import time
import json
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup


def parse_mirkvartir_and_update_baza(url, baza_path='baza.json'): 
    """
    параметр в бд - rent_1room_apartment_rub
    """
    # Словарь оставляем строго — не парсим, только используем
    region_to_capital = {
        "Краснодарский край (Индустриальный парк Краснодар)": "Краснодар",
        "Краснодарский край (Индустриальный парк Армавир)": "Краснодар",
        "Ростовская область (ОЭЗ ППТ Ростовская, Новочеркасск)": "Ростов-на-Дону",
        "Ростовская область (Азовский индустриальный парк)": "Ростов-на-Дону",
        "Свердловская область (ОЭЗ ППТ Титановая долина, Верхняя Салда)": "Екатеринбург",
        "Свердловская область (Индустриальный парк Уральский, Екатеринбург)": "Екатеринбург",
        "Республика Татарстан (ОЭЗ ППТ Алабуга)": "Казань",
        "Республика Татарстан (Индустриальный парк Лаишево)": "Казань",
        "Новосибирская область (Индустриальный парк Нова)": "Новосибирск",
        "Новосибирская область (Индустриальный парк ПЛП)": "Новосибирск",
        "Калужская область (ОЭЗ ППТ Калуга - Людиново)": "Калуга",
        "Калужская область (Индустриальный парк Ворсино)": "Калуга",
        "Липецкая область (ОЭЗ ППТ Липецк - Грязинская площадка)": "Липецк",
        "Липецкая область (Индустриальный парк «Кузнецкая слобода»)": "Липецк",
        "Московская область (ОЭЗ ТВТ Дубна)": "Москва",
        "Республика Башкортостан (ОЭЗ ППТ «Алга»)": "Уфа",
        "Республика Башкортостан (Индустриальный парк «Уфимский»)": "Уфа",
        "Самарская область (ОЭЗ ППТ «Тольятти»)": "Самара",
        "Самарская область (Индустриальный парк «Преображенка»)": "Самара",
        "Московская область (Индустриальный парк «Ступино Квадрат»)": "Москва",
    }

    # Берём имя поля в базе из докстринга функции
    doc = parse_mirkvartir_and_update_baza.__doc__ or ''
    if '-' in doc:
        bd_param = doc.split('-', 1)[1].strip()
    else:
        # fallback
        m = re.search(r'rent_[a-z0-9_]+', doc)
        bd_param = m.group(0) if m else 'rent_1room_apartment_rub'

    print("[1/5] Запуск фонового браузера Playwright...", flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 1000}
        )
        page = context.new_page()

        def block_aggressively(route):
            url_str = route.request.url.lower()
            if any(x in url_str for x in ["google", "yandex", "mc.yandex", "gtm", "counter", ".png", ".jpg", ".jpeg", ".gif"]):
                return route.abort()
            return route.continue_()

        page.route("**/*", block_aggressively)

        try:
            print(f"[2/5] Подключение к сайту: {url}", flush=True)
            page.goto(url, wait_until="domcontentloaded", timeout=20000)

            print("[3/5] Ждем появления таблицы на странице...", flush=True)
            page.wait_for_selector("table", timeout=10000)
            time.sleep(2)

            html_content = page.content()
            soup = BeautifulSoup(html_content, "html.parser")

            print("[4/5] Анализ HTML таблицы...", flush=True)
            table = soup.find("table")
            if not table:
                print("[ОШИБКА]: Таблица не найдена на странице!", file=sys.stderr, flush=True)
                return

            rent_dict = {}
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue
                city = cells[1].get_text(strip=True)
                price_raw = cells[2].get_text(strip=True)
                if "город" in city.lower() or "№" in city.lower() or not price_raw:
                    continue
                price_clean = "".join([char for char in price_raw if char.isdigit()])
                if city and price_clean:
                    rent_dict[city] = int(price_clean)

            print("[5/5] Обработка завершена!\n", flush=True)

            # Обновляем baza.json — заменяем параметр для соответствующих регионов
            try:
                with open(baza_path, 'r', encoding='utf-8') as f:
                    baza = json.load(f)

                updated = 0
                for region in baza.get('regions', []):
                    name = region.get('name')
                    if not name:
                        continue
                    capital = region_to_capital.get(name)
                    if not capital:
                        continue
                    if capital in rent_dict:
                        if 'social' not in region or not isinstance(region['social'], dict):
                            region['social'] = {}
                        region['social'][bd_param] = rent_dict[capital]
                        updated += 1

                if updated:
                    with open(baza_path, 'w', encoding='utf-8') as f:
                        json.dump(baza, f, ensure_ascii=False, indent=2)
                print(f"Обновлено регионов в базе: {updated}")
            except Exception as e:
                print(f"Ошибка при обновлении {baza_path}: {e}", file=sys.stderr, flush=True)

        except Exception as e:
            print(f"\n[КРИТИЧЕСКАЯ ОШИБКА]: {e}", file=sys.stderr, flush=True)
        finally:
            browser.close()

if __name__ == "__main__":
    target_url = "https://www.mirkvartir.ru/journal/analytics/2026/05/17/arenda-v-aprele/"
    parse_mirkvartir_and_update_baza(target_url)