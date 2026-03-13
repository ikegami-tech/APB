def generate_cover_image(image_prompt):
    """AIプロンプトから雑誌の表紙用画像を生成する"""
    response = client.images.generate(
        model="dall-e-3",
        prompt=f"High-end real estate magazine cover photo, {image_prompt}, cinematic lighting, 8k, professional photography",
        size="1024x1792", # 縦長（A4に近い比率）
        quality="standard",
        n=1,
    )
    return response.data[0].url
