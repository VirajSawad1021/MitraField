"""House look for every generated image: cinematic, photographic, restrained.

Appended to all Nano Banana prompts (stills, characters, cast references, Veo first frames) so
generated beats read like a high-end documentary, not like AI art.
"""

CINEMATIC = ("Photographic realism, cinematic documentary cinematography, shot on a full-frame cinema camera "
             "with a 35mm or 50mm prime lens, practical and natural light, gentle contrast, restrained film colour "
             "grade, subtle film grain, real textures and imperfections, believable scale and physics.")

AVOID = ("Avoid: cartoon, chibi, anime, cel shading, toy-like 3D render, plastic or airbrushed skin, big shiny eyes, "
         "glowing holograms, neon overload, floating UI, sci-fi clutter, fantasy elements, oversaturated colours, "
         "heavy bloom, lens-flare spam, text, letters, logos, watermarks.")


def finish(prompt: str, style: str | None = None) -> str:
    """Prompt + art direction + realism guard. `style` overrides the default cinematic direction."""
    return f"{prompt.rstrip('. ')}. {style or CINEMATIC} {AVOID}"
