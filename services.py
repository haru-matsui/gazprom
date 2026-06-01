def normalize_inverse(value, values):
    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        return 1
    result = (max_v - value) / (max_v - min_v)
    return max(0, min(result, 1))
def normalize_direct(value, values):
    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        return 1
    result = (value - min_v) / (max_v - min_v)
    return max(0, min(result, 1))
def calculate_estimate(region, user_input, required_power):
    # Функция: calculate_estimate
    # Входные параметры:
    # - region: словарь с данными по региону (логистика, инфраструктура, экономика, социальные параметры)
    # - user_input: словарь с входными данными от пользователя (production_volume, employees, housing и т.д.)
    # - required_power: требуемая мощность для производства (кВА)
    # Функция вычисляет планируемые площади (м2) для разных объектов, затем оценивает
    # CapEx и OpEx и возвращает детализированную смету и разбиение по статьям.
    logistics = region["logistics"]
    infra = region["infrastructure"]
    econ = region["economics"]
    # Входные значения из user_input
    production_volume = user_input["production_volume"]  # V — объём производства (тыс. м²/год)
    employees = user_input["employees"]  # N — количество сотрудников

    # Новые формулы расчёта площадей (соответствуют спецификации):
    # Цех: V * 4
    shop_area = production_volume * 4
    # Склад: цех * 0.35
    warehouse_area = shop_area * 0.35
    # АБК: цех * 0.02
    abk_area = shop_area * 0.04
    housing_percent = user_input["housing"]["percent"] / 100
    housing_type = user_input["housing"]["type"]
    if housing_type == "общежитие":
        housing_per_person = 25
        housing_cost_per_m2 = 65000
    else:
        housing_per_person = 42
        housing_cost_per_m2 = 90000
    # Корпоративное жильё: площадь на сотрудника зависит от типа жилья (T)
    # - квартира: 40 м2 на человека
    # - общежитие: 25 м2 на человека
    # P (housing_percent) — процент сотрудников с жильём
    housing_area = employees * housing_percent * housing_per_person
    # Детский сад: (N / 100) * K * 12  (K — места в детском саду на 100 сотрудников, 12 м2 на место)
    kindergarten_k_per_100 = user_input.get("kindergarten_k_per_100", user_input.get("kindergarten_places", 0))
    kindergarten_area = (employees / 100.0) * kindergarten_k_per_100 * 12
    regional_coef = 1.0
    name = region["name"]
    if "Москва" in name: regional_coef = 1.35
    elif "Самарская" in name: regional_coef = 1.12
    elif "Башкортостан" in name: regional_coef = 1.08
    elif "Липецкая" in name: regional_coef = 0.95
    elif "Калужская" in name: regional_coef = 1.03
    shop_cost = shop_area * 32000 * regional_coef
    warehouse_cost = warehouse_area * 32000 * regional_coef
    abk_cost = abk_area * 52000 * regional_coef
    housing_cost = housing_area * housing_cost_per_m2 * regional_coef
    kindergarten_cost = kindergarten_area * 50000 * regional_coef
    # Столовая: N * 0.8
    canteen_area = employees * 0.8
    canteen_cost = canteen_area * 50000 * regional_coef
    # Медпункт: max(20, N * 0.2)
    medical_area = max(20, employees * 0.2)
    medical_cost = medical_area * 55000 * regional_coef
    # Парковка: N * 0.5 * 0.25  (по новой формуле — сразу м2)
    parking_area = employees * 7.5
    parking_cost = parking_area * 3500 * regional_coef
    # Дороги: (цех + склад) * 0.25
    roads_area = (shop_area + warehouse_area) * 0.25
    landscaping_prices = {
        "Сквер с фонтаном": 5_000_000,
        "Беседки": 1_000_000, "Сцена": 3_000_000,
        "Пруд": 6_000_000,
        "Арт-объект": 1_500_000
    }
    landscaping_cost = sum([landscaping_prices.get(i, 0) for i in user_input["landscaping"]])
    sports_prices = {
        "Уличные тренажёры": 1_000_000, "Стадион": 5_000_000,
        "Бассейн": 8_000_000, "Спортзал": 3_000_000,
        "Хоккейная коробка": 2_000_000
    }
    sports_cost = sum([sports_prices.get(i, 0) for i in user_input["sports"]])
    connection_cost = required_power * infra["connection_cost_rub_kwt"]
    capex = (
        shop_cost + warehouse_cost + abk_cost + housing_cost + kindergarten_cost +
        landscaping_cost + sports_cost + connection_cost + canteen_cost + medical_cost + parking_cost
    )
    # Дополнительные расчёты, связанные с площадью производства (для логистики и Opex):
    # production_m2 — общая площадь производства в м2 (здесь 1000 м2 на условную единицу объёма)
    production_m2 = production_volume * 1000
    # Используется эмпирическое соотношение массы стали/полиуретана на 1 м2
    steel_mass = production_m2 * 0.012
    poly_mass = production_m2 * 0.003
    logistics_tariff = 15
    steel_cost = steel_mass * logistics["distance_to_steel_km"] * logistics_tariff
    poly_cost = poly_mass * logistics["distance_to_polyurethane_km"] * logistics_tariff
    salary_cost = employees * econ["average_salary_rub"] * 12
    energy_cost = production_m2 * econ["energy_tariff_rub_kwh"] * 1.5
    ecology_cost = 10_000_000
    opex = steel_cost + poly_cost + salary_cost + energy_cost + ecology_cost
    total_cost = capex + opex

    # CapEx breakdown by groups and buildings
    # Здесь в разбиении CapEx мы используем ранее посчитанные площади и стоимости
    # Каждая строка показывает название объекта, рассчитанную сумму и суммарную группу
    capex_breakdown = [
        {
            "group": "Производственные помещения",
            "items": [
                {"name": "Цех", "amount": round(shop_cost)},
                {"name": "Склад", "amount": round(warehouse_cost)},
            ],
            "total": round(shop_cost + warehouse_cost)
        },
        {
            "group": "Административно-бытовой корпус (АБК)",
            "items": [
                {"name": "АБК", "amount": round(abk_cost)},
                {"name": "Столовая", "amount": round(canteen_cost)},
                {"name": "Медпункт", "amount": round(medical_cost)},
            ],
            "total": round(abk_cost + canteen_cost + medical_cost)
        },
        {
            "group": "Социальная инфраструктура",
            "items": [
                {"name": "Жилые площади (корпоративное жильё)", "amount": round(housing_cost)},
                {"name": "Детский сад", "amount": round(kindergarten_cost)},
                {"name": "Благоустройство / ландшафт", "amount": round(landscaping_cost)},
                {"name": "Спортивные объекты", "amount": round(sports_cost)},
                {"name": "Парковка корпоративного транспорта", "amount": round(parking_cost)},
            ],
            "total": round(housing_cost + kindergarten_cost + landscaping_cost + sports_cost + parking_cost)
        },
        {
            "group": "Инженерные подключения и сеть",
            "items": [
                {"name": "Подключение мощности", "amount": round(connection_cost)},
            ],
            "total": round(connection_cost)
        }
    ]

    # OpEx breakdown (годовые или ориентировочные)
    # В OpEx включены годовые расходы, часть которых зависит от площадей (логистика, энергия)
    opex_breakdown = {
        "items": [
            {"name": "Сталь (логистика)", "amount": round(steel_cost)},
            {"name": "Полиуретан (логистика)", "amount": round(poly_cost)},
            {"name": "Зарплатный фонд (годовой)", "amount": round(salary_cost)},
            {"name": "Энергия (годовой)", "amount": round(energy_cost)},
            {"name": "Экология / прочие", "amount": round(ecology_cost)},
        ],
        "total": round(opex)
    }

    # Возвращаем словарь со всеми ключевыми площадями (в м2) и суммами (CapEx, OpEx).
    # Эти значения затем используются в функции `run_scoring_algorithm` для фильтрации
    # регионов по бюджету и отображения сметы в интерфейсе.
    return {
        "shop_area": round(shop_area),
        "warehouse_area": round(warehouse_area),
        "abk_area": round(abk_area),
        "housing_area": round(housing_area),
        "kindergarten_area": round(kindergarten_area),
        "canteen_area": round(canteen_area),
        "medical_area": round(medical_area),
        "parking_area": round(parking_area),
        "roads_area": round(roads_area),
        "capex": round(capex),
        "opex": round(opex),
        "total_cost": round(total_cost),
        "capex_breakdown": capex_breakdown,
        "opex_breakdown": opex_breakdown
    }
