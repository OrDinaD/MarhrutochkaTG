#!/usr/bin/env python3
"""
Пример использования WebApp URL с параметрами
"""

def create_webapp_url_example(direction: str = None, date: str = None) -> str:
    """Создает URL для веб-приложения маршруточки с параметрами"""
    base_url = "https://билет.маршруточка.бел/"
    
    params = []
    
    if direction and direction not in ["general", "both", "all"]:
        direction_map = {
            "minsk_ostrovets": "from=minsk&to=ostrovets",
            "ostrovets_minsk": "from=ostrovets&to=minsk",
            "minsk_smorgon": "from=minsk&to=smorgon",
            "smorgon_minsk": "from=smorgon&to=minsk",
            "ostrovets_smorgon": "from=ostrovets&to=smorgon",
            "smorgon_ostrovets": "from=smorgon&to=ostrovets"
        }
        
        if direction in direction_map:
            params.append(direction_map[direction])
    
    if date:
        params.append(f"date={date}")
    
    if params:
        return f"{base_url}#{'&'.join(params)}"
    
    return base_url


if __name__ == "__main__":
    print("Примеры URL для WebApp:")
    print()
    
    # Пример 1: Минск → Островец на конкретную дату
    url1 = create_webapp_url_example("minsk_ostrovets", "2025-11-25")
    print(f"1. Минск → Островец, 25 ноября 2025:")
    print(f"   {url1}")
    print()
    
    # Пример 2: Островец → Минск без даты
    url2 = create_webapp_url_example("ostrovets_minsk")
    print(f"2. Островец → Минск (без даты):")
    print(f"   {url2}")
    print()
    
    # Пример 3: Минск → Сморгонь с датой
    url3 = create_webapp_url_example("minsk_smorgon", "2025-12-01")
    print(f"3. Минск → Сморгонь, 1 декабря 2025:")
    print(f"   {url3}")
    print()
    
    # Пример 4: Без параметров (обычный вход)
    url4 = create_webapp_url_example()
    print(f"4. Главная страница (без параметров):")
    print(f"   {url4}")
    print()
    
    print("=" * 60)
    print("Как читать параметры на сайте (JavaScript):")
    print("=" * 60)
    print("""
const hash = window.location.hash.substring(1);
if (hash) {
    const params = new URLSearchParams(hash);
    const from = params.get('from');      // 'minsk'
    const to = params.get('to');          // 'ostrovets'
    const date = params.get('date');      // '2025-11-25'
    
    // Автозаполнение формы
    if (from && to) {
        selectRoute(from, to);
        if (date) setDate(date);
        searchRoutes();  // Автоматический поиск
    }
}
    """)
