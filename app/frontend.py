import streamlit as st
import requests
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Подбор локации", layout="wide")

st.title("Выбор оптимального региона для строительства")

st.markdown("Внесите требуемые параметры для скоринга (10 базовых форм):")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Производство и Экономика")
    production_volume = st.number_input("Объем производства (тыс. м²/год):", min_value=1, value=500, step=50)
    employees = st.number_input("Количество сотрудников:", min_value=10, value=50, step=10)
    budget_mln = st.number_input("Бюджет (млн руб):", min_value=10, value=1500, step=100)
    
    st.subheader("2. Логистика")
    railway_options = {
        "Не имеет значения": "any",
        "Обязательно нужны": "required",
        "Не требуются (запрещено)": "forbidden"
    }
    railway_choice = st.selectbox("Потребность в Ж/Д путях", list(railway_options.keys()))
    railway_mode = railway_options[railway_choice]
    max_distance_to_highway = st.slider("Макс. удаленность от трассы (км)", min_value=0, max_value=100, value=10)

with col2:
    st.subheader("3. Архитектура и Благоустройство")
    architecture_priority = st.selectbox("Архитектурный приоритет", ["Экодизайн", "Техно-стиль", "Аутентичность региону"])
    
    landscaping_options = ["Аллея", "Сквер с фонтаном", "Беседки", "Сцена", "Тропа здоровья", "Пруд", "Арт-объект"]
    landscaping = st.multiselect("Элементы благоустройства", landscaping_options, default=["Аллея", "Пруд"])

    st.subheader("4. Социальные приоритеты")
    housing_percent = st.slider("Процент сотрудников с жильем (%)", min_value=0, max_value=100, value=10)
    housing_type = st.selectbox("Тип жилья", ["общежитие", "квартира"])
    kindergarten_places = st.number_input("Места в детском саду", min_value=0, value=50)
    
    sports_options = ["Уличные тренажёры", "Стадион", "Бассейн", "Спортзал", "Хоккейная коробка"]
    sports = st.multiselect("Спортивные объекты", sports_options, default=["Спортзал", "Стадион"])

if st.button("Рассчитать оптимальные регионы", type="primary"):
    payload = {
        "production_volume": production_volume,
        "employees": employees,
        "budget_mln": budget_mln,
        "railway_mode": railway_mode,
        "max_distance_to_highway": max_distance_to_highway,
        "architecture_priority": architecture_priority,
        "landscaping": landscaping,
        "housing": {
            "percent": housing_percent,
            "type": housing_type
        },
        "kindergarten_places": kindergarten_places,
        "sports": sports
    }
    
    with st.spinner("Анализ данных..."):
        try:
            # Send request to FastAPI backend
            response = requests.post("http://localhost:8000/api/score", json=payload)
            response.raise_for_status()
            
            data = response.json()
            st.session_state["top_regions"] = data.get("top_regions", [])
            st.session_state["calculated"] = True
                
        except Exception as e:
            st.error(f"Ошибка при подключении к backend: {e}")

