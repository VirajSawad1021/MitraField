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
    "woodblock": {
        "label": "Woodblock",
        "blurb": "Japanese woodblock print on aged paper: flat colour, fine line, calm.",
        "image": ("Japanese ukiyo-e woodblock print style: flat areas of colour from a limited natural palette (indigo, "
                  "vermilion, ochre, sage, cream), fine confident outlines, stylised waves, clouds and mist bands, visible "
                  "washi paper texture and gentle print registration, calm balanced composition with generous sky."),
        "character": "an adult figure drawn in woodblock-print style: simple elegant outline, flat colour clothing, small calm face",
        "avoid": "photorealism, gradients, 3D shading, glossy digital look, anime, childish faces",
    },
    "collage": {
        "label": "Paper collage",
        "blurb": "Paper cutouts, halftone dots and torn layers, crafted and tactile.",
        "image": ("Handmade paper collage: layered cut and torn paper shapes with visible edges and soft drop shadows, "
                  "halftone dot textures, risograph-like grain, a warm limited palette, cut-out photographic fragments "
                  "where useful, playful but grown-up editorial composition."),
        "character": "an adult figure assembled from cut paper and a halftone photo fragment, clean silhouette",
        "avoid": "smooth digital gradients, glossy 3D, childish stickers, clip-art",
    },
    "isometric": {
        "label": "Isometric",
        "blurb": "Clean isometric 3D diagrams: systems, cities and machines explained.",
        "image": ("Clean isometric illustration at a true 30-degree isometric angle: precise geometric forms, soft "
                  "ambient-occlusion shading, a calm cohesive palette with one accent colour, tidy diorama composition "
                  "on a plain ground, every part readable like a technical explainer diagram."),
        "character": "a small adult figure in matching isometric style, simple shapes, correct proportions",
        "avoid": "perspective distortion, photorealism, clutter, toy-like gloss, childish characters",
    },
    "blueprint": {
        "label": "Blueprint",
        "blurb": "Technical line drawing on blueprint, precise and engineered.",
        "image": ("Engineering blueprint: crisp white and pale-cyan technical linework on deep blueprint blue, "
                  "orthographic and cutaway views, construction lines, subtle grid and paper texture, precise and "
                  "uncluttered like a master draughtsman's plate."),
        "character": "an adult figure rendered as a clean technical line drawing on blueprint",
        "avoid": "colour fills, photorealism, glow effects, sketchy mess, any readable text",
    },
}
DEFAULT_LOOK = "cinematic"

# Colours for code-drawn visuals in each look: bg, ink (main), muted, accent, accent2, and whether the ground is paper.
PALETTES = {
    "cinematic": dict(bg="#0A0A0B", ink="#F4F1EA", muted="#8C8A85", accent="#FF5A36", accent2="#4FB3FF", paper=False),
    "editorial": dict(bg="#F3EDE3", ink="#1F2A3A", muted="#8A8478", accent="#E4572E", accent2="#2E6E8E", paper=True),
    "studio3d": dict(bg="#101317", ink="#EEF1F4", muted="#8D96A0", accent="#FF8A3D", accent2="#5BC0EB", paper=False),
    "ink": dict(bg="#F5F0E6", ink="#22201C", muted="#8C857A", accent="#B5432F", accent2="#3F6E8C", paper=True),
    "motion": dict(bg="#0E0E10", ink="#FFFFFF", muted="#7A7A80", accent="#FF4D2E", accent2="#3DDC97", paper=False),
    "archival": dict(bg="#EDE6D6", ink="#2A2620", muted="#8F877A", accent="#9C3B2A", accent2="#4D5E6E", paper=True),
    "woodblock": dict(bg="#F1E8D6", ink="#22344F", muted="#9A8F7C", accent="#C8452F", accent2="#3D6B8F", paper=True),
    "collage": dict(bg="#F4EBDD", ink="#2B2622", muted="#9A8E80", accent="#E05A3A", accent2="#2F7F86", paper=True),
    "isometric": dict(bg="#EEF2F3", ink="#22313A", muted="#8A979E", accent="#F26B4F", accent2="#3B8EA5", paper=True),
    "blueprint": dict(bg="#123A6B", ink="#EAF4FF", muted="#8FB3D9", accent="#FFD166", accent2="#7FD3FF", paper=False),
}


def palette(name):
    return PALETTES.get(name or DEFAULT_LOOK, PALETTES[DEFAULT_LOOK])

COMMON_AVOID = ("borders, frames or mats around the picture (always full-bleed), chibi, childish or baby-faced characters, mascots, glowing holograms, neon overload, floating UI, sci-fi "
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
