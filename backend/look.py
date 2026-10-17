"""Looks: professional art directions a project can choose. Every generated image (stills,
presenter, cast references, Veo first frames) is finished with the project's look, and every
look shares one guard against the cheap 'AI art' feel."""

LOOKS = {
    "cinematic": {
        "label": "Cinematic",
        "blurb": "Photographic documentary realism, like a premium film series.",
        "image": ("Photographic realism, cinematic documentary cinematography, full-frame cinema camera with a 35mm or "
                  "50mm prime, practical and natural light, restrained film colour grade, subtle film grain, real "
                  "textures and imperfections."),
        "character": "a real-looking adult, natural face and wardrobe, filmed candidly",
        "avoid": "cartoon, illustration, anime, toy-like 3D render, plastic or airbrushed skin",
    },
    "editorial": {
        "label": "Editorial flat",
        "blurb": "Clean flat vector illustration, like a top explainer studio.",
        "image": ("Premium flat vector illustration for a professional explainer animation: bold geometric shapes, "
                  "clean edges, a limited harmonious palette of 4-6 colours, soft long shadows, subtle paper grain, "
                  "generous negative space, clear focal point, strong composition."),
        "character": ("a professional explainer-animation character: adult proportions, simple geometric face with a "
                      "few precise features, clean silhouette, flat colours from the palette, confident natural pose"),
        "avoid": "photorealism, gradients overload, clip-art, childish or baby-faced characters, big glossy eyes",
    },
    "studio3d": {
        "label": "Premium 3D",
        "blurb": "Polished stylised 3D, soft studio light, adult characters.",
        "image": ("High-end stylised 3D render like a premium product or feature-animation still: soft global "
                  "illumination, matte and subtle-roughness materials, gentle depth of field, clean studio lighting, "
                  "tasteful muted palette, physically plausible scale."),
        "character": ("a stylised 3D adult character with realistic proportions, refined sculpted features, matte skin, "
                      "well-tailored clothing, subtle expression"),
        "avoid": "toy or plastic look, oversized heads, baby faces, big glossy eyes, candy colours, mobile-game style",
    },
    "ink": {
        "label": "Ink & wash",
        "blurb": "Hand-inked line with watercolour wash, like a quality newspaper.",
        "image": ("Editorial ink drawing with loose watercolour wash, confident hand-drawn linework of varying weight, "
                  "off-white paper texture, restrained palette of two or three washes, thoughtful composition like a "
                  "feature illustration in a serious newspaper."),
        "character": "an adult drawn with confident ink lines and light wash, natural proportions, observed not cute",
        "avoid": "digital gloss, neon, cartoonish exaggeration, childish characters, heavy outlines everywhere",
    },
    "motion": {
        "label": "Motion graphics",
        "blurb": "Bold iconographic shapes and type-ready layouts, Swiss-design clean.",
        "image": ("Modern motion-graphics frame: bold flat iconographic shapes, Swiss design grid, high contrast, a "
                  "near-black or warm off-white ground with one or two vivid accent colours, crisp vector edges, "
                  "purposeful empty space for on-screen text, no clutter."),
        "character": "a minimal iconographic human figure built from simple geometric shapes, adult proportions, no facial clutter",
        "avoid": "photorealism, painterly texture, busy backgrounds, childish mascots",
    },
    "archival": {
        "label": "Archival",
        "blurb": "Period photographs and engravings with authentic grain.",
        "image": ("Authentic archival look of the era: period-correct photographic film stock or engraving, natural "
                  "grain, tonal range and wear of the period, documentary framing, believable historical detail."),
        "character": "a real-looking adult of the period, photographed as in historical archives",
        "avoid": "modern objects, digital sharpness, cartoon, illustration gloss",
    },
}
DEFAULT_LOOK = "cinematic"

COMMON_AVOID = ("chibi, childish or baby-faced characters, mascots, glowing holograms, neon overload, floating UI, sci-fi "
                "clutter, fantasy elements, oversaturated colours, heavy bloom, lens-flare spam, AI-art gloss, text, "
                "letters, logos, watermarks")

# kept for engines that import it directly
CINEMATIC = LOOKS["cinematic"]["image"]


def get(name):
    return LOOKS.get(name or DEFAULT_LOOK, LOOKS[DEFAULT_LOOK])


def finish(prompt: str, style: str | None = None, look: str | None = None) -> str:
    """Prompt + project style (or the look's art direction) + look-specific and common guards."""
    lk = get(look)
    return f"{prompt.rstrip('. ')}. {style or lk['image']} Avoid: {lk['avoid']}, {COMMON_AVOID}."


def character(look: str | None) -> str:
    return get(look)["character"]