if st.session_state.get("calculated", False):
    top_regions = st.session_state["top_regions"]
    
    if not top_regions:
        st.warning("Нет регионов, удовлетворяющих жестким фильтрам.")
    else:
        # Center map around the top 1 region
        if top_regions and "coordinates" in top_regions[0]["region"]:
            first_lat = top_regions[0]["region"]["coordinates"].get("lat", 54.0)
            first_lon = top_regions[0]["region"]["coordinates"].get("lon", 45.0)
            m = folium.Map(location=[first_lat, first_lon], zoom_start=6)
        else:
            m = folium.Map(location=[54.0, 45.0], zoom_start=5)
            
        # Скрываем вотермарку Leaflet с помощью CSS
        from branca.element import Element
        m.get_root().html.add_child(Element("<style>.leaflet-control-attribution { display: none !important; }</style>"))
        
        tabs = st.tabs([f"{i+1}. {r['region']['name']}" for i, r in enumerate(top_regions)])
        
        colors = ["red", "orange", "blue", "green", "purple"]
        
        for i, r in enumerate(top_regions):
            region_data = r["region"]
            est = r["estimate"]
            
            lat = region_data.get("coordinates", {}).get("lat", 54.0)
            lon = region_data.get("coordinates", {}).get("lon", 45.0)
            
            marker_color = colors[i] if i < len(colors) else "gray"
            icon_type = "star" if i == 0 else "info-sign"
                    
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(f"<b>{region_data['name']}</b><br>Место: {i+1}<br>Рейтинг: {r['score']}", max_width=300),
                tooltip=f"#{i+1}: {region_data['name']} (Рейтинг: {r['score']})",
                icon=folium.Icon(color=marker_color, icon=icon_type)
            ).add_to(m)
            
            with tabs[i]:
                st.subheader(f"Итоговый рейтинг: {r['score']}")
                
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.markdown("#### Социальный паспорт региона")
                    st.write(f"- **Индекс городской среды:** {region_data['social']['city_environment_index']}")
                    st.write(f"- **Обеспеченность детскими садами:** {region_data['social']['kindergarten_occupancy_per_100_kids']} мест на 100 детей")
                    st.write(f"- **Профильные колледжи:** {'Есть' if region_data['social']['has_profile_colleges'] else 'Нет'}")
                    st.write(f"- **Средняя аренда 1-комн. квартиры:** {region_data['social']['rent_1room_apartment_rub']} руб/мес")

                    st.markdown("#### Экономический блок")
                    st.write(f"- **Налоговые льготы:** {'Есть' if region_data['economics']['has_oez_benefits'] else 'Нет'}")
                    st.write(f"- **Энерготариф:** {region_data['economics']['energy_tariff_rub_kwh']} руб/кВт·ч")
                    st.write(f"- **Средняя зарплата:** {region_data['economics']['average_salary_rub']} руб/мес")

                    st.markdown("#### Рекомендации по удержанию персонала")
                    if region_data['social']['rent_1room_apartment_rub'] >= 25000:
                        st.write("- Рекомендуется строительство корпоративного жилья.")
                    else:
                        st.write("- Допускается использование рынка аренды жилья.")
                    
                    if region_data['logistics']['distance_to_highway_km'] > 15:
                        st.write("- Требуется корпоративный автобус для сотрудников.")
                    else:
                        st.write("- Транспортная доступность соответствует нормативам.")
                        
                    if region_data['social']['has_profile_colleges']:
                        st.write("- Рекомендуется сотрудничество с профильными колледжами.")

                with col_b:
                    st.markdown("#### Сетевой блок")
                    st.write(f"- **Наличие газа:** {'Есть' if region_data['infrastructure']['has_gas_in_promzone'] else 'Нет'}")
                    st.write(f"- **Свободная мощность:** {region_data['infrastructure']['available_power_kva']} кВА")
                    st.write(f"- **Стоимость подключения:** {region_data['infrastructure']['connection_cost_rub_kwt']} руб/кВт")

                    st.markdown("#### Логистика сырья")
                    st.write(f"- **Расстояние до поставщика стали:** {region_data['logistics']['distance_to_steel_km']} км")
                    st.write(f"- **Расстояние до поставщика утеплителя:** {region_data['logistics']['distance_to_polyurethane_km']} км")

                    st.markdown("#### Предварительная смета строительства")
                    st.write(f"- **Площадь производственного цеха:** {est['shop_area']:,} м²")
                    st.write(f"- **Площадь склада:** {est['warehouse_area']:,} м²")
                    st.write(f"- **Площадь АБК:** {est['abk_area']:,} м²")
                    st.write(f"- **Площадь жилья:** {est['housing_area']:,} м²")
                    st.write(f"- **Площадь детского сада:** {est['kindergarten_area']:,} м²")
                    st.write("---")
                    st.write(f"- **CAPEX проекта:** {est['capex']:,} руб")
                    st.write(f"- **Годовой OPEX:** {est['opex']:,} руб/год")
                    st.markdown(f"**ИТОГОВАЯ СМЕТА ПРОЕКТА:** :green[**{est['total_cost']:,} руб**]")
        
        st.markdown("### Карта рекомендованных площадок")
        st_folium(m, width=900, height=400)
