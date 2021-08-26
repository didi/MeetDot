from .language import Language

languages = {
    "en-US": Language("en-US", has_spaces=True),
    "zh": Language("zh", has_spaces=False),
    "es-ES": Language("es-ES", has_spaces=True),
    "pt-BR": Language("pt-BR", has_spaces=True),
}
