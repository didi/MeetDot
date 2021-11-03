/*
Convert a translationLines object into an indexedTranslationLines object,
which includes highlight information (which text should be grey vs white)

*/
function indexTranslationLines(
  translationLines,
  highlightBoundaries,
  lineIndex
) {
  const indexedTranslationLines = [];
  for (let i = 0; i < translationLines.length; i++) {
    let text = translationLines[i];
    let highlightedText = "";

    if (highlightBoundaries) {
      if (highlightBoundaries[i] >= 0) {
        // highlight (fade out) the from hb[i] to the end characters
        // OR 0, which means highlight everything
        highlightedText = text.slice(highlightBoundaries[i]);
        text = text.slice(0, highlightBoundaries[i]);
      } // otherwise, -1, highlight nothing
    }

    indexedTranslationLines.push({
      index: lineIndex + i,
      text,
      highlightedText,
    });
  }
  return indexedTranslationLines;
}

export default {
  indexTranslationLines,
};
