
from pathlib import Path
import re

import torch
from PIL import Image

from app.service.model import florence_processor, florence_model


def run_florence(image: Image.Image, task_prompt: str, max_new_tokens: int):
    inputs = florence_processor(
        text=task_prompt,
        images=image,
        return_tensors="pt"
    )

    with torch.no_grad():
        generated_ids = florence_model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            num_beams=1
        )

    generated_text = florence_processor.batch_decode(
        generated_ids,
        skip_special_tokens=False
    )[0]

    result = florence_processor.post_process_generation(
        generated_text,
        task=task_prompt,
        image_size=image.size
    )

    return result.get(task_prompt, "")


def format_region_captions(region_result: dict) -> str:
    labels = region_result.get("labels", [])
    bboxes = region_result.get("bboxes", [])

    descriptions = []

    for index, label in enumerate(labels):
        if index < len(bboxes):
            bbox = bboxes[index]

            descriptions.append(
                f"Region {index + 1}: {label}. "
                f"Location: {bbox}"
            )
        else:
            descriptions.append(
                f"Region {index + 1}: {label}"
            )

    return "\n".join(descriptions)


def build_structured_description(ocr_text: str) -> str:
    normalized_text = re.sub(r"\s+", " ", ocr_text).lower()

    details = []

    if "post" in normalized_text:
        details.append("HTTP method: POST")

    if "bearer" in normalized_text and "token" in normalized_text:
        details.append("Authorization: Bearer Token")

    if "form-data" in normalized_text or "form data" in normalized_text:
        details.append("Request body: form-data")

    if "sample.pdf" in normalized_text:
        details.append("Uploaded file: sample.pdf")

    if "200 ok" in normalized_text:
        details.append("Response status: 200 OK")

    if not details:
        return ""

    description = "Detected image details:\n"

    for detail in details:
        description += detail + "\n"

    return description.strip()


def generate_image_description(file_path: Path) -> str:
    file_path = Path(file_path)

    with Image.open(file_path) as image:
        image = image.convert("RGB")

        # 1. Extract text from the image.
        ocr_text = run_florence(
            image=image,
            task_prompt="<OCR>",
            max_new_tokens=512
        )

        # 2. Generate a detailed description of the entire image.
        caption = run_florence(
            image=image,
            task_prompt="<MORE_DETAILED_CAPTION>",
            max_new_tokens=512
        )

        # 3. Generate descriptions of individual image regions.
        region_result = run_florence(
            image=image,
            task_prompt="<DENSE_REGION_CAPTION>",
            max_new_tokens=512
        )

    # Format region descriptions.
    region_descriptions = format_region_captions(region_result)

    # Build structured OCR details.
    structured_description = build_structured_description(ocr_text)

    # Combine all information.
    description = (
        f"Image text:\n{ocr_text}\n\n"
        f"{structured_description}\n\n"
        f"Overall image description:\n{caption}\n\n"
        f"Individual region descriptions:\n{region_descriptions}"
    )

    return description.strip()
