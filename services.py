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
    logistics = region["logistics"]
    infra = region["infrastructure"]
    econ = region["economics"]
    production_m2 = user_input["production_volume"] * 1000
    employees = user_input["employees"]
    shop_area = max(7000, production_m2 * 0.026)
    warehouse_area = shop_area * 0.35
    abk_area = employees * 12
    housing_percent = user_input["housing"]["percent"] / 100
    housing_type = user_input["housing"]["type"]
    if housing_type == "общежитие":
        housing_per_person = 22
        housing_cost_per_m2 = 65000
    else:
        housing_per_person = 38
        housing_cost_per_m2 = 90000
    housing_area = employees * housing_percent * housing_per_person
    kindergarten_area = user_input["kindergarten_places"] * 15
    regional_coef = 1.0
    name = region["name"]
    if "Москва" in name: regional_coef = 1.35
    elif "Самарская" in name: regional_coef = 1.12
    elif "Башкортостан" in name: regional_coef = 1.08
    elif "Липецкая" in name: regional_coef = 0.95
    elif "Калужская" in name: regional_coef = 1.03
    production_cost = (shop_area + warehouse_area) * 32000 * regional_coef
    abk_cost = abk_area * 52000 * regional_coef
    housing_cost = housing_area * housing_cost_per_m2 * regional_coef
    kindergarten_cost = kindergarten_area * 50000 * regional_coef
    landscaping_prices = {
        "Аллея": 2_000_000, "Сквер с фонтаном": 5_000_000,
        "Беседки": 1_000_000, "Сцена": 3_000_000,
        "Тропа здоровья": 2_500_000, "Пруд": 6_000_000,
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
    capex = (production_cost + abk_cost + housing_cost + kindergarten_cost + landscaping_cost + sports_cost + connection_cost)
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
    return {
        "shop_area": round(shop_area),
        "warehouse_area": round(warehouse_area),
        "abk_area": round(abk_area),
        "housing_area": round(housing_area),
        "kindergarten_area": round(kindergarten_area),
        "capex": round(capex),
        "opex": round(opex),
        "total_cost": round(total_cost)
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
    architecture = user_input_dict["architecture_priority"]
    if architecture == "Экодизайн":
        weights["environment"] += 20
        weights["energy"] += 10
    elif architecture == "Техно-стиль":
        weights["power"] += 25
        weights["energy"] += 10
    elif architecture == "Аутентичность региону":
        weights["environment"] += 10
        weights["salary"] += 10
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
        score = 0
        score += normalize_inverse(logistics["distance_to_steel_km"], steel_values) * weights["steel"]
        score += normalize_inverse(logistics["distance_to_polyurethane_km"], poly_values) * weights["poly"]
        score += normalize_inverse(econ["energy_tariff_rub_kwh"], energy_values) * weights["energy"]
        score += normalize_direct(infra["available_power_kva"], power_values) * weights["power"]
        score += normalize_inverse(econ["average_salary_rub"], salary_values) * weights["salary"]
        score += normalize_inverse(social["rent_1room_apartment_rub"], rent_values) * weights["rent"]
        score += normalize_direct(social["city_environment_index"], env_values) * weights["environment"]
        if econ["has_oez_benefits"]: score += 5
        if econ["has_insurance_benefits"]: score += 3
        if logistics["has_railway"]: score += 2
        if logistics["distance_to_highway_km"] > 5:
            score -= 5
        if econ["average_salary_rub"] > 100000:
            score -= 5
        if score <= 0:
            continue
        results.append({
            "region": region,
            "score": round(score, 2),
            "estimate": estimate
        })
    results = sorted(results, key=lambda x: x["score"], reverse=True)
    return results[:3]