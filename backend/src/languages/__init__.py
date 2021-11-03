from .language import Language

languages = {
    "en-US": Language("en-US"),
    "zh": Language("zh", has_spaces=False, eos_punctuation="。"),
    "es-ES": Language("es-ES"),
    "pt-BR": Language("pt-BR"),
}
