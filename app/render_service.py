import base64
import requests
from io import BytesIO
from PIL import Image

# Константы для конфигурации API
OPENROUTER_API_KEY = "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"
MODEL_NAME = "bytedance-seed/seedream-4.5"


def generate_photorealistic_renders(screenshot_base64: str, region_name: str, cultural_code: dict) -> Image.Image:
    """
    Отправляет 1 скриншот (вид с Севера) в Seedream 4.5.
    Нейросеть генерирует коллаж 2x2 с четырьмя ракурсами здания.
    """
    style = cultural_code.get('architecture_style', 'modern industrial')
    materials = cultural_code.get('materials', 'sandwich panels, glass')
    colors = ", ".join(cultural_code.get('color_profile', ['gray']))

    prompt = (
        f"A quad-split 2x2 grid photo, architectural render of an industrial factory in {region_name}. "
        f"Based on the provided front view, generate a highly photorealistic 2x2 collage showing 4 different angles of this exact building. "
        f"Top-Left quadrant: North view (front). Top-Right quadrant: East view. "
        f"Bottom-Left quadrant: South view. Bottom-Right quadrant: West view. "
        f"Architecture style: {style}. Materials: {materials}. Main colors: {colors}. "
        f"Crisp clean 2x2 grid alignment, professional composition, realistic sunny daylight."
    )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    # Очистка base64 если есть префикс data:image
    if "," in screenshot_base64:
        screenshot_base64 = screenshot_base64.split(",")[1]

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{screenshot_base64}"
                        }
                    }
                ]
            }
        ],
        "modalities": ["image"],
        "seed": 777
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)

        if response.status_code == 200:
            res_json = response.json()
            img_data = res_json['choices'][0]['message']['content']

            if img_data.startswith("http"):
                img_res = requests.get(img_data)
                return Image.open(BytesIO(img_res.content))
            else:
                if "," in img_data:
                    img_data = img_data.split(",")[1]
                return Image.open(BytesIO(base64.b64decode(img_data)))
        else:
            print(f"Ошибка OpenRouter API: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        print(f"Исключение при генерации рендеров: {e}")
        return None


def split_render_collage(collage_img: Image.Image) -> dict:
    """
    Разрезает готовый 2x2 коллаж ровно пополам по вертикали и горизонтали
    на 4 самостоятельные картинки.
    """
    width, height = collage_img.size
    mid_x = width // 2
    mid_y = height // 2

    return {
        "Север (Главный фасад)": collage_img.crop((0, 0, mid_x, mid_y)),
        "Восток (Правый профиль)": collage_img.crop((mid_x, 0, width, mid_y)),
        "Юг (Задний фасад)": collage_img.crop((0, mid_y, mid_x, height)),
        "Запад (Левый профиль)": collage_img.crop((mid_x, mid_y, width, height))
    }