def _build_score_term(label, raw_value, values, weight, mode, value_text, value_unit=""):
    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        normalized = 1
        formula = f"Так как min = max = {min_v}, нормализация = 1"
    elif mode == "inverse":
        normalized = (max_v - raw_value) / (max_v - min_v)
        formula = f"({max_v} - {raw_value}) / ({max_v} - {min_v})"
    else:
        normalized = (raw_value - min_v) / (max_v - min_v)
        formula = f"({raw_value} - {min_v}) / ({max_v} - {min_v})"

    normalized = max(0, min(normalized, 1))
    contribution = normalized * weight
    return {
        "label": label,
        "value": value_text,
        "raw_value": raw_value,
        "raw_unit": value_unit,
        "min": min_v,
        "max": max_v,
        "mode": mode,
        "normalized": round(normalized, 3),
        "weight": weight,
        "contribution": round(contribution, 2),
        "normalization_formula": formula,
    }
def run_scoring_algorithm(user_input_dict: dict, regions: list):
    required_power = user_input_dict["production_volume"] * 1.8
    budget_rub = user_input_dict["budget_mln"] * 1_000_000
    steel_values = [r["logistics"]["distance_to_steel_km"] for r in regions]
    poly_values = [r["logistics"]["distance_to_polyurethane_km"] for r in regions]
    salary_values = [r["economics"]["average_salary_rub"] for r in regions]
    energy_values = [r["economics"]["energy_tariff_rub_kwh"] for r in regions]
    power_values = [r["infrastructure"]["available_power_kva"] for r in regions]
    rent_values = [r["social"]["rent_1room_apartment_rub"] for r in regions]
    env_values = [r["social"]["city_environment_index"] for r in regions]
    weights = {
        "steel": 20, "poly": 20, "salary": 15, "energy": 15,
        "environment": 15, "rent": 10, "power": 15
    }
    housing_percent = user_input_dict["housing"]["percent"]
    if housing_percent >= 70:
        weights["rent"] += 15
        weights["salary"] += 10
    elif housing_percent >= 50:
        weights["rent"] += 10
    filtered_regions = []
    for region in regions:
        logistics = region["logistics"]
        infra = region["infrastructure"]
        railway_mode = user_input_dict["railway_mode"]
        if railway_mode == "required" and not logistics["has_railway"]: continue
        elif railway_mode == "forbidden" and logistics["has_railway"]: continue
        if logistics["distance_to_highway_km"] > user_input_dict["max_distance_to_highway"]:
            continue
        if infra["available_power_kva"] < required_power:
            continue
        filtered_regions.append(region)
    results = []
    for region in filtered_regions:
        logistics = region["logistics"]
        infra = region["infrastructure"]
        econ = region["economics"]
        social = region["social"]
        estimate = calculate_estimate(region, user_input_dict, required_power)
        if estimate["capex"] > budget_rub:
            continue
        score_terms = []
        score = 0

        steel_term = _build_score_term(
            "Расстояние до стали",
            logistics["distance_to_steel_km"],
            steel_values,
            weights["steel"],
            "inverse",
            f"{logistics['distance_to_steel_km']} км",
            "км",
        )
        score += steel_term["contribution"]
        score_terms.append(steel_term)

        poly_term = _build_score_term(
            "Расстояние до полиуретана",
            logistics["distance_to_polyurethane_km"],
            poly_values,
            weights["poly"],
            "inverse",
            f"{logistics['distance_to_polyurethane_km']} км",
            "км",
        )
        score += poly_term["contribution"]
        score_terms.append(poly_term)

        energy_term = _build_score_term(
            "Энерготариф",
            econ["energy_tariff_rub_kwh"],
            energy_values,
            weights["energy"],
            "inverse",
            f"{econ['energy_tariff_rub_kwh']} руб/кВт·ч",
            "руб/кВт·ч",
        )
        score += energy_term["contribution"]
        score_terms.append(energy_term)

        power_term = _build_score_term(
            "Доступная мощность",
            infra["available_power_kva"],
            power_values,
            weights["power"],
            "direct",
            f"{infra['available_power_kva']} кВА",
            "кВА",
        )
        score += power_term["contribution"]
        score_terms.append(power_term)

        salary_term = _build_score_term(
            "Средняя зарплата",
            econ["average_salary_rub"],
            salary_values,
            weights["salary"],
            "inverse",
            f"{econ['average_salary_rub']} руб/мес",
            "руб/мес",
        )
        score += salary_term["contribution"]
        score_terms.append(salary_term)

        rent_term = _build_score_term(
            "Аренда 1-комн. квартиры",
            social["rent_1room_apartment_rub"],
            rent_values,
            weights["rent"],
            "inverse",
            f"{social['rent_1room_apartment_rub']} руб/мес",
            "руб/мес",
        )
        score += rent_term["contribution"]
        score_terms.append(rent_term)

        env_term = _build_score_term(
            "Индекс городской среды",
            social["city_environment_index"],
            env_values,
            weights["environment"],
            "direct",
            f"{social['city_environment_index']}",
        )
        score += env_term["contribution"]
        score_terms.append(env_term)

        oez_bonus = 5 if econ["has_oez_benefits"] else 0
        insurance_bonus = 3 if econ["has_insurance_benefits"] else 0
        railway_bonus = 2 if logistics["has_railway"] else 0

        score += oez_bonus
        score += insurance_bonus
        score += railway_bonus

        score_terms.append({
            "label": "Льготы ОЭЗ",
            "value": "есть" if econ["has_oez_benefits"] else "нет",
            "normalized": None,
            "weight": 0,
            "contribution": round(oez_bonus, 2),
            "explanation": "Постоянная надбавка за наличие льгот ОЭЗ",
        })
        score_terms.append({
            "label": "Страховые льготы",
            "value": "есть" if econ["has_insurance_benefits"] else "нет",
            "normalized": None,
            "weight": 0,
            "contribution": round(insurance_bonus, 2),
            "explanation": "Постоянная надбавка за наличие страховых льгот",
        })
        score_terms.append({
            "label": "Ж/Д доступ",
            "value": "есть" if logistics["has_railway"] else "нет",
            "normalized": None,
            "weight": 0,
            "contribution": round(railway_bonus, 2),
            "explanation": "Постоянная надбавка за наличие железной дороги",
        })

        if score <= 0:
            continue
        results.append({
            "region": region,
            "score": round(score, 2),
            "estimate": estimate,
            "score_breakdown": score_terms,
            "score_formula": "Рейтинг = " + " + ".join(
                [
                    f"({term['normalized']} × {term['weight']})"
                    if term["normalized"] is not None
                    else f"{term['contribution']}"
                    for term in score_terms
                ]
            ) + f" = {round(score, 2)}"
        })
    results = sorted(results, key=lambda x: x["score"], reverse=True)
    return results[:3